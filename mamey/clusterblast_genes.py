"""ClusterBlast per-gene correspondence layer (v9.7.100, P-CBG).

WHY THIS EXISTS
---------------
RG-GMCI parses the ClusterBlast "Table of Blast hits" but keeps only (subject_locus, %identity) for its
adjacency/tiling math. It discards the QUERY GENE, the per-hit BLAST score, and the %coverage. That means
the engine can score that NODE_182 hits AT2433-A1, and (since P-ST) which subject genes it hits — but it
never retains WHICH QUERY CDS maps to WHICH reference gene, at what identity and coverage. That per-gene
correspondence is exactly what is needed to characterise a locus against its reference (e.g. "ctg182_7,
the indsynth core gene, hits the AT2433-A1 bis-indole synthase at 51% identity over 99% coverage"), and it
is the artifact that has had to be reconstructed by hand from the TXT on every indolocarbazole pass.

WHAT THIS DOES
--------------
Parses the FULL hit table (query gene, subject gene, %identity, blast_score, %coverage, e-value) for every
ClusterBlast reference block in every per-BGC TXT, and emits:
  * per_gene_best_hit : for each query CDS, its single best reference-gene hit (by blast score) across the
                        top references, with the reference it came from.
  * reference_correspondence : per (BGC, reference) the ordered query->subject gene map, so a whole locus
                        can be read against one reference cluster.

CLAIM SAFETY
------------
ClusterBlast %identity is SIMILARITY to a reference protein, not identity of product. A hit to an
indolocarbazole core gene is capacity evidence ("biosynthetic capacity consistent with"), never a
production or compound-identity claim. This module is deterministic Mamey extraction; it makes no judgment.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import re
import zipfile

from .antismash_evidence import _region_key_from_name
from .ziputil import regular_file_names


# A reference block in a ClusterBlast TXT, with its full per-gene hit table retained.
@dataclass
class ClusterBlastHit:
    query_gene: str
    subject_gene: str
    pct_identity: float | None
    blast_score: float | None
    pct_coverage: float | None
    evalue: str


@dataclass
class ReferenceBlock:
    bgc_id: str
    region_key: str
    rank: int
    ref: str
    source: str
    reference_type: str
    nprot: int | None
    cumulative_score: float | None
    hits: list[ClusterBlastHit]


_HIT_TABLE_RE = re.compile(r"Table of Blast hits.*?\n(.*)", re.S)


def _parse_hit_rows(block: str) -> list[ClusterBlastHit]:
    """Parse the 6-column Blast-hits table: query, subject, %id, blast_score, %coverage, e-value.

    Columns are bare numbers in this antiSMASH format. Rows with fewer than 6 tab fields, or a
    non-numeric %identity in column 3, are skipped (header/blank lines)."""
    out: list[ClusterBlastHit] = []
    m = _HIT_TABLE_RE.search(block)
    if not m:
        return out
    for line in m.group(1).splitlines():
        parts = line.split("\t")
        if len(parts) < 6:
            continue
        try:
            pid = float(parts[2])
        except ValueError:
            continue  # header row or non-data line
        q = parts[0].strip()
        s = parts[1].strip()
        if not q or not s:
            continue

        def _f(x: str) -> float | None:
            try:
                return float(x)
            except ValueError:
                return None

        out.append(ClusterBlastHit(
            query_gene=q, subject_gene=s, pct_identity=pid,
            blast_score=_f(parts[3]), pct_coverage=_f(parts[4]), evalue=parts[5].strip(),
        ))
    return out


def _split_blocks(text: str) -> list[str]:
    return re.split(r"\n>>\n", text)[1:]


def _parse_one_txt(name: str, text: str, bgc_by_key: dict[str, Any]) -> list[ReferenceBlock]:
    _, _, region_key = _region_key_from_name(name)
    bgc = bgc_by_key.get(region_key) if region_key else None
    if bgc is None:
        return []
    blocks: list[ReferenceBlock] = []
    for block in _split_blocks(text):
        ref_m = re.search(r"\d+\.\s+(\S+)", block)
        if not ref_m:
            continue
        ref = ref_m.group(1)
        rank_m = re.match(r"\s*(\d+)\.", block)
        src = re.search(r"Source:\s*(.+)", block)
        typ = re.search(r"Type:\s*(.+)", block)
        np_ = re.search(r"Number of proteins with BLAST hits to this cluster:\s*(\d+)", block)
        cs = re.search(r"Cumulative BLAST score:\s*([\d.]+)", block)
        hits = _parse_hit_rows(block)
        if not hits:
            continue
        blocks.append(ReferenceBlock(
            bgc_id=bgc.bgc_id, region_key=region_key, rank=int(rank_m.group(1)) if rank_m else 9999,
            ref=ref, source=src.group(1).strip() if src else "",
            reference_type=typ.group(1).strip() if typ else "",
            nprot=int(np_.group(1)) if np_ else None,
            cumulative_score=float(cs.group(1)) if cs else None,
            hits=hits,
        ))
    return blocks


def parse_clusterblast_gene_map(zip_path: str | Path, bgcs: list[Any], top_refs: int = 5) -> dict[str, Any]:
    """Parse per-gene ClusterBlast correspondence for every BGC.

    top_refs caps how many top-ranked references contribute to the per-gene best-hit search (the full set
    is parsed; only the best-hit aggregation is capped, to keep the per-gene call anchored on the strongest
    references rather than a long tail of weak homologs)."""
    bgc_by_key = {f"{b.contig}_c{int(b.region_number)}": b
                  for b in bgcs if getattr(b, "contig", None) and getattr(b, "region_number", None) is not None}
    blocks_by_bgc: dict[str, list[ReferenceBlock]] = {}
    parse_errors = 0
    with zipfile.ZipFile(zip_path) as zf:
        for nm in regular_file_names(zf):
            low = nm.lower()
            if not low.endswith(".txt"):
                continue
            if "clusterblast" not in low and "knownclusterblast" not in low:
                continue
            try:
                for blk in _parse_one_txt(nm, zf.read(nm).decode("utf-8", "replace"), bgc_by_key):
                    blocks_by_bgc.setdefault(blk.bgc_id, []).append(blk)
            except Exception:  # pragma: no cover - defensive
                parse_errors += 1

    per_gene: dict[str, list[dict[str, Any]]] = {}
    correspondence: dict[str, list[dict[str, Any]]] = {}
    for bgc_id, blocks in blocks_by_bgc.items():
        blocks_sorted = sorted(blocks, key=lambda b: b.rank)
        # Per-gene best hit: across the top_refs references, the single highest-blast-score hit per query CDS.
        best: dict[str, dict[str, Any]] = {}
        for blk in blocks_sorted[:top_refs]:
            for h in blk.hits:
                cur = best.get(h.query_gene)
                cand = {
                    "query_gene": h.query_gene, "subject_gene": h.subject_gene,
                    "pct_identity": h.pct_identity, "pct_coverage": h.pct_coverage,
                    "blast_score": h.blast_score, "evalue": h.evalue,
                    "reference": blk.ref, "reference_source": blk.source,
                    "reference_rank": blk.rank,
                }
                if cur is None or (h.blast_score or 0) > (cur["blast_score"] or 0):
                    best[h.query_gene] = cand
        per_gene[bgc_id] = [best[k] for k in sorted(best, key=_gene_sort_key)]
        # Reference correspondence: for the top references, the ordered query->subject map for the whole locus.
        corr: list[dict[str, Any]] = []
        for blk in blocks_sorted[:top_refs]:
            corr.append({
                "reference": blk.ref, "reference_source": blk.source,
                "reference_type": blk.reference_type, "reference_rank": blk.rank,
                "nprot": blk.nprot, "cumulative_score": blk.cumulative_score,
                "gene_map": [
                    {"query_gene": h.query_gene, "subject_gene": h.subject_gene,
                     "pct_identity": h.pct_identity, "pct_coverage": h.pct_coverage,
                     "blast_score": h.blast_score}
                    for h in sorted(blk.hits, key=lambda x: _gene_sort_key(x.query_gene))
                ],
            })
        correspondence[bgc_id] = corr

    return {
        "status": "PASS" if blocks_by_bgc else "NULL_NO_CLUSTERBLAST_GENE_HITS",
        "per_gene_best_hit": per_gene,
        "reference_correspondence": correspondence,
        "bgc_count": len(blocks_by_bgc),
        "parse_error_count": parse_errors,
        "claim_safety": ("ClusterBlast %identity is similarity to a reference protein, not product identity. "
                         "Per-gene hits are capacity evidence only."),
    }


def _gene_sort_key(gene: str):
    """Sort ctg<contig>_<n> by the trailing gene number so the locus reads 5'->3' by CDS order."""
    m = re.search(r"_(\d+)$", gene or "")
    return (0, int(m.group(1))) if m else (1, gene)


# ── BGC functional-role profiling for rescue complementarity (v9.7.100, P-CBDB) ──────────
# A homology-based contig rescue is only credible when the two fragments are FUNCTIONALLY COMPLEMENTARY:
# one carries biosynthetic-core genes (the assembly line / synthase), the other carries tailoring,
# transport, or regulatory genes — together making one plausible cluster, not two copies of the same part.
# antiSMASH writes a gene_kind qualifier (biosynthetic / biosynthetic-additional / transport / regulatory /
# other) and gene_functions/sec_met text on every CDS; this turns those into a per-BGC role profile.

_CORE_DOMAIN_HINTS = (
    "indsynth", "iuca_iucc", "pks_ks", "ketoacyl", "condensation", "amp-binding", "lant_dehydr",
    "lanc_like", "terpene_synth", "dxs", "phytoene", "ycao", "pf00067",
    # NOTE (AUDIT_377): 'asn_synthase' deliberately excluded. bgc_decomp.py's own
    # _classify_gene() already ruled this domain "too promiscuous" to trust alone -- it is a
    # widespread primary-metabolism enzyme that also happens to be the lasso-peptide cyclase
    # (see bgc_decomp.py's "NOT added: ... Asn_synthase (too promiscuous)" comment and
    # test_bgc_decomp.py::_classify_gene("Asn_synthase") == "unknown"). Trusting it here as an
    # unconditional CORE trigger let one incidental primary-metabolism gene swept into a BGC
    # region window inflate a fragment's core-fraction and flip a genuinely ACCESSORY_ONLY
    # rescue pair into a false COMPLEMENTARY claim. A genuine antiSMASH-rule-confirmed lasso
    # cyclase still classifies core via gene_kind == "biosynthetic" below.
)
_TAILORING_HINTS = (
    "p450", "monooxygenase", "methyltransferase", "halogenase", "glycos_transf", "mgt", "rmld",
    "oxidoreductase", "dehydrogenase", "reductase", "aminotran", "degt", "acetyltransferase",
    "hydroxylase", "epimerase", "nucleotid",
)
_TRANSPORT_HINTS = ("abc_tran", "transporter", "permease", "mfs", "efflux", "major facilitator")
_REGULATORY_HINTS = ("regulator", "tetr", "luxr", "sarp", "marr", "response_reg", "hth", "transcriptional")


def _role_of(gene_kind: str, blob: str) -> str:
    """Classify one CDS into core / tailoring / transport / regulatory / other from gene_kind + text."""
    gk = (gene_kind or "").lower()
    t = (blob or "").lower()
    if gk == "biosynthetic" or any(h in t for h in _CORE_DOMAIN_HINTS):
        return "core"
    if any(h in t for h in _TRANSPORT_HINTS):
        return "transport"
    if any(h in t for h in _REGULATORY_HINTS) or gk == "regulatory":
        return "regulatory"
    if gk == "biosynthetic-additional" or any(h in t for h in _TAILORING_HINTS):
        return "tailoring"
    if gk == "transport":
        return "transport"
    return "other"


def functional_profile_from_gene_context(gene_ctx: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Per-BGC functional-role counts from sealed gene context.

    gene_ctx: {bgc_id: [ {gene_kind?, gene_functions, sec_met_domains, ...}, ... ]}.
    Returns {bgc_id: {core, tailoring, transport, regulatory, other, has_core, roles_present}}.
    """
    out: dict[str, dict[str, Any]] = {}
    for bgc_id, rows in (gene_ctx or {}).items():
        counts = {"core": 0, "tailoring": 0, "transport": 0, "regulatory": 0, "other": 0}
        for r in rows:
            blob = " ".join(filter(None, [
                r.get("gene_functions", "") if isinstance(r.get("gene_functions"), str) else " ".join(r.get("gene_functions", []) or []),
                "; ".join(r.get("sec_met_domains", []) or []),
                r.get("product", "") or "",
            ]))
            counts[_role_of(r.get("gene_kind", ""), blob)] += 1
        roles_present = {k for k, v in counts.items() if v and k != "other"}
        out[bgc_id] = {**counts, "has_core": counts["core"] > 0, "roles_present": sorted(roles_present)}
    return out


