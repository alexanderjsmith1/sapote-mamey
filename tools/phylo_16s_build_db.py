
"""phylo 16s build db. External inputs remain outside the software bundle."""
import argparse
from pathlib import Path
from contextlib import closing
import math
import csv
import glob
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import logging
_LOG = logging.getLogger(__name__)
import _phylo16s as _p16


R = str(_p16.root())
DB = _p16.rrna16s_db(os.environ.get("SAPOTE_16S_SQLITE"), must_exist=False)
BLASTDB = _p16.refseq_16s_blastdb()
AS_FA = os.environ.get(
    "PHYLO_AUTHORITATIVE_16S",
    f"{R}/inputs/authoritative_16s.fasta")
AS_PROV = os.environ.get("PHYLO_AS_16S_PROVENANCE",
                         f"{R}/inputs/16s_provenance.tsv")
NONTYPE = os.environ.get("PHYLO_NONTYPE_16S_DIR", f"{R}/inputs/nontype_16s")
RECT2 = os.environ.get("PHYLO_RECT2_DIR", f"{R}/inputs/reference_metadata")
PDFHITS = os.environ.get("PHYLO_BLAST_PDF_HITS",
                         f"{R}/inputs/blast_pdf_hits.tsv")


COHORTS = {
    "moss":   ("moss", "cladonia", "liverwort", "dicranum", "leucobryum", "lichen"),
    "attine": ("atta", "acromyrmex", "myrmicocrypta", "attine", "trachymyrmex", "cyphomyrmex"),
    "bee":    ("bombus", "apis", "apidae", "andrena", "wasp", "megachile", "halictus",
               "xylocopa", "colletes", "osmia"),
}


COLLECTIONS = (
    "ATCC BCRC CBS CCTCC CCUG CECT CGMCC CIP CPCC DSM DSMZ HAMBI IAM IFO IFM IMET INA JCM KACC "
    "KCC KCTC KCCM LMG MTCC NBIMCC NBRC NCAIM NCCB NCIB NCIMB NCTC NRRL PCM RIA SANK TISTR VKM "
    "VTT YIM CPCC ISP AS ACCC CFBP CGMCC JS KRIBB NRC"
).split()
COLL_RE = re.compile(r"\b(" + "|".join(COLLECTIONS) + r")[ \-_]?([0-9][0-9A-Za-z\-]{1,12})\b")

TYPE_HINT = re.compile(r"\btype strain\b", re.I)


def base_acc(a):
    """Accession without its version. NR_112082.2 -> NR_112082."""
    return (a or "").strip().split(".")[0]


def parse_title(title):
    """(binomial, genus, designation, is_type_hint) from a FASTA definition line.

    The designation is everything the record offers as a strain name — `strain X`, `str. X`, or a
    bare culture-collection number. It is deliberately NOT trimmed to a fixed width: the collection
    numbers are the join key and cutting one produces a false identity, the same failure class as
    the truncated accessions found on 2026-09-07.
    """
    t = re.sub(r"\s+", " ", (title or "").strip())
    t = re.sub(r"^[A-Z]{1,2}_?[0-9]{5,}(\.\d+)?\s+", "", t)
    t = re.sub(r"\s+16S ribosomal RNA.*$", "", t, flags=re.I)
    t = re.sub(r"\s+(partial|complete) sequence.*$", "", t, flags=re.I)
    words = t.split()
    genus = words[0] if words else ""
    if not re.fullmatch(r"[A-Z][a-z]{2,}", genus):
        genus = ""
    sp = words[1] if len(words) > 1 else ""
    binom = f"{genus} {sp}" if genus and re.fullmatch(r"[a-z-]{2,}|sp\.", sp) else genus
    m = re.search(r"\b(?:strain|str\.|isolate)\s+(.+)$", t, flags=re.I)
    desig = m.group(1).strip() if m else ""
    if not desig:
        cm = COLL_RE.search(t)
        desig = f"{cm.group(1)} {cm.group(2)}" if cm else ""
    return binom, genus, desig, bool(TYPE_HINT.search(title or ""))


def collection_ids(text):
    """Normalised culture-collection identifiers found anywhere in the text."""
    return sorted({f"{m.group(1).upper()}{m.group(2).upper()}" for m in COLL_RE.finditer(text or "")})


