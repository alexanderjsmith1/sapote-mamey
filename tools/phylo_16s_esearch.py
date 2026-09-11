
"""phylo 16s esearch. External inputs remain outside the software bundle."""
import argparse
import os
import re
import sqlite3
import subprocess
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import logging
_LOG = logging.getLogger(__name__)
import _phylo16s as _p16

DB = _p16.rrna16s_db(os.environ.get("SAPOTE_16S_SQLITE"), must_exist=False)
ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
TOOL = "sapote-mamey-16s"
RETMAX = 5000


BASE = 'Actinomycetota[Organism] AND "16S ribosomal RNA"[Title] AND 900:2000[SLEN]'

SETS = {
    "moss":        "(moss[All Fields] OR Sphagnum[All Fields] OR Dicranum[All Fields] "
                   "OR Polytrichum[All Fields] OR Leucobryum[All Fields])",
    "bryophyte":   "(bryophyte[All Fields] OR liverwort[All Fields] OR hornwort[All Fields] "
                   "OR Marchantia[All Fields] OR moss[All Fields])",
    "lichen":      "(lichen[All Fields] OR Cladonia[All Fields] OR Usnea[All Fields] "
                   "OR Parmelia[All Fields] OR Peltigera[All Fields])",
    "bee":         "(Bombus[All Fields] OR Apis[All Fields] OR bumblebee[All Fields] "
                   "OR honeybee[All Fields] OR Megachile[All Fields] OR Osmia[All Fields] "
                   "OR Andrena[All Fields])",
    "wasp":        "(wasp[All Fields] OR Philanthus[All Fields] OR Vespula[All Fields])",
    "ant":         "(Atta[All Fields] OR Acromyrmex[All Fields] OR attine[All Fields] "
                   "OR Trachymyrmex[All Fields] OR Cyphomyrmex[All Fields] "
                   "OR Myrmicocrypta[All Fields])",
    "hymenoptera": "(Hymenoptera[All Fields] OR Bombus[All Fields] OR Apis[All Fields] "
                   "OR wasp[All Fields] OR Atta[All Fields] OR Acromyrmex[All Fields])",
    "insect":      "(insect[All Fields] OR beetle[All Fields] OR termite[All Fields] "
                   "OR Dendroctonus[All Fields] OR Coleoptera[All Fields])",
    "ontario":     "Ontario[All Fields]",
    "canada":      "Canada[All Fields]",
    "eastern_us":  "(New Jersey[All Fields] OR Pennsylvania[All Fields] OR Alabama[All Fields] "
                   "OR West Virginia[All Fields] OR Virginia[All Fields] OR Maryland[All Fields] "
                   "OR New York[All Fields] OR Georgia[All Fields] OR Tennessee[All Fields] "
                   "OR North Carolina[All Fields] OR South Carolina[All Fields])",
}


def esearch(term, retmax=RETMAX):
    """(ids, reported_count, verified). `verified` is False when the count could not be confirmed
    against the returned identifiers, which is the only condition under which it may be wrong."""
    params = {"db": "nuccore", "term": term, "retmax": str(retmax), "tool": TOOL}
    url = ESEARCH + "?" + urllib.parse.urlencode(params)
    for attempt in range(4):
        p = subprocess.run(["curl", "--fail", "--silent", "--show-error", "--max-time", "120", url],
                           capture_output=True, text=True)
        if p.returncode == 0 and "<eSearchResult>" in p.stdout:
            try:
                xml = ET.fromstring(p.stdout)
                if xml.find('.//ERROR') is not None or xml.find('.//ErrorList') is not None:
                    raise ValueError('ESearch returned an error')
                count = int(xml.findtext('Count', '-1'))
                ids = [node.text for node in xml.findall('./IdList/Id')]
                verified = (count >= 0 and count == len(ids) and count <= retmax
                            and len(ids) == len(set(ids)) and all(x and x.isdigit() for x in ids))
                return ids, count, verified
            except (ValueError, ET.ParseError) as exc:
                _LOG.warning("ESearch response could not be admitted on attempt %s: %s", attempt + 1, exc)
        time.sleep(2 ** attempt)
    return [], -1, False