def _core_fraction(prof: dict[str, Any]) -> float:
    """Fraction of biosynthetically-relevant genes that are CORE (core / core+tailoring+transport+reg)."""
    rel = (prof.get("core", 0) + prof.get("tailoring", 0)
           + prof.get("transport", 0) + prof.get("regulatory", 0))
    return (prof.get("core", 0) / rel) if rel else 0.0


# Calibrated on AS-XXX HIGH pairs: genuine paralogs (both fragments carry a near-complete core) sit at
# core-fraction ~0.4-0.55 on BOTH sides; real splits show one fragment accessory-dominated (core-fraction
# well below the other). A pair is COMPLEMENTARY when the two core-fractions differ by at least this much
# AND the lower side is accessory-dominated; BOTH_CORE when both are core-rich and similar.
FRC_ASYMMETRY_MIN = 0.20          # min core-fraction gap to call a split complementary
FRC_ACCESSORY_CEILING = 0.30      # a fragment with core-fraction <= this is accessory-dominated
FRC_CORE_FLOOR = 0.35             # both sides above this (and similar) => both carry a real core => paralog


def rescue_functional_complementarity(prof_a: dict[str, Any], prof_b: dict[str, Any]) -> dict[str, Any]:
    """Assess whether two BGC fragments are functionally complementary for a rescue.

    Uses RELATIVE core burden (core-fraction), not a binary has-core test: every called BGC has some core
    gene, so 'does it have a core' is always true and useless. The discriminating signal is whether ONE
    fragment is accessory-dominated while the other is core-bearing.

      COMPLEMENTARY  — core-fractions differ by >= FRC_ASYMMETRY_MIN and the lower side is accessory-
                       dominated (<= FRC_ACCESSORY_CEILING): a core fragment + an accessory fragment.
      BOTH_CORE      — both sides core-rich (>= FRC_CORE_FLOOR) and similar: paralogous cores, not a split
                       (corroborates an OVERLAPPING_PARALOG subject-tiling verdict).
      ACCESSORY_ONLY — both sides accessory-dominated: two tailoring fragments, weak rescue.
      AMBIGUOUS      — none of the above cleanly.
    """
    if prof_a is None or prof_b is None:
        return {"functional_rescue_class": "UNKNOWN_NO_PROFILE", "a_core_fraction": None, "b_core_fraction": None}
    fa, fb = _core_fraction(prof_a), _core_fraction(prof_b)
    lo, hi = min(fa, fb), max(fa, fb)
    gap = hi - lo
    if gap >= FRC_ASYMMETRY_MIN and lo <= FRC_ACCESSORY_CEILING:
        cls = "COMPLEMENTARY"
    elif fa >= FRC_CORE_FLOOR and fb >= FRC_CORE_FLOOR and gap < FRC_ASYMMETRY_MIN:
        cls = "BOTH_CORE"
    elif hi <= FRC_ACCESSORY_CEILING:
        cls = "ACCESSORY_ONLY"
    else:
        cls = "AMBIGUOUS"
    return {
        "functional_rescue_class": cls,
        "a_core_fraction": round(fa, 2),
        "b_core_fraction": round(fb, 2),
        "a_roles": prof_a.get("roles_present", []),
        "b_roles": prof_b.get("roles_present", []),
    }
