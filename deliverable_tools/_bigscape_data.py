#!/usr/bin/env python3
"""_bigscape_data.py — shared, read-only extraction helpers for the Sapote-Mamey BiG-SCAPE
cohort widgets (strain x GCF-family matrix + clinker-style within-family gene alignments).

Graduated into the engine as a first-class deliverable helper (v9.7.349x candidate). It is
imported by ``bigscape_matrix_widget.py`` and ``bigscape_clinker_widget.py`` in this same
directory (run standalone: ``python deliverable_tools/bigscape_matrix_widget.py --db <path>``).

Source of truth: the BiG-SCAPE 2.x SQLite cohort DB (``full_cohort.db``) produced by the
AS + Type + SID run (run label full_cohort_AS_Type_SID_2026-07-18). Everything is derived
from that DB — CDS coordinates, gene_kind, Pfam HSP hits, and the GCF ``family`` table.

Stdlib-only (sqlite3 + re + collections). No network, no external assets.

Claim-safety: GCF membership and gene "orthogroups" here are *sequence-similarity
clustering* (BiG-SCAPE distance + shared Pfam domains), class-level only. "AS-private" means
no Type/SID reference member fell in the family at this cutoff — a novelty *prior*, not proof.
Comparators (Type/SID members) are similarity anchors, not identity calls. Judgment deferred.
"""
from __future__ import annotations
import os, re, sqlite3, collections

# Documented default location of the BiG-SCAPE 2.x cohort DB. Override with --db on any
# generator (run standalone: `python deliverable_tools/bigscape_matrix_widget.py --db <path>`).
# NOTE: the bigscape-widgets CLI subcommand wiring (cards AUG3_08/11) is a tracked .350-rebaseline
# follow-up — the shipped cli.py diffs were cut against .349x and do not apply to the .350 base.
DB_DEFAULT = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd()) + "/sessions/Red/bigscape_cohort_AS_Type_SID/full_cohort.db"

# Enriched domain-depth cohort table + the (strain,contig,region)->bgc_id map live here. Used by
# the clinker overlay to join each AS track to its Sapote/Mamey verdict row (READER-SIDE ONLY —
# nothing here recomputes depth or tiers; it reconciles with already-built tables).
DOMAIN_DEPTH_DIR = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd()) + "/strain_data/_DOMAIN_DEPTH"


def strain_of(path: str, organism: str):
    """Return (strain_label, cohort_class) for a gbk row. class in {AS, SID, Type}."""
    b = os.path.basename(path or "")
    m = re.match(r"(AS-\d+)", b)
    if m:
        return m.group(1), "AS"
    m = re.search(r"SID\d+", b)
    if m:
        return m.group(0), "SID"
    if organism and "SID" in organism:
        mm = re.search(r"SID\d+", organism)
        if mm:
            return mm.group(0), "SID"
    # Named reference/type genomes folded into a re-run with the tip label encoded in the FILENAME
    # (the phylogenomics lane tree×GCF overlay, 2026-08-05). Convention: `Genus_species_strain[__<contig>].regionNNN.gbk`
    # — UNDERSCORES in the taxon (existing cohort Type gbks use SPACES, so they keep their prior labels).
    # Returned verbatim to match GToTree phylogeny tips. `__` separates an optional contig suffix; else a
    # trailing `_NODE/_scaffold/_contig/_ctg/_tig_…` locator is stripped.
    if re.match(r"[A-Z][A-Za-z0-9]+_[a-z0-9]+_", b):
        stem = re.sub(r"\.region\d+\.gbk$", "", b)
        stem = stem.split("__", 1)[0]
        stem = re.sub(r"_(NODE|scaffold|contig|ctg|tig)_.*$", "", stem, flags=re.I)
        return stem[:60] or "ref", "Ref"
    if organism and organism not in (".", "", "Unknown"):
        return " ".join(organism.split()[:3]), "Type"
    return re.sub(r"\.region\d+\.gbk$", "", b)[:40] or "unknown", "Type"


def gbk_index(con):
    """gbk_id -> (strain_label, cohort_class)."""
    idx = {}
    for gid, path, org in con.execute("select id, path, organism from gbk"):
        idx[gid] = strain_of(path, org)
    return idx


def family_members(con, cutoff=0.3):
    """family_id -> list of dicts {record_id, gbk_id, product, nt_start, nt_stop, strain, cls}."""
    idx = gbk_index(con)
    fam = collections.defaultdict(list)
    q = """select bf.family_id, r.id, r.gbk_id, r.product, r.nt_start, r.nt_stop
           from bgc_record_family bf
           join family f on f.id = bf.family_id
           join bgc_record r on r.id = bf.record_id
           where f.cutoff = ?"""
    for fid, rid, gbkid, prod, a, b in con.execute(q, (cutoff,)):
        s, cl = idx.get(gbkid, ("?", "?"))
        fam[fid].append(dict(record_id=rid, gbk_id=gbkid, product=prod or "",
                             nt_start=a, nt_stop=b, strain=s, cls=cl))
    return fam