def norm_desig(d):
    """A free designation reduced to a comparable form: case and separators removed."""
    return re.sub(r"[^A-Za-z0-9]", "", (d or "")).upper()


def md5(s):
    return hashlib.md5(s.encode()).hexdigest()


UNCULT = re.compile(r"uncultured|\bclone\b|environmental sample", re.I)


def uncultured(title):
    return 1 if UNCULT.search(title or "") else 0


RANK = {"as_governed": 4, "refseq_type": 3, "nontype_fetch": 2, "external": 2, "pdf_candidate": 1}

UPSERT = """INSERT INTO record (acc_base,acc_version,source,definition,binomial,genus,designation,coll_ids,is_type,seq,seq_len,seq_md5,origin,uncultured) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
  ON CONFLICT(acc_base) DO UPDATE SET
    acc_version=excluded.acc_version, source=excluded.source, definition=excluded.definition,
    binomial=excluded.binomial, genus=excluded.genus, designation=excluded.designation,
    coll_ids=excluded.coll_ids, is_type=excluded.is_type, seq=excluded.seq,
    seq_len=excluded.seq_len, seq_md5=excluded.seq_md5, origin=excluded.origin,
    uncultured=excluded.uncultured
  WHERE :rank > (SELECT r2.rank FROM (SELECT 'as_governed' s, 4 rank UNION ALL
                 SELECT 'refseq_type', 3 UNION ALL SELECT 'nontype_fetch', 2 UNION ALL
                 SELECT 'external', 2 UNION ALL SELECT 'pdf_candidate', 1) r2
                 WHERE r2.s = record.source)"""


def upsert(con, rows, source):
    """Normalize sequence identity and hold conflicting accessions instead of overwriting."""
    rank = RANK[source]
    for row in rows:
        r = list(row)
        if len(r) != 14 or r[2] != source:
            raise ValueError('invalid record width or source binding')
        if r[0].startswith('LOCAL:'):
            if r[1] is not None or source != 'as_governed':
                raise ValueError('local record key cannot be an accession')
        elif _p16.accession(r[1] or r[0]).split('.')[0] != r[0]:
            raise ValueError('accession/version conflict')
        if r[9] is not None:
            r[9] = _p16.sequence(r[9]); r[10] = len(r[9]); r[11] = md5(r[9])
        old = con.execute('SELECT acc_version,seq FROM record WHERE acc_base=?',(r[0],)).fetchone()
        if old and ((old[0] and r[1] and old[0] != r[1]) or
                    (old[1] and r[9] and _p16.sequence(old[1]) != r[9])):
            raise ValueError('conflicting record version or sequence; explicit reconciliation required')
        con.execute(UPSERT.replace(':rank',str(rank)),r)


