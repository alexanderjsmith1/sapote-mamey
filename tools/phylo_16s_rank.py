
"""phylo 16s rank. External inputs remain outside the software bundle."""
import argparse
import math
from contextlib import closing
import csv
import os
import re
import sqlite3
import sys

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import logging
_LOG = logging.getLogger(__name__)
import _phylo16s as _p16

DB = _p16.rrna16s_db(os.environ.get("SAPOTE_16S_SQLITE"), must_exist=False)
PDFHITS = os.environ.get("PHYLO_BLAST_PDF_HITS",
                         f"{_p16.root()}/inputs/blast_pdf_hits.tsv")


ISOLATED_PCT = 98.5
RESCUE_TOP_N = 25


EASTERN_US = {
    "maine", "new hampshire", "vermont", "massachusetts", "rhode island", "connecticut",
    "new york", "new jersey", "pennsylvania", "delaware", "maryland", "district of columbia",
    "virginia", "west virginia", "north carolina", "south carolina", "georgia", "florida",
    "kentucky", "tennessee", "alabama", "mississippi", "ohio",
}


FIELDS_SUB = ("isolation_source", "host", "study_title", "definition")
FIELDS_GEO = ("geo_loc_name", "country", "subregion", "admin2")

SUBSTRATE = [
    ("sub:moss",       r"\bmoss(es)?\b|\bsphagnum\b|\bdicranum\b|\bleucobryum\b|\bpolytrichum\b|\bbryum\b"),
    ("sub:liverwort",  r"\bliverwort|\bmarchantia\b|\bhepatic(ae)?\b"),
    ("sub:hornwort",   r"\bhornwort|\banthoceros\b"),
    ("sub:lichen",     r"\blichen|\bcladonia\b|\busnea\b|\bparmelia\b|\bxanthoria\b|\bpeltigera\b"),
    ("sub:soil",       r"\bsoil\b"),
    ("sub:rhizosphere", r"\brhizospher"),
    ("sub:marine",     r"\bmarine\b|\bsea ?water\b|\bocean\b|\bsediment\b|\bBaltic\b"),
    ("sub:freshwater", r"\bfreshwater\b|\blake\b|\briver\b|\bpond\b|\bstream\b"),
    ("sub:cave",       r"\bcave\b|\bkarst\b|\bspeleo"),
    ("sub:plant",      r"\bendophyt|\broot\b|\bleaf\b|\bleaves\b|\brhizome\b|\bstem\b|\bbark\b"),
    ("sub:desert",     r"\bdesert\b|\barid\b|\bAtacama\b|\bGobi\b|\bSahara\b"),
    ("sub:compost",    r"\bcompost|\bmanure\b|\bdung\b"),
    ("sub:clinical",   r"\bclinical\b|\bsputum\b|\bblood\b|\bpatient\b|\bwound\b"),
]
HOSTS = [
    ("host:bee",     r"\bbee\b|\bbees\b|\bApis\b|\bBombus\b|\bMegachile\b|\bOsmia\b|\bAndrena\b|"
                     r"\bhoney ?bee|\bbumble ?bee|\bColletes\b|\bHalictus\b|\bXylocopa\b"),
    ("host:ant",     r"\bant\b|\bants\b|\bAtta\b|\bAcromyrmex\b|\battine\b|\bTrachymyrmex\b|"
                     r"\bCyphomyrmex\b|\bMyrmicocrypta\b|\bformicid"),
    ("host:wasp",    r"\bwasp\b|\bPhilanthus\b|\bVespula\b"),
    ("host:beetle",  r"\bbeetle\b|\bDendroctonus\b|\bcoleopter"),
    ("host:termite", r"\btermite\b|\bisopter"),
    ("host:nematode", r"\bnematode\b"),
    ("host:sponge",  r"\bsponge\b|\bPorifera\b|\bHaliclona\b|\bTheonella\b|\bDysidea\b"),
    ("host:coral",   r"\bcoral\b|\bgorgonian\b|\bAnthozoa\b|\bAcropora\b|\balcyonac"),
    ("host:tunicate", r"\btunicate\b|\bascidian\b|\bEcteinascidia\b|\bDidemnum\b"),
    ("host:mollusc", r"\bmollus[ck]\b|\bbivalve\b|\bmussel\b|\boyster\b|\bAbalone\b|\bConus\b"),
    ("host:echinoderm", r"\bsea ?cucumber\b|\bsea ?urchin\b|\bstarfish\b|\bholothur|\bechinoderm"),
    ("host:bryozoan", r"\bbryozoan\b|\bBugula\b"),
    ("host:crustacean", r"\bshrimp\b|\bcrab\b|\bcrustacean\b|\bamphipod\b|\bcopepod\b"),
    ("host:mollusc_terr", r"\bsnail\b|\bslug\b"),
    ("host:myriapod", r"\bmillipede\b|\bcentipede\b|\bdiplopod"),
    ("host:arachnid", r"\bspider\b|\bmite\b|\btick\b|\bacarin|\bAraneae\b"),
    ("host:annelid", r"\bearthworm\b|\bLumbricus\b|\bpolychaete\b"),
]