def acc_for(uids):
    """UID -> accession.version, via esummary. esearch on nuccore returns GI numbers, and the
    database is keyed on accessions, so this step is not optional."""
    out = []
    for i in range(0, len(uids), 400):
        chunk = uids[i:i + 400]
        url = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=nuccore&id="
               + ",".join(chunk) + f"&tool={TOOL}")


        got = None
        for attempt in range(4):
            p = subprocess.run(["curl", "--fail", "--silent", "--show-error", "--max-time", "120", url],
                               capture_output=True, text=True)
            if p.returncode == 0 and "eSummaryResult" in p.stdout:
                try:
                    xml = ET.fromstring(p.stdout)
                    mapped = {}
                    for doc in xml.findall('./DocSum'):
                        uid = doc.findtext('Id')
                        values = [item.text for item in doc.findall("./Item[@Name='AccessionVersion']")]
                        if uid not in chunk or uid in mapped or len(values) != 1:
                            raise ValueError('unexpected, duplicate or unbound ESummary UID')
                        mapped[uid] = _p16.accession(values[0], version_required=True)
                    if set(mapped) != set(chunk):
                        raise ValueError('incomplete ESummary UID mapping')
                    got = [mapped[uid] for uid in chunk]
                    if len(set(got)) != len(got):
                        raise ValueError('duplicate ESummary accession mapping')
                    break
                except (ValueError, ET.ParseError):
                    got = None
            time.sleep(2 ** attempt)
        if got is None:
            raise SystemExit(
                f"esummary FAILED for UIDs {i}-{i + len(chunk)} after 4 attempts "
                f"(last curl exit {p.returncode}). Refusing to continue: the missing accessions "
                f"would be indistinguishable from records NCBI does not have.")
        out += got
        time.sleep(0.4)
    return out


def main(argv=None):
    from contextlib import closing
    ap = argparse.ArgumentParser(allow_abbrev=False)
    ap.add_argument('--db', default='')
    ap.add_argument('--out-db')
    ap.add_argument('--sets', default='all')
    ap.add_argument('--dry-run', action='store_true', help='validate and display plan; no network or writes')
    ap.add_argument('--retmax', type=int, default=RETMAX)
    a = ap.parse_args(argv)
    names = list(SETS) if a.sets == 'all' else [s.strip() for s in a.sets.split(',')]
    if a.retmax <= 0 or len(set(names)) != len(names) or any(name not in SETS for name in names):
        ap.error('positive retmax and unique known set names required')
    if not a.dry_run and not a.out_db:
        ap.error('--out-db is required for an additive result')
    if a.out_db:
        _p16.require_new_output(a.out_db)
    db = _p16.rrna16s_db(a.db or None)
    digest = _p16.sha256_file(db)
    events = []
    with closing(_p16.database_copy(db)) as con:
        if a.dry_run:
            _LOG.info('DRY_RUN: counts and new records NOT_MEASURED; no network or files written')
            for name in names:
                _LOG.info(f'{name}: {BASE} AND {SETS[name]}')
            return 0
        con.execute('CREATE TABLE IF NOT EXISTS record_tag '
                    '(acc_base TEXT NOT NULL, tag TEXT NOT NULL, evidence TEXT, PRIMARY KEY(acc_base,tag))')
        for name in names:
            term = f'{BASE} AND {SETS[name]}'
            ids, count, verified = esearch(term, a.retmax)
            if not verified:
                raise ValueError(f'ESearch completeness hold for {name}: count={count}, returned={len(ids)}')
            accs = acc_for(ids) if ids else []
            if len(accs) != count:
                raise ValueError('ESummary count does not bind to ESearch result')
            for acc in accs:
                base = acc.split('.')[0]
                row = con.execute('SELECT acc_version FROM record WHERE acc_base=?', (base,)).fetchone()
                if row and row[0] and row[0] != acc:
                    raise ValueError(f'accession version conflict for {base}')
                con.execute('INSERT OR IGNORE INTO record '
                    '(acc_base,acc_version,source,origin,coll_ids,uncultured) VALUES (?,?,?,?,?,?)',
                    (base,acc,'attribute_candidate',f'esearch:{name}','[]',0))
                con.execute('INSERT OR REPLACE INTO record_tag VALUES (?,?,?)',
                    (base,f'query:{name}', 'query match only; source metadata must establish membership'))
            events.append(dict(name=name, term=term, count=count, uid_accessions=list(zip(ids,accs))))
        if _p16.sha256_file(db) != digest:
            raise ValueError('input database changed during search')
        _p16.save_database(con, a.out_db, 'esearch', dict(input_sha256=digest, searches=events,
                                                       status='QUERY_CANDIDATES_ONLY'))
    _LOG.info(f'Candidate searches complete; additive database: {a.out_db}')
    return 0


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    sys.exit(main())