SCHEMA = """
CREATE TABLE IF NOT EXISTS record (
  acc_base    TEXT PRIMARY KEY,   -- NR_112082  (version stripped: one record, not two strains)
  acc_version TEXT,               -- NR_112082.2 as last seen
  source      TEXT NOT NULL,      -- refseq_type | as_governed | nontype_fetch | pdf_candidate | external
  definition  TEXT,
  binomial    TEXT, genus TEXT, designation TEXT,
  coll_ids    TEXT,               -- JSON list of normalised culture-collection ids
  is_type     INTEGER,            -- 1 type material, 0 explicitly not, NULL unknown
  seq         TEXT,               -- NULL for pdf_candidate rows (title harvested, sequence not yet)
  seq_len     INTEGER, seq_md5 TEXT,
  origin      TEXT,               -- file this row came from
  -- Uncultured/clone wording is a title screen, not an accepted strain identity.
  uncultured  INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_record_genus ON record(genus);
CREATE INDEX IF NOT EXISTS ix_record_binom ON record(binomial);
CREATE INDEX IF NOT EXISTS ix_record_src   ON record(source);
CREATE INDEX IF NOT EXISTS ix_record_unc   ON record(uncultured);

CREATE TABLE IF NOT EXISTS strain (
  strain_uid  TEXT PRIMARY KEY,
  binomial    TEXT, genus TEXT, designation TEXT,
  coll_ids    TEXT,
  is_type     INTEGER,
  n_records   INTEGER,
  merge_basis TEXT                -- collection_id | designation | singleton
);
CREATE INDEX IF NOT EXISTS ix_strain_genus ON strain(genus);

CREATE TABLE IF NOT EXISTS record_strain (
  acc_base   TEXT PRIMARY KEY,
  strain_uid TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_rs_uid ON record_strain(strain_uid);

-- Additive scientific review layer. The imported is_type value remains unchanged; a reviewed
-- role can correct a source-wide type-material declaration without erasing source history.
CREATE TABLE IF NOT EXISTS record_type_review (
  acc_base       TEXT PRIMARY KEY,
  reviewed_role  TEXT NOT NULL CHECK(reviewed_role IN ('type_reference','cultured_non_type_reference','exclude')),
  type_strain_of TEXT,
  evidence_url   TEXT NOT NULL,
  evidence_note  TEXT NOT NULL,
  reviewed_at    TEXT NOT NULL,
  authority      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS strain_meta (
  strain_uid TEXT NOT NULL, key TEXT NOT NULL, value TEXT, source TEXT,
  PRIMARY KEY (strain_uid, key, source)
);

CREATE TABLE IF NOT EXISTS strain_set (
  set_name   TEXT NOT NULL, strain_uid TEXT NOT NULL, note TEXT,
  PRIMARY KEY (set_name, strain_uid)
);

-- A merged group whose members' sequences disagree. Recorded, never acted on automatically:
-- one strain's two records CAN legitimately differ, so this is a question for a human.
CREATE TABLE IF NOT EXISTS merge_audit (
  strain_uid TEXT, acc_a TEXT, acc_b TEXT, containment REAL, note TEXT
);
"""


def ingest_refseq(con, type_material=False):
    """Ingest an explicitly selected BLAST source; type scope requires an operator declaration."""


    wd = _p16.space_free_workdir("phylo16s_refseq_")
    try:
        db = _p16.stage_blastdb(BLASTDB, wd)
        p = _p16.run_checked(
            [_p16.blast_bin("blastdbcmd"), "-db", db, "-entry", "all",
             "-outfmt", "%a\t%t\t%s"],
            "blastdbcmd (16S RefSeq ingest)", allow_empty_stdout=False)
    finally:
        shutil.rmtree(wd, ignore_errors=True)
    n = 0
    rows = []
    for line in p.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            raise ValueError('malformed blastdbcmd ingest row')
        acc, title, seq = parts
        _p16.accession(acc, version_required=True)
        seq = _p16.sequence(seq)
        binom, genus, desig, _ = parse_title(title)
        source = 'refseq_type' if type_material else 'external'
        rows.append((base_acc(acc), acc, source, title, binom, genus, desig,
                     json.dumps(collection_ids(title)), 1 if type_material else None, seq, len(seq), md5(seq),
                     os.path.basename(BLASTDB), uncultured(title)))
        n += 1
    if len({r[0] for r in rows}) != len(rows):
        raise ValueError('duplicate accession identity in BLAST source')
    upsert(con, rows, 'refseq_type' if type_material else 'external')
    return n


read_fasta = _p16.read_fasta

