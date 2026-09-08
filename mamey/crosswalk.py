"""BGC-to-contig/node crosswalk helpers for Sapote--Mamey.

The executable Mamey module assigns stable BGC### IDs during parsing, but
antiSMASH users navigate by contig/node, region file, coordinates, and protein
IDs.  These helpers make that mapping mandatory and reusable across CSV,
workbook, JSON, PDF/report, RG-GMCI, and manual BLASTP outputs.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from .models import BGCRecord, CDSFeature


def region_label(region_number) -> str:
    """v9.7.244: tolerate an already-formatted label. `region_label("region003")` used to raise
    ValueError, and this helper is imported by 11 modules — several of which read `antismash_region`,
    whose value IS "region003". Digits are extracted; anything without digits is unknown."""
    if region_number is None or region_number == "":
        return "region_unknown"
    raw = str(region_number).strip()
    # v9.7.245: `re.search(r"(\d+)", "-1")` matches "1" — the sign is not part of \d+ — so a negative
    # region silently became region001, contradicting this function's own stated rule ("anything <= 0 is
    # region_unknown"). Reject a leading minus before the digits are read. Found by an outside verifier
    # who tested the boundary the fix note named, instead of assuming the note covered it.
    if re.match(r"^\s*-\s*\d", raw):
        return "region_unknown"
    m = re.search(r"(\d+)", raw)
    if not m:
        return "region_unknown"
    n = int(m.group(1))
    return f"region{n:03d}" if n > 0 else "region_unknown"


def contig_key(name: str) -> str:
    """Normalise a contig id so the same physical contig matches across files even when the SPAdes coverage
    suffix is formatted differently (e.g. _cov_63.42318 vs _cov_63.042318) — match on node id/length, never
    the cov float (feedback §1 / T-4). Shared util: use for EVERY contig / Source_GBK join, not just orphan
    detection, so cross-file joins (GBK merges, package-dir/strain-id reconciliation) all normalise the same."""
    if not name:
        return ""
    m = re.match(r"(NODE_\d+_length_\d+)", name)
    if m:
        return m.group(1)
    return re.sub(r"[_.]cov[_=].*$", "", name)


def infer_node_id(contig_id: str, source_gbk: str = "") -> str:
    """Return the most user-recognizable contig/node identifier available.

    antiSMASH and assemblers vary: NODE_10_length_..., ctg10, scaffold_42,
    CP073042.1.  We preserve the original contig ID if it already looks like a
    node/scaffold/contig accession; otherwise we use the GenBank record ID.
    """
    base = Path(source_gbk).name
    for candidate in (contig_id, base):
        if not candidate:
            continue
        m = re.search(r"(NODE_\d+[^.\s]*)", candidate, flags=re.I)
        if m:
            return m.group(1)
        m = re.search(r"((?:ctg|contig|scaffold)_?\d+)", candidate, flags=re.I)
        if m:
            return m.group(1)
    return contig_id


def assembly_locator(bgc) -> str:
    """Boss-facing locus label: node/contig first, BGC id second.

    BGC### is Mamey's immutable internal bookkeeping. Humans find loci in the
    assembly/antiSMASH HTML by NODE/contig plus region/coordinates, so every
    boss-facing label should start with the assembly locator and carry BGC### only
    as a parenthetical cross-reference.
    """
    get = bgc.get if isinstance(bgc, dict) else lambda k, default="": getattr(bgc, k, default)
    bgc_id = str(get("bgc_id", "") or get("BGC_ID", "") or "").strip()
    node = str(get("node_id", "") or get("Node_ID", "") or get("contig", "") or get("Contig", "") or "").strip()
    region = str(get("antismash_region", "") or get("antiSMASH_Region", "") or "").strip()
    # v9.7.244: `x or y` treats region_number=0 as absent and silently reads `Region` instead.
    # Region numbers are 1-based, so 0 is invalid input, not a fallback trigger — say so explicitly.
    region_number = get("region_number", None)
    if region_number in (None, ""):
        region_number = get("Region", None)
    if not region and region_number not in (None, ""):
        try:
            region = region_label(int(region_number))
        except Exception:
            region = str(region_number)
    left = " ".join(x for x in (node, region) if x).strip() or "UNKNOWN_LOCUS"
    return f"{left} ({bgc_id})" if bgc_id else left


def enrich_bgc_crosswalk(bgc: BGCRecord, source_gbk: str = "") -> BGCRecord:
    bgc.source_gbk = source_gbk or bgc.source_gbk
    bgc.antismash_region = bgc.antismash_region or region_label(bgc.region_number)
    bgc.node_id = bgc.node_id or infer_node_id(bgc.contig, bgc.source_gbk)
    bgc.user_label = assembly_locator(bgc)
    return bgc


def build_bgc_crosswalk(bgcs: Iterable[BGCRecord]) -> list[dict]:
    return [b.crosswalk_dict() for b in bgcs]


def bgc_proteins(cds_list: Iterable[CDSFeature], bgc: BGCRecord, flank: int = 0) -> list[CDSFeature]:
    """Return CDS records overlapping a BGC interval, optionally with flank."""
    out: list[CDSFeature] = []
    lo = max(1, bgc.start - flank)
    hi = bgc.end + flank
    for cds in cds_list:
        if cds.contig != bgc.contig:
            continue
        if cds.end >= lo and cds.start <= hi:
            out.append(cds)
    return out


# v9.7.91: scoring terms widened so VERY_POOR / nucleoside strains are not silently missed.
_BLASTP_PRIORITY_TERMS = [
    "halogenase", "arylpolyene", "ketosynthase", "pks", "nrps", "adenylation",
    "condensation", "terpene", "cyclase", "lanthipeptide", "precursor",
    "siderophore", "glycosyltransferase", "p450", "oxygenase", "methyltransferase",
    "nucleoside", "radical_sam", "radical sam", "aminotransferase", "dehydrogenase",
]
# KCB / smCOG hits read as: "nikJ (E-value: 1.8e-172, bitscore: 563.5, seeds: 4, tool: ...)"
_KCB_HIT_RE = re.compile(r"([A-Za-z][A-Za-z0-9_]+)\s*\(E-value:[^,]+,\s*bitscore:\s*([0-9.]+)")
# rule-based-clusters gene assignment in gene_functions: "... (rule-based-clusters) <class>: <geneName>"
# the <geneName> after the colon is the genuine KCB cluster gene (nikJ, truD, tra_KS) — the signal we want.
_RBC_GENE_RE = re.compile(r"rule-based-clusters\)\s*[A-Za-z0-9_+\-]+:\s*([A-Za-z][A-Za-z0-9_]+)")
# descriptor / accession tokens that are NOT gene names — never surface as kcb_closest_gene.
# v9.7.91 hardening: added the common antiSMASH NRPS/PKS catalytic-domain profile names that were
# leaking into the column (e.g. "Condensation", "AMP-binding"). Heuristic draft — see report caveat.
_KCB_SKIP = {
    "pf", "smcog", "other", "biosynthetic", "additional", "rule", "based", "clusters",
    "binding", "domain", "protein", "transport", "regulatory", "seeds", "tool",
    # antiSMASH catalytic-domain profiles (descriptors, not gene names):
    "condensation", "epimerization", "heterocyclization", "thioesterase", "aminotran",
    "ketoacyl", "acp", "pcp", "pks_ks", "pks_at", "pks_kr", "pks_dh", "pks_er", "cglyc",
    "amp", "pp", "nad", "polysacc_synt", "glycos_transf", "methyltransf", "abhydrolase",
    "adh_short", "fabd", "ketoacyl-synt", "phytoene_synt",
}


def _cds_qual(cds, key: str) -> str:
    """Qualifier value as a flat string ('' if absent). antiSMASH stores function here, not in .product."""
    q = getattr(cds, "qualifiers", None) or {}
    v = q.get(key)
    return " ".join(v) if isinstance(v, list) else (v or "")


def _annotation_blob(cds) -> str:
    """The text antiSMASH actually populates — NOT just product (often None on these GBKs)."""
    return " ".join([
        cds.locus_tag or "", cds.product or "",
        _cds_qual(cds, "sec_met_domain"), _cds_qual(cds, "gene_functions"),
    ]).lower()


def _is_skipped(name: str) -> bool:
    return name.lower() in _KCB_SKIP or name.upper().startswith(("PF", "SMCOG"))


def kcb_closest_gene(cds) -> tuple[str, str]:
    """Closest named KCB cluster gene + its bitscore. ('','') if none.

    v9.7.91 hardening: prefer a gene name that antiSMASH assigned via rule-based-clusters
    (the "<class>: <geneName>" form in gene_functions) — those are genuine KCB cluster genes
    (nikJ, truD, tra_KS). Fall back to the highest-bitscore named hit in sec_met_domain only
    when no rule-based-clusters assignment exists. Catalytic-domain profiles (Condensation,
    AMP-binding, …) are filtered by _KCB_SKIP so they never surface as a gene name.
    """
    sec = _cds_qual(cds, "sec_met_domain")
    # bitscore lookup by gene name from sec_met_domain
    scores = {}
    for m in _KCB_HIT_RE.finditer(sec):
        nm, bs = m.group(1), float(m.group(2))
        if not _is_skipped(nm):
            scores[nm] = max(bs, scores.get(nm, 0.0))
    # 1) prefer a rule-based-clusters-assigned gene name (the genuine KCB cluster gene)
    rbc = [g for g in _RBC_GENE_RE.findall(_cds_qual(cds, "gene_functions")) if not _is_skipped(g)]
    for g in rbc:
        if g in scores:
            return (g, str(scores[g]))
    if rbc:
        return (rbc[0], str(scores.get(rbc[0], "")))
    # 2) conservative: with NO rule-based-clusters assignment we do NOT guess from sec_met_domain
    #    (that surfaced catalytic-domain fragments like "synt"/"ATd"). A wrong gene label is worse
    #    than an empty cell for manuscript-facing labelling, so leave it blank.
    return ("", "")


def candidate_blastp_rows(bgcs: Iterable[BGCRecord], cds_list: Iterable[CDSFeature],
                          strain: str | None = None) -> list[dict]:
    """Build a conservative manual BLASTP spot-check worklist.

    This does not run BLASTP. It selects a few high-value proteins per BGC from
    antiSMASH/source annotations so a human or external service can verify them.

    v9.7.91 fix: score against the qualifiers antiSMASH actually populates
    (sec_met_domain / gene_functions), not just `product` (which is None on these
    GBKs and produced a silently-empty worklist), and surface the closest named KCB
    gene + bitscore plus a pre-formatted user_blastp_label as their own columns.
    """
    rows: list[dict] = []
    for bgc in bgcs:
        ranked = []
        for cds in bgc_proteins(cds_list, bgc):
            score = sum(1 for term in _BLASTP_PRIORITY_TERMS if term in _annotation_blob(cds))
            if score:
                ranked.append((score, cds))
        ranked.sort(key=lambda x: (-x[0], x[1].start))
        for score, cds in ranked[:3]:
            kcb_gene, kcb_bs = kcb_closest_gene(cds)
            locus = cds.locus_tag or ""
            rows.append({
                "bgc_id": bgc.bgc_id,
                "assembly_locator": assembly_locator(bgc),
                "user_label": bgc.user_label,
                # pre-formatted to the user's BLASTp file-naming convention, e.g. "AS-XXX ctg162_11"
                "user_blastp_label": (f"{strain} {locus}".strip() if strain else locus),
                "contig": bgc.contig,
                "node_id": bgc.node_id,
                "antismash_region": bgc.antismash_region,
                "source_gbk": bgc.source_gbk,
                "protein_id": locus,
                "kcb_closest_gene": kcb_gene,
                "kcb_bitscore": kcb_bs,
                "protein_start": cds.start,
                "protein_end": cds.end,
                "product_annotation": cds.product or _cds_qual(cds, "sec_met_domain")[:80],
                "manual_blastp_status": "MANUAL_BLASTP_OPTIONAL",
                "reason_for_blastp": "top-lead/source-derived biosynthetic marker; KCB = similarity not identity; verify function against NCBI nr/Swiss-Prot/local DB before manuscript claims",
                "sequence_available": "yes" if cds.translation else "no",
            })
    return rows