MARINE_INVERT = {"host:sponge", "host:coral", "host:tunicate", "host:mollusc", "host:echinoderm",
                 "host:bryozoan", "host:crustacean"}
TERR_INVERT = {"host:bee", "host:ant", "host:wasp", "host:beetle", "host:termite",
               "host:mollusc_terr", "host:myriapod", "host:arachnid", "host:annelid"}
INSECT_UNION = {"host:bee", "host:ant", "host:wasp", "host:beetle", "host:termite"}
BRYO_UNION = {"sub:moss", "sub:liverwort", "sub:hornwort"}


def first_match(row, fields, pattern):
    for f in fields:
        v = row.get(f) or ""
        m = re.search(pattern, v, re.I)
        if m:
            return f"{f}: {v[:120]}"
    return None


def tags_for(row):
    out = []


    ph = (row.get("phylum") or "").strip()
    if ph:
        out.append((f"tax:{ph.lower()}", f"lineage: {ph}"))
        if ph == "Actinomycetota":
            out.append(("tax:actinomycete", f"lineage: {(row.get('lineage') or '')[:120]}"))
    fam = (row.get("family") or "").strip()
    if fam:
        out.append((f"fam:{fam.lower()}", f"lineage: {fam}"))


    geo = " | ".join(str(row.get(f) or "") for f in FIELDS_GEO)
    country = (row.get("country") or "").strip()
    sub = (row.get("subregion") or "").strip()
    if country:
        out.append((f"geo:{country.lower().replace(' ', '_')}", f"geo_loc_name: {row.get('geo_loc_name')}"))
    if re.search(r"\bcanada\b", geo, re.I):
        out.append(("geo:canada", f"geo_loc_name: {row.get('geo_loc_name')}"))
        if re.search(r"\bontario\b", geo, re.I):
            out.append(("geo:ontario", f"geo_loc_name: {row.get('geo_loc_name')}"))
    if re.search(r"\bUSA\b|\bUnited States\b", geo, re.I):
        out.append(("geo:usa", f"geo_loc_name: {row.get('geo_loc_name')}"))
        if sub.lower() in EASTERN_US:
            out.append(("geo:eastern_us", f"geo_loc_name: {row.get('geo_loc_name')} "
                                          f"(project-defined region, see EASTERN_US)"))


    for tag, pat in SUBSTRATE:
        ev = first_match(row, FIELDS_SUB, pat)
        if ev:
            out.append((tag, ev))
    for tag, pat in HOSTS:
        ev = first_match(row, FIELDS_SUB, pat)
        if ev:
            out.append((tag, ev))
    got = {t for t, _ in out}
    if got & BRYO_UNION:
        out.append(("sub:bryophyte", "union of " + ", ".join(sorted(got & BRYO_UNION))))
    if got & INSECT_UNION:
        out.append(("host:insect", "union of " + ", ".join(sorted(got & INSECT_UNION))))
    if got & MARINE_INVERT:
        out.append(("host:marine_invertebrate",
                    "union of " + ", ".join(sorted(got & MARINE_INVERT))))
        out.append(("habitat:marine", "marine-invertebrate host"))
    if got & TERR_INVERT:
        out.append(("host:terrestrial_invertebrate",
                    "union of " + ", ".join(sorted(got & TERR_INVERT))))

    if "sub:marine" in got and "habitat:marine" not in {t for t, _ in out}:
        out.append(("habitat:marine", "marine substrate"))
    if got & {"sub:soil", "sub:rhizosphere", "sub:moss", "sub:lichen", "sub:cave", "sub:desert",
              "sub:compost"} or (got & TERR_INVERT):
        out.append(("habitat:terrestrial", "terrestrial substrate or host"))


    ln = len(_p16.sequence(row['seq'])) if row.get('seq') else None
    if not row.get("seq"):
        out.append(("len:no_sequence", "sequence not fetched"))
    elif ln >= 1200:
        out.append(("len:full", f"{ln} nt"))
    elif ln >= 500:
        out.append(("len:partial", f"{ln} nt — a usable tip; ranks like any other record"))
    else:
        out.append(("len:short", f"{ln} nt — under the 500 ungapped columns an identity needs"))


    defn = (row.get("definition") or "")
    acc = row.get("acc_base") or ""
    if re.match(r"^(CP|NZ|NC|AP|CM|GC[AF]|AE|BA)", acc) or "genome" in defn.lower() \
            or "chromosome" in defn.lower():
        out.append(("qual:from_genome", f"accession {acc}; {defn[:80]}"))
    elif re.search(r"16S ribosomal RNA", defn, re.I):
        out.append(("qual:gene_submission",
                    'definition mentions 16S; other deposits not assessed'))
    if row.get("is_type"):
        out.append(("qual:type_material", 'input is_type flag; source authority requires review'))
    if row.get("uncultured"):
        out.append(("qual:uncultured", f"definition: {(row.get('definition') or '')[:90]}"))
    return [(tag, 'SCREEN_ONLY: ' + evidence) for tag, evidence in out]