def ingest_as(con):
    """Explicit authoritative FASTA, with optional sequence-hash-bound accession metadata."""
    prov = {}
    if AS_PROV:
        with open(AS_PROV) as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            if 'strain' not in (reader.fieldnames or []):
                raise ValueError('provenance TSV requires strain column')
            for row in reader:
                strain = row['strain'].strip()
                if not strain or strain in prov:
                    raise ValueError('empty or duplicate provenance strain identity')
                prov[strain] = row
    fa = read_fasta(AS_FA)
    rows, meta, sets = [], [], []
    for hdr, seq in fa.items():
        strain = hdr.split()[0]
        pr = prov.get(strain, {})
        accession = pr.get('accession') or None
        if accession:
            _p16.accession(accession, version_required=True)
            if pr.get('sequence_sha256') != hashlib.sha256(seq.encode()).hexdigest():
                raise ValueError('accession provenance requires matching normalized sequence_sha256')
        acc = base_acc(accession) if accession else 'LOCAL:' + hashlib.sha256((strain+'\0'+seq).encode()).hexdigest()
        org = pr.get("organism_as_deposited", "") or "unclassified"
        genus = org.split()[0] if org and org[0].isupper() else ""
        rows.append((acc, accession, "as_governed",
                     f"{org} strain {strain} 16S ribosomal RNA gene", org, genus, strain,
                     "[]", None, seq, len(seq), md5(seq), os.path.basename(AS_FA), 0))
        uid = f"AS:{strain}"
        for key in ("host", "isolation_source", "geo_loc_name", "collection_date", "lat_lon"):
            v = (pr.get(key) or "").strip()
            if v:
                meta.append((uid, key, v, "operator_supplied_provenance"))

        blob = " ".join((pr.get("host", ""), pr.get("isolation_source", ""))).lower()
        for cohort, keys in COHORTS.items():
            if any(k in blob for k in keys):
                sets.append((f"cohort_{cohort}", uid, "operator-supplied host/isolation_source keyword screen"))
        sets.append(("as_all", uid, "operator-selected authoritative 16S store"))
    if set(prov) - {h.split()[0] for h in fa}:
        raise ValueError('provenance contains unmatched strain identities')
    if len({r[0] for r in rows}) != len(rows):
        raise ValueError('duplicate accession identity in authoritative FASTA')
    upsert(con, rows, "as_governed")
    con.executemany("INSERT OR REPLACE INTO strain_meta VALUES (?,?,?,?)", meta)
    con.executemany("INSERT OR REPLACE INTO strain_set VALUES (?,?,?)", sets)
    return len(rows), len(meta)


def ingest_nontype(con):
    """Non-type records already fetched for the rare-genus panels, with their rect2 metadata."""
    meta_by_acc = {}
    for p in sorted(glob.glob(f"{RECT2}/*/*_nontype_meta.tsv")) if RECT2 else []:
        for r in csv.DictReader(open(p), delimiter="\t"):
            accession = _p16.accession(r.get('accession'), version_required=True)
            if accession in meta_by_acc:
                raise ValueError('duplicate reference metadata accession')
            meta_by_acc[accession] = r
    rows, meta = [], []
    for p in sorted(glob.glob(f"{NONTYPE}/*_nontype_16S.fasta")):
        for hdr, seq in read_fasta(p).items():
            acc = hdr.split()[0]
            title = hdr.split(" ", 1)[1] if " " in hdr else hdr
            binom, genus, desig, _ = parse_title(title)
            _p16.accession(acc, version_required=True)
            b = base_acc(acc)
            rows.append((b, acc, "nontype_fetch", title, binom, genus, desig,
                         json.dumps(collection_ids(title)), None, seq, len(seq), md5(seq),
                         os.path.basename(p), uncultured(title)))
            m = meta_by_acc.get(acc, {})
            for src_key, key in (("isolation_source", "isolation_source"), ("geo", "geo_loc_name")):
                v = (m.get(src_key) or "").strip()
                if v:
                    meta.append((f"REC:{b}", key, v, "rect2_nontype_meta"))
    if not rows:
        raise ValueError('selected nontype directory contains no supported FASTA records')
    if len({r[0] for r in rows}) != len(rows):
        raise ValueError('duplicate accession identity in nontype FASTA inputs')
    if set(meta_by_acc) - {r[1] for r in rows}:
        raise ValueError('reference metadata has unmatched accession versions')
    upsert(con, rows, "nontype_fetch")
    con.executemany("INSERT OR REPLACE INTO strain_meta VALUES (?,?,?,?)", meta)
    return len(rows)


