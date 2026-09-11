
"""phylo 16s fetch. External inputs remain outside the software bundle."""
import argparse
import os
import re
import sqlite3
import sys
import time
import subprocess
import urllib.parse

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import logging
_LOG = logging.getLogger(__name__)
import _phylo16s as _p16


DB = _p16.rrna16s_db(os.environ.get("SAPOTE_16S_SQLITE"), must_exist=False)
EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
BATCH = 200
SLEEP = 0.4
TOOL = "sapote-mamey-16s"
EMAIL = os.environ.get("NCBI_EMAIL", "")

EXTRA_COLS = [
    ("lineage", "TEXT"), ("phylum", "TEXT"), ("class_", "TEXT"), ("order_", "TEXT"),
    ("family", "TEXT"), ("strain_qual", "TEXT"), ("host", "TEXT"),
    ("isolation_source", "TEXT"), ("geo_loc_name", "TEXT"), ("country", "TEXT"),
    ("subregion", "TEXT"), ("admin2", "TEXT"), ("lat_lon", "TEXT"),
    ("collection_date", "TEXT"),
    ("study_title", "TEXT"), ("fetched_at", "TEXT"),
    ("seq_sha256", "TEXT"),
]


def ensure_columns(con):
    have = {r[1] for r in con.execute("PRAGMA table_info(record)")}
    for name, typ in EXTRA_COLS:
        if name not in have:
            con.execute(f"ALTER TABLE record ADD COLUMN {name} {typ}")
    con.execute("""CREATE TABLE IF NOT EXISTS record_tag (
        acc_base TEXT NOT NULL, tag TEXT NOT NULL, evidence TEXT,
        PRIMARY KEY (acc_base, tag))""")
    con.execute("CREATE INDEX IF NOT EXISTS ix_tag ON record_tag(tag)")
    con.commit()


def parse_gb(text):
    """Read exactly one complete GenBank record with Biopython's feature parser.

    Source qualifiers can span lines and source can be the terminal feature or
    have a compound location. Taxonomy lineage is retained without guessing ranks
    from name suffixes. Missing optional Biopython is an explicit dependency hold.
    """
    import io
    try:
        from Bio import SeqIO
    except ImportError as exc:
        raise RuntimeError("GenBank parsing requires the optional Biopython dependency") from exc
    if not re.search(r"^//\s*$", text, re.M):
        raise ValueError("incomplete GenBank record")
    record = SeqIO.read(io.StringIO(text), "genbank")
    version = _p16.accession(record.id, version_required=True)
    seq = _p16.sequence(str(record.seq))
    declared = re.search(r'^LOCUS\s+\S+\s+(\d+)\s+bp\b',text,re.M)
    if not declared or int(declared.group(1)) != len(seq):
        raise ValueError('GenBank LOCUS length does not bind to sequence')
    accessions = record.annotations.get('accessions',[])
    if not accessions or accessions[0] != version.split('.')[0]:
        raise ValueError('GenBank ACCESSION and VERSION conflict')
    out = dict(acc_version=version, acc_base=version.split('.')[0], seq=seq,
               definition=record.description, organism=record.annotations.get('organism'),
               lineage='; '.join(record.annotations.get('taxonomy', [])) or None)
    sources = [feature for feature in record.features if feature.type == 'source']
    if len(sources) != 1:
        raise ValueError("source feature is missing or ambiguous")
    qualifiers = sources[0].qualifiers
    for key in ('strain','host','isolation_source','geo_loc_name','country','lat_lon','collection_date'):
        values = {' '.join(value.split()) for value in qualifiers.get(key, [])}
        if len(values) > 1:
            raise ValueError(f"conflicting source qualifier: {key}")
        if values:
            out[key] = next(iter(values))
    if out.get('country') and out.get('geo_loc_name') and out['country'] != out['geo_loc_name']:
        raise ValueError("conflicting country and geo_loc_name qualifiers")
    geography = out.get('geo_loc_name') or out.get('country')
    if geography:
        out['geo_loc_name'] = geography
        out['country'] = geography.partition(':')[0].strip()
        # Administrative levels cannot be inferred from comma order.
    for reference in record.annotations.get('references', []):
        if reference.title and reference.title.lower() != 'direct submission':
            out['study_title'] = reference.title
            break
    out['type_material'] = qualifiers.get('type_material', [])
    return out