def sm_annotation_index(depth_dir=DOMAIN_DEPTH_DIR):
    """Build a callable ``annot_for(gbk_path) -> str|None`` that joins one clinker track (an AS
    region gbk) to its enriched Sapote/Mamey verdict row, reconciled from already-built tables:

      gbk basename  ->  (strain, contig, region_number)          [regex on <strain>_<contig>.regionNNN.gbk]
                    ->  bgc_id                                    [bgc_region_map.tsv]
                    ->  {tier, lead_priority, reference_dark, activity}   [domain_depth_cohort.tsv]

    Returns None for SID/Type paths (comparators/anchors carry no verdict) and for any AS region
    absent from the maps. The formatted string is compact, e.g. "Low · pri 82 · DARK 57% · AF·self-res×2".
    All values are class-level CAPACITY / routing priors, never phenotype — judgment deferred.
    """
    region_map = {}  # (strain, contig, region_number) -> bgc_id
    mp = os.path.join(depth_dir, "bgc_region_map.tsv")
    if os.path.exists(mp):
        with open(mp) as fh:
            next(fh, None)  # header
            for line in fh:
                p = line.rstrip("\n").split("\t")
                if len(p) >= 4 and p[2].isdigit():
                    region_map[(p[0], p[1], int(p[2]))] = p[3]
    enrich = {}  # (strain, bgc_id) -> row dict
    cp = os.path.join(depth_dir, "domain_depth_cohort.tsv")
    if os.path.exists(cp):
        with open(cp) as fh:
            hdr = fh.readline().rstrip("\n").split("\t")
            for line in fh:
                vals = line.rstrip("\n").split("\t")
                row = dict(zip(hdr, vals))
                enrich[(row.get("strain"), row.get("bgc"))] = row

    def _compact_activity(a):
        # drop the parenthetical mechanism detail and tighten the " · " joiner to stay one-line
        a = re.sub(r"\s*\([^)]*\)", "", a or "").strip()
        return a.replace(" · ", "·")

    def annot_for(gbk_path):
        # The BiG-SCAPE input filenames are <strain>[decoration]_<contig>.regionNNN.gbk. Tolerate two
        # provenance decorations seen in the 2026-07-18 cohort DB: a " (N)" duplicate-file suffix
        # (e.g. "AS-XXX (1)_NODE_19...") and a "_new" re-run tag (e.g. "AS-XXX_new_NODE_29..."). The
        # contig is still matched EXACTLY against bgc_region_map.tsv, so a bad strip just misses (None)
        # rather than mis-annotating.
        m = re.match(r"(AS-\d+)(?: \(\d+\)|_new)?_(.+)\.region(\d+)\.gbk$",
                     os.path.basename(gbk_path or ""))
        if not m:
            return None  # SID/Type comparators (or non-AS) get no verdict overlay
        strain, contig, region = m.group(1), m.group(2), int(m.group(3))
        bgc = region_map.get((strain, contig, region))
        if not bgc:
            return None
        row = enrich.get((strain, bgc))
        if not row:
            return None
        parts = []
        tier = (row.get("tier") or "").strip()
        if tier:
            parts.append(tier)
        lp = (row.get("lead_priority") or "").strip()
        if lp:
            try:
                parts.append("pri %d" % round(float(lp)))
            except ValueError:
                pass
        rd = (row.get("reference_dark") or "").strip()
        if rd:
            parts.append(rd)
        act = _compact_activity(row.get("activity"))
        if act:
            parts.append(act)
        return " · ".join(parts) or None

    return annot_for


def genes_for_gbk(con, gbk_id):
    """Return list of gene dicts for one region gbk, sorted by nt_start.
    Each gene: {orf, x0, x1, strand, gene_kind, aa, pfams:[...], og, _aa}.
    og (orthogroup) = dominant Pfam accession (max bit_score) or None.
    Coordinates are relative to the region's own min nt_start (0-based bp).
    `_aa` carries the raw amino-acid sequence (consumed and stripped by
    bigscape_clinker_widget.cluster_dark_proteins() before the JSON payload is built,
    so it never reaches the client) -- required for reference-dark (no shared-Pfam)
    proteins to be linkable by sequence similarity; `aa` stays the display length."""
    rows = con.execute(
        "select id, nt_start, nt_stop, orf_num, strand, gene_kind, aa_seq from cds "
        "where gbk_id=? order by nt_start", (gbk_id,)).fetchall()
    if not rows:
        return []
    base = min(r[1] for r in rows)
    genes = []
    for cid, a, b, orf, strand, kind, aa in rows:
        hsps = con.execute(
            "select accession, bit_score from hsp where cds_id=? order by bit_score desc",
            (cid,)).fetchall()
        pfams, seen = [], set()
        for acc, _sc in hsps:
            if acc not in seen:
                seen.add(acc); pfams.append(acc)
        genes.append(dict(orf=orf, x0=a - base, x1=b - base,
                          strand=-1 if strand in (-1, "-", "-1") else 1,
                          gene_kind=kind or "", aa=len(aa) if aa else None,
                          pfams=pfams, og=pfams[0] if pfams else None, _aa=aa))
    return genes