def ingest_pdf_candidates(con):
    """Ingest explicit saved-hit accession observations; sequences remain missing.

    Titles do not establish type status, strain identity or taxonomic authority.
    """
    if not os.path.isfile(PDFHITS):
        raise ValueError('selected PDF-hit TSV is missing')
    best, seen_for = {}, {}
    for r in csv.DictReader(open(PDFHITS), delimiter="\t"):
        version = _p16.accession(r.get('accession', ''))
        acc = base_acc(version)
        raw_pid = (r.get("pct_identity") or "").strip()
        if raw_pid:
            try:
                pid = float(raw_pid)
            except ValueError as exc:
                raise ValueError('invalid percent identity in PDF-hit row') from exc
            if not math.isfinite(pid) or not 0 <= pid <= 100:
                raise ValueError('invalid percent identity in PDF-hit row')
        else:
            pid = None
        subj = (r.get("subject") or "").strip()
        if acc in best and best[acc][3] != version:
            raise ValueError('PDF-hit accession version conflict')
        if acc not in best or (pid is not None and (best[acc][1] is None or pid > best[acc][1])):
            best[acc] = (subj, pid, r.get("subject_len") or "", version)
        seen_for.setdefault(acc, set()).add(r.get("strain", ""))
    have = {a for (a,) in con.execute("SELECT acc_base FROM record")}
    rows, meta = [], []
    for acc, (subj, pid, slen, version) in best.items():
        if acc in have:
            current = con.execute('SELECT acc_version FROM record WHERE acc_base=?',(acc,)).fetchone()[0]
            if current and current != version:
                raise ValueError('saved-hit accession conflicts with selected source version')
            continue


        title = re.sub(r"([a-z])([A-Z])", r"\1 \2", subj)
        binom, genus, desig, is_t = parse_title(title)
        rows.append((acc, version, "pdf_candidate", title, binom, genus, desig,
                     json.dumps(collection_ids(title)), None, None,
                     int(slen) if str(slen).isdigit() else None, None,
                     os.path.basename(PDFHITS), uncultured(subj)))
        meta.append((f"REC:{acc}", "surfaced_by_as_strains",
                     ",".join(sorted(x for x in seen_for[acc] if x)), "blast_pdf_harvest"))
    upsert(con, rows, "pdf_candidate")
    con.executemany("INSERT OR REPLACE INTO strain_meta VALUES (?,?,?,?)", meta)
    return len(rows), len(best)


def resolve_strains(con):
    """Collapse records onto strain identities. See the module docstring for the rule."""
    recs = list(con.execute(
        "SELECT acc_base, binomial, genus, designation, coll_ids, is_type, source FROM record"))
    parent = {}

    def find(x):
        while parent.get(x, x) != x:
            parent[x] = parent.get(parent[x], parent[x])
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    by_coll, by_desig = {}, {}
    basis = {}
    for acc, binom, genus, desig, colls, is_type, source in recs:
        parent.setdefault(acc, acc)
        if source == "as_governed":
            continue
        if not binom or binom.endswith(" sp."):
            continue
        for cid in json.loads(colls or "[]"):
            k = (binom, cid)
            if k in by_coll:
                union(by_coll[k], acc)
                basis[find(acc)] = "collection_id"
            else:
                by_coll[k] = acc
        # PDF text is a lossy observation surface.  A parsed designation alone cannot
        # establish that two accessions are the same strain; culture-collection IDs can
        # propose that grouping and remain reviewable through merge_audit.
        if source == "pdf_candidate":
            continue
        nd = norm_desig(desig)
        if len(nd) >= 3:
            k = (binom, nd)
            if k in by_desig:
                union(by_desig[k], acc)
                basis.setdefault(find(acc), "designation")
            else:
                by_desig[k] = acc

    groups = {}
    for acc, *_ in recs:
        groups.setdefault(find(acc), []).append(acc)

    info = {r[0]: r for r in recs}
    strains, links = [], []
    for root, members in groups.items():
        rows = [info[m] for m in members]


        rows.sort(key=lambda r: (-(r[5] or 0), -len(json.loads(r[4] or "[]")), r[0]))
        head = rows[0]
        acc, binom, genus, desig, colls, is_type, source = head
        if source == "as_governed":
            uid = f"AS:{desig}"
        else:
            uid = ('REC:' + acc if len(members) == 1 else
                   'GROUP:' + hashlib.sha256('\n'.join(sorted(members)).encode()).hexdigest())
        allc = sorted({c for m in members for c in json.loads(info[m][4] or "[]")})
        if any(s[0] == uid for s in strains):
            raise ValueError('duplicate strain identity; explicit multi-record reconciliation required')
        strains.append((uid, binom, genus, desig, json.dumps(allc), is_type, len(members),
                        basis.get(root, "singleton")))
        for m in members:
            links.append((m, uid))
    con.execute("DELETE FROM strain")
    con.execute("DELETE FROM record_strain")
    con.executemany("INSERT OR REPLACE INTO strain VALUES (?,?,?,?,?,?,?,?)", strains)
    con.executemany("INSERT OR REPLACE INTO record_strain VALUES (?,?)", links)
    for acc, uid in links:
        for key, value, source in con.execute('SELECT key,value,source FROM strain_meta WHERE strain_uid=?',('REC:'+acc,)).fetchall():
            old = con.execute('SELECT value FROM strain_meta WHERE strain_uid=? AND key=? AND source=?',(uid,key,source)).fetchone()
            if old and old[0] != value:
                if key == "surfaced_by_as_strains" and source == "blast_pdf_harvest":
                    merged = ",".join(sorted(set(old[0].split(",")) | set(value.split(","))))
                    con.execute('UPDATE strain_meta SET value=? WHERE strain_uid=? AND key=? AND source=?',
                                (merged, uid, key, source))
                    continue
                raise ValueError('conflicting metadata within proposed strain group')
            con.execute('INSERT OR IGNORE INTO strain_meta VALUES (?,?,?,?)',(uid,key,value,source))
    return len(strains), sum(1 for s in strains if s[6] > 1)