def fetch_batch(accs, seq_stop=None):
    """Fetch through curl with normal TLS and HTTP error checking."""
    params = {"db": "nuccore", "id": ",".join(accs), "rettype": "gb", "retmode": "text",
              "tool": TOOL}
    if seq_stop:


        params["seq_start"] = "1"
        params["seq_stop"] = str(seq_stop)
    if EMAIL:
        params["email"] = EMAIL
    url = EFETCH + "?" + urllib.parse.urlencode(params)
    for attempt in range(4):
        p = subprocess.run(["curl", "--fail", "--silent", "--show-error", "--max-time", "180", url],
                           capture_output=True, text=True)
        if p.returncode == 0 and "VERSION" in p.stdout:
            return p.stdout
        if attempt == 3:
            _LOG.error("batch failed after 4 tries (curl rc=%s)", p.returncode)
            return ""
        time.sleep(2 ** attempt)
    return ""


def work_queue(con, limit_genus=None, source="pdf_candidate"):
    """Exact accession.version where available; local records never enter NCBI requests."""
    cohort = [g for (g,) in con.execute(
        "SELECT DISTINCT genus FROM record WHERE source='as_governed' AND genus != ''")]
    have = {row[1] for row in con.execute('PRAGMA table_info(record)')}
    missing = 'lineage IS NULL' if 'lineage' in have else '1=1'
    sql = "SELECT acc_base,acc_version,genus FROM record WHERE source=? AND "
    sql += missing if source == 'refseq_type' else 'seq IS NULL'
    params = [source]
    if limit_genus:
        sql += ' AND genus=?'
        params.append(limit_genus)
    rows = con.execute(sql, params).fetchall()
    rows.sort(key=lambda row: (row[2] not in cohort, row[2] or '', row[0]))
    queue = []
    for base, version, _ in rows:
        value = _p16.accession(version or base)
        if value.split('.')[0] != base:
            raise ValueError('stored accession/version conflict')
        queue.append(value)
    return queue, cohort


def bind_batch(text, requested):
    """All returned rows must bind once to the requested accession and exact version."""
    requested_by_base = {value.split('.')[0]: value for value in requested}
    if len(requested_by_base) != len(requested):
        raise ValueError('duplicate requested accession base')
    returned = {}
    parts = re.split(r'^//[ \t]*\r?$', text, flags=re.M)
    if parts[-1].strip():
        raise ValueError('incomplete GenBank response')
    for raw in parts[:-1]:
        if not raw.strip():
            continue
        data = parse_gb(raw.strip() + '\n//\n')
        base = data['acc_base']
        requested_value = requested_by_base.get(base)
        if not requested_value or base in returned:
            raise ValueError('unexpected or duplicate returned accession')
        if '.' in requested_value and requested_value != data['acc_version']:
            raise ValueError('returned accession version differs from request')
        returned[base] = (data, raw.strip() + '\n//\n')
    return returned