def priority(row, tags):
    """P1 highest likelihood of use, P5 lowest. Nothing is deleted at any tier."""
    t = {x for x, _ in tags}
    if "qual:uncultured" in t or "len:no_sequence" in t or "genome_record" in t:
        return 5, "uncultured clone, or no usable sequence stored"
    actino = "tax:actinomycete" in t
    usable = ("len:full" in t) or ("len:partial" in t)
    cohort = row.get("_cohort_genus")


    relevant = t & {"sub:bryophyte", "sub:moss", "sub:lichen", "host:insect",
                    "host:terrestrial_invertebrate",
                    "geo:canada", "geo:ontario", "geo:eastern_us"}
    if "qual:rarity_rescue" in t and usable:
        who = sorted(x.split(":", 1)[1] for x in t if x.startswith("rescue:"))
        return 1, ("saved-hit threshold screen for query strains: "
                   + ", ".join(who[:6]) + ("..." if len(who) > 6 else ""))


    if actino and usable and relevant:
        why = "actinomycete from a habitat or locality this project studies: " \
              + ", ".join(sorted(relevant))
        return 1, why + (" (and a genus this project trees)" if cohort else "")
    if actino and usable and cohort:
        return 2, "actinomycete, a genus this project trees"
    if actino and usable:
        return 3, "actinomycete, other genus"
    if usable:
        return 4, "usable sequence; actinomycete classification not established by these tags"
    return 5, "under 500 nt — too short for a comparable identity"


def rescue_tags():
    """(accession -> [tags]) for records that speak to an isolated AS strain."""
    if not PDFHITS:
        return {}, None
    if not os.path.isfile(PDFHITS):
        raise ValueError('selected saved-hit TSV is missing')
    per, incomplete = {}, set()
    with open(PDFHITS) as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            st, acc = r.get("strain", ""), (r.get("accession") or "").split(".")[0]
            if not st or not acc:
                continue
            try:
                pid = float(r.get("pct_identity"))
                if not math.isfinite(pid) or not 0 <= pid <= 100:
                    raise ValueError('invalid identity')
            except (ValueError, TypeError):
                incomplete.add(st)
                continue
            per.setdefault(st, []).append((pid, acc))
    out = {}
    isolated = 0
    for st, hits in per.items():
        hits.sort(reverse=True)
        if st in incomplete or not hits or hits[0][0] >= ISOLATED_PCT:
            continue
        isolated += 1
        for pid, acc in hits[:RESCUE_TOP_N]:
            out.setdefault(acc, []).append(
                (f"rescue:{st}", f"highest measured hit in supplied table for {st}: {hits[0][0]:.2f}%; "
                                 f"this row: {pid:.2f}%; heuristic screen, not a novelty claim"))
    return out, isolated