def audit_merges(con, k=16, floor=0.90):
    """K-mer containment screen only; alignment and owner review remain required.

    Containment uses distinct shared k-mers over the smaller distinct k-mer set.
    It does not prove a strain merge, sequence identity or biological absence.
    """
    con.execute("DELETE FROM merge_audit")
    out = []
    for (uid,) in con.execute("SELECT strain_uid FROM strain WHERE n_records > 1"):
        seqs = list(con.execute(
            "SELECT r.acc_base, r.seq FROM record r JOIN record_strain rs USING(acc_base) "
            "WHERE rs.strain_uid = ? AND r.seq IS NOT NULL", (uid,)))
        for i in range(len(seqs)):
            for j in range(i + 1, len(seqs)):
                a, sa = seqs[i]
                b, sb = seqs[j]
                ka = {sa[x:x + k] for x in range(len(sa) - k + 1)}
                kb = {sb[x:x + k] for x in range(len(sb) - k + 1)}
                if not ka or not kb:
                    continue
                shared = len(ka & kb)
                contain = shared / min(len(ka), len(kb))
                if contain < floor:
                    out.append((uid, a, b, round(contain, 3),
                                f"{k}-mer containment {contain:.3f} below {floor} "
                                f"({len(sa)} nt vs {len(sb)} nt); needs a pairwise alignment before "
                                f"the merge is trusted"))
    con.executemany("INSERT INTO merge_audit VALUES (?,?,?,?,?)", out)
    return len(out)


def build_sets(con):
    """Named strain sets. Membership is many-to-many: a strain can be type material AND a cohort
    isolate AND a published comparator, and a tree may draw on any combination."""
    rows = []
    for uid, is_type, src in con.execute(
            "SELECT s.strain_uid, s.is_type, (SELECT r.source FROM record r "
            "JOIN record_strain rs USING(acc_base) WHERE rs.strain_uid = s.strain_uid LIMIT 1) "
            "FROM strain s"):
        if src == "refseq_type":
            rows.append(("type_refseq", uid, "NCBI 16S RefSeq, type material"))
        elif src == "nontype_fetch":
            rows.append(("nontype_fetched", uid, "fetched for a rare-genus panel"))
        elif src == "pdf_candidate":
            rows.append(("nontype_candidate", uid, "seen in a saved BLAST PDF; sequence not fetched"))
    con.executemany("INSERT OR REPLACE INTO strain_set VALUES (?,?,?)", rows)

    con.execute("DELETE FROM strain_set WHERE strain_uid NOT IN (SELECT strain_uid FROM strain)")
    return len(rows)