def main(argv=None):
    import hashlib
    from pathlib import Path
    from contextlib import closing
    ap = argparse.ArgumentParser(allow_abbrev=False)
    ap.add_argument('--db', default='')
    ap.add_argument('--out-db', help='new additive database; input is read-only')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--genus')
    ap.add_argument('--no-cache', action='store_true')
    ap.add_argument('--cache-dir', help='cache base; defaults beside selected input database')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--source', default='pdf_candidate', choices=[
        'pdf_candidate','refseq_type','nontype_fetch','attribute_candidate'])
    a = ap.parse_args(argv)
    if a.limit < 0:
        ap.error('limit must be nonnegative')
    if not a.dry_run and not a.out_db:
        ap.error('--out-db is required for an additive result')
    if a.out_db:
        _p16.require_new_output(a.out_db)
    db = Path(_p16.rrna16s_db(a.db or None)).resolve()
    input_hash = _p16.sha256_file(db)
    cache = Path(a.cache_dir or os.environ.get('SAPOTE_16S_GB_CACHE') or db.parent / 'gb_cache') / input_hash
    results = []
    with closing(_p16.database_copy(str(db))) as con:
        queue, _ = work_queue(con, a.genus, a.source)
        if a.limit:
            queue = queue[:a.limit]
        if a.dry_run:
            _LOG.info(f'DRY_RUN: {len(queue)} requests planned; no network or files written')
            return 0
        ensure_columns(con)
        eligible = []
        for request in queue:
            length, definition = con.execute('SELECT seq_len,definition FROM record WHERE acc_base=?',
                                            (request.split('.')[0],)).fetchone()
            if (length and length > 25000) or re.search(r'genome|chromosome',definition or '',re.I):
                results.append(dict(request=request,status='GENOME_EXTRACTION_REQUIRED',
                                    reason='whole-genome records require a separately bound extraction'))
            else:
                eligible.append(request)
        queue = eligible
        for i in range(0, len(queue), BATCH):
            chunk = queue[i:i + BATCH]
            try:
                body = fetch_batch(chunk)
                if not body:
                    raise ValueError('empty or failed transport response')
                returned = bind_batch(body, chunk)
            except (ValueError, RuntimeError, OSError) as exc:
                results.extend(dict(request=x, status='FETCH_HOLD', reason=str(exc)) for x in chunk)
                continue
            for request in chunk:
                base = request.split('.')[0]
                if base not in returned:
                    results.append(dict(request=request, status='NOT_RETURNED', reason='cause unknown'))
                    continue
                data, raw = returned[base]
                seq = data['seq']
                existing = con.execute('SELECT seq FROM record WHERE acc_base=?', (base,)).fetchone()[0]
                if len(seq) > 25000 or not re.search(r'16S ribosomal RNA', data['definition'], re.I):
                    results.append(dict(request=request, status='SEQUENCE_SCOPE_HOLD',
                                        reason='returned record is not a supported standalone 16S candidate'))
                    continue
                if existing and _p16.sequence(existing) != seq:
                    results.append(dict(request=request, status='SEQUENCE_CONFLICT',
                                        reason='stored sequence differs from returned sequence'))
                    continue
                raw_hash = hashlib.sha256(raw.encode()).hexdigest()
                if not a.no_cache:
                    cache.mkdir(parents=True, exist_ok=True)
                    target = cache / (raw_hash + '.gb')
                    if target.exists():
                        if _p16.sha256_file(target) != raw_hash:
                            raise ValueError('content-addressed cache integrity conflict')
                    else:
                        with target.open('x') as handle:
                            handle.write(raw)
                values = {key: data.get(key) for key, _ in EXTRA_COLS}
                values.update(acc_version=data['acc_version'], definition=data['definition'], seq=seq,
                              seq_len=len(seq), seq_md5=hashlib.md5(seq.encode()).hexdigest(),
                              seq_sha256=hashlib.sha256(seq.encode()).hexdigest(),
                              strain_qual=data.get('strain'), fetched_at=time.strftime('%Y-%m-%d'))
                con.execute('UPDATE record SET ' + ','.join(key+'=?' for key in values) +
                            ' WHERE acc_base=?', [*values.values(), base])
                results.append(dict(request=request, returned=data['acc_version'], status='STORED',
                                    raw_sha256=raw_hash, sequence_sha256=values['seq_sha256']))
            time.sleep(SLEEP)
        failed = sum(row['status'] != 'STORED' for row in results)
        if _p16.sha256_file(db) != input_hash:
            raise ValueError('selected input database changed during fetch')
        _p16.save_database(con, a.out_db, 'fetch', dict(input_sha256=input_hash,
            source=a.source, results=results, status='PARTIAL_WITH_HOLDS' if failed else 'COMPLETE'))
    _LOG.info(f'{len(results)-failed} stored; {failed} held; additive database: {a.out_db}')
    return 1 if failed else 0


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    sys.exit(main())