def main(argv=None):
    global PDFHITS
    ap = argparse.ArgumentParser(allow_abbrev=False)
    ap.add_argument('--db', default='')
    ap.add_argument('--out-db')
    ap.add_argument('--pdf-hits', help='optional explicit saved-hit TSV')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args(argv)
    if not a.dry_run and not a.out_db:
        ap.error('--out-db is required for an additive result')
    if a.out_db:
        _p16.require_new_output(a.out_db)
    db = _p16.rrna16s_db(a.db or None)
    digest = _p16.sha256_file(db)
    PDFHITS = a.pdf_hits
    rescue, n_isolated = rescue_tags()
    hits_hash = _p16.sha256_file(PDFHITS) if PDFHITS else None
    with closing(_p16.database_copy(db)) as con:
        if a.dry_run:
            _LOG.info('DRY_RUN: no database writes; ranking is a heuristic screen')
            return 0
        from phylo_16s_fetch import ensure_columns
        ensure_columns(con)
        have = {row[1] for row in con.execute('PRAGMA table_info(record)')}
        for col, typ in [('priority','INTEGER'),('priority_reason','TEXT')]:
            if col not in have:
                con.execute(f'ALTER TABLE record ADD COLUMN {col} {typ}')
        # These namespaces are generated by this ranker. Rebuild them in the new
        # output so stale positives do not survive a changed input observation.
        for prefix in ('tax:','fam:','geo:','sub:','host:','habitat:','len:','qual:','rescue:'):
            con.execute('DELETE FROM record_tag WHERE tag LIKE ?', (prefix+'%',))
        cohort = {g for (g,) in con.execute("SELECT DISTINCT genus FROM record WHERE source='as_governed'")}
        genome = {acc for (acc,) in con.execute("SELECT acc_base FROM record_tag WHERE tag='genome_record'")}
        fields = [r[1] for r in con.execute('PRAGMA table_info(record)')]
        rows = con.execute('SELECT * FROM record').fetchall()
        for values in rows:
            row = dict(zip(fields,values));row['_cohort_genus'] = row.get('genus') in cohort
            tags = tags_for(row)
            if row['acc_base'] in genome:
                tags.append(('genome_record','sequence extraction required'))
            if row['acc_base'] in rescue:
                tags.extend(rescue[row['acc_base']])
                tags.append(('qual:rarity_rescue','saved-hit threshold screen only'))
            con.executemany('INSERT OR REPLACE INTO record_tag VALUES (?,?,?)',
                            [(row['acc_base'],tag,ev) for tag,ev in tags])
            p, reason = priority(row,tags)
            con.execute('UPDATE record SET priority=?,priority_reason=? WHERE acc_base=?',
                        (p,'HEURISTIC: '+reason,row['acc_base']))
        con.execute('DROP VIEW IF EXISTS panel_candidates')
        con.execute("""CREATE VIEW panel_candidates AS SELECT
            acc_base,acc_version,source,priority,priority_reason,binomial,genus,
            phylum,family,seq_len,is_type,host,isolation_source,geo_loc_name,
            CASE WHEN seq IS NULL OR seq='' THEN 'NOT_AVAILABLE' ELSE 'AVAILABLE' END sequence_status,
            'KEYWORD_SCREEN_NOT_VALIDATED_MEMBERSHIP' tag_scope,
            (SELECT group_concat(tag,'|') FROM record_tag t WHERE t.acc_base=r.acc_base) candidate_tags
            FROM record r""")
        if _p16.sha256_file(db) != digest or (PDFHITS and _p16.sha256_file(PDFHITS) != hits_hash):
            raise ValueError('input changed during rank')
        _p16.save_database(con,a.out_db,'rank',dict(input_sha256=digest,saved_hits_sha256=hits_hash,
            rescue_status='NOT_MEASURED' if n_isolated is None else 'SCREENED',
            screened_queries=n_isolated,record_count=len(rows),status='HEURISTIC_RANK_ONLY'))
    _LOG.info(f'{len(rows)} records screened; additive database: {a.out_db}')
    return 0


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    sys.exit(main())