def main(argv=None):
    global DB, BLASTDB, AS_FA, AS_PROV, NONTYPE, RECT2, PDFHITS
    ap = argparse.ArgumentParser(allow_abbrev=False)
    ap.add_argument('--db', required=True, help='new output SQLite database')
    ap.add_argument('--refseq-blastdb', help='explicit BLAST database prefix')
    ap.add_argument('--refseq-type-material', action='store_true',
                    help='operator declares selected BLAST source contains type material only')
    ap.add_argument('--authoritative-fasta')
    ap.add_argument('--provenance', help='TSV; accessions require normalized sequence_sha256 binding')
    ap.add_argument('--nontype-dir')
    ap.add_argument('--reference-metadata-dir')
    ap.add_argument('--pdf-hits')
    ap.add_argument('--sets-only', action='store_true')
    ap.add_argument('--input-db', help='existing source for --sets-only')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args(argv)
    _p16.require_new_output(a.db)
    selected = [a.refseq_blastdb,a.authoritative_fasta,a.nontype_dir,a.pdf_hits]
    if a.sets_only:
        if not a.input_db or any(selected):
            ap.error('--sets-only requires --input-db and excludes ingest sources')
    elif not any(selected) or a.input_db:
        ap.error('select at least one explicit ingest source; input-db requires sets-only')
    if a.provenance and not a.authoritative_fasta:
        ap.error('--provenance requires --authoritative-fasta')
    if a.reference_metadata_dir and not a.nontype_dir:
        ap.error('--reference-metadata-dir requires --nontype-dir')
    if a.refseq_type_material and not a.refseq_blastdb:
        ap.error('--refseq-type-material requires --refseq-blastdb')
    files = []
    for kind, value in [('authoritative_fasta',a.authoritative_fasta),('provenance',a.provenance),
                        ('pdf_hits',a.pdf_hits),('input_db',a.input_db)]:
        if value:
            path = Path(value).resolve(strict=True)
            if not path.is_file():
                raise ValueError('selected input is not a file')
            files.append((kind,path))
    for kind, directory, pattern in [('nontype',a.nontype_dir,'*_nontype_16S.fasta'),
                                    ('reference_metadata',a.reference_metadata_dir,'*/*_nontype_meta.tsv')]:
        if directory:
            path = Path(directory).resolve(strict=True)
            matched = sorted(path.glob(pattern))
            if not path.is_dir() or not matched:
                raise ValueError('selected directory has no supported input files')
            files.extend((kind,p) for p in matched)
    if a.refseq_blastdb:
        prefix = Path(a.refseq_blastdb).resolve()
        members = sorted(p for p in prefix.parent.glob(prefix.name+'.*') if p.is_file())
        if not members:
            raise ValueError('selected BLAST prefix has no files')
        files.extend(('blast_member',p) for p in members)
    sources = [dict(role=kind,name=p.name,sha256=_p16.sha256_file(p)) for kind,p in files]
    if a.dry_run:
        _LOG.info(f'DRY_RUN: {len(files)} source files bound; no ingest or output writes')
        return 0
    DB, BLASTDB = a.db, a.refseq_blastdb
    AS_FA, AS_PROV, NONTYPE, RECT2, PDFHITS = (a.authoritative_fasta,a.provenance,a.nontype_dir,
                                            a.reference_metadata_dir,a.pdf_hits)
    with closing(_p16.database_copy(a.input_db) if a.sets_only else sqlite3.connect(':memory:')) as con:
        if not a.sets_only:
            con.executescript(SCHEMA)
            if BLASTDB: ingest_refseq(con, a.refseq_type_material)
            if AS_FA: ingest_as(con)
            if NONTYPE: ingest_nontype(con)
            if PDFHITS: ingest_pdf_candidates(con)
        resolve_strains(con)
        audit_merges(con)
        build_sets(con)
        from phylo_16s_fetch import ensure_columns
        ensure_columns(con)
        con.execute('UPDATE record SET seq_sha256=NULL')
        for acc, seq in con.execute('SELECT acc_base,seq FROM record WHERE seq IS NOT NULL').fetchall():
            con.execute('UPDATE record SET seq_sha256=? WHERE acc_base=?',
                        (hashlib.sha256(_p16.sequence(seq).encode()).hexdigest(),acc))
        for source, (_,path) in zip(sources,files):
            if source['sha256'] != _p16.sha256_file(path):
                raise ValueError('source changed during build')
        _p16.save_database(con,a.db,'build',dict(sources=sources,
            type_material_scope='operator_declared' if a.refseq_type_material else 'UNKNOWN',
            strain_merge_authority='HEURISTIC_GROUPS_REQUIRE_REVIEW'))
    _LOG.info(f'Additive 16S database written: {a.db}')
    return 0


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    sys.exit(main())
