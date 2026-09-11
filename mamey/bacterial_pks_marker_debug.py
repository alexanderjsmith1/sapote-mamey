"""Conservative bacterial PKS/macrolide marker-debug helpers.

B2 Phase 2 first trial: this module adds support/caution marker extraction from
public bacterial reference fixtures. It does NOT activate HMM/DIAMOND/BLASTP
backends globally, does NOT change scoring, and does NOT claim product identity.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import re


@dataclass(frozen=True)
class MarkerHit:
    marker: str
    locus_tag: str
    product: str
    evidence: str
    source: str = "annotation_regex"


@dataclass(frozen=True)
class MarkerDebugSummary:
    accession: str
    family_hint: str
    support_flags: list[str]
    caution_flags: list[str]
    marker_hits: list[MarkerHit]

    def as_dict(self) -> dict:
        out = asdict(self)
        out["marker_hits"] = [asdict(h) for h in self.marker_hits]
        return out


MARKER_PATTERNS: dict[str, list[str]] = {
    # Rosamicin/macrolide-style support
    "ABC_F_RIBOSOMAL_PROTECTION": [r"\bABC-F\b", r"ribosomal protection"],
    "ERM_23S_RRNA_METHYLTRANSFERASE": [r"23S ribosomal RNA methyltransferase", r"\bErm\b"],
    "P450_TAILORING": [r"cytochrome P450"],
    "SDR_REDUCTIVE_TAILORING": [r"\bSDR\b", r"NAD\(P\).*oxidoreductase", r"dehydrogenase"],
    "GLYCOSYLTRANSFERASE": [r"glycosyl\s*transferase", r"glycosyltransferase"],
    "GLYCOSYLTRANSFERASE_ACTIVATOR": [r"glycosyltransferase activator", r"P450-derived glycosyltransferase activator"],
    "SAM_METHYLTRANSFERASE": [r"SAM-dependent methyltransferase", r"methyltransferase"],
    "DTDP_SUGAR_AMINOTRANSFERASE": [r"dTDP.*aminotransferase"],
    "DTDP_SUGAR_LYASE": [r"dTDP.*lyase"],
    "CROTONYL_COA_CARBOXYLASE_REDUCTASE": [r"crotonyl-CoA carboxylase/reductase"],

    # Desertomycin/large modular PKS support
    "MODULAR_POLYKETIDE_SYNTHASE": [r"modular polyketide synthase", r"type I polyketide"],
    "TYPEII_THIOESTERASE": [r"type\s*II thioesterase", r"typeII thioesterase"],
    "ACYL_COA_LIGASE": [r"acyl-CoA ligase"],
    "ACYLTRANSFERASE": [r"\bacyltransferase\b"],
    "AMINE_MONOOXYGENASE": [r"amine monooxygenase"],
    "AGMATINASE": [r"agmatinase"],
    "ABC_TRANSPORTER": [r"ABC transporter"],
    "MFS_TRANSPORTER": [r"major facilitator superfamily", r"\bMFS\b"],
    "LUXR_REGULATOR": [r"LuxR-family"],
    "TETR_REGULATOR": [r"TetR-family"],
    "HTH_REGULATOR": [r"helix-turn-helix"],

    # Caution/noise
    "TRANSPOSASE_BOUNDARY_CAUTION": [r"transposase"],
}


def _iter_kcb_query_genes(text: str) -> list[tuple[str, str]]:
    """Return (locus_tag, annotation) from antiSMASH ClusterBlast query table."""
    rows: list[tuple[str, str]] = []
    in_query = False
    for line in (text or "").splitlines():
        if line.startswith("Table of genes, locations"):
            in_query = True
            continue
        if in_query and not line.strip():
            break
        if not in_query:
            continue
        parts = line.split("\t")
        if len(parts) >= 5:
            rows.append((parts[0].strip(), parts[4].strip()))
    return rows


def _iter_gbk_cds_products(text: str) -> list[tuple[str, str]]:
    """Return (protein_id/locus_tag, product) from GenBank CDS blocks."""
    rows: list[tuple[str, str]] = []
    blocks = re.split(r"\n     CDS\s+", text or "")
    for block in blocks[1:]:
        locus = re.search(r'/locus_tag="([^"]+)"', block)
        protein = re.search(r'/protein_id="([^"]+)"', block)
        product = re.search(r'/product="([^"]+)"', block)
        gene = re.search(r'/gene="([^"]+)"', block)
        ident = (gene.group(1) if gene else "") or (locus.group(1) if locus else "") or (protein.group(1) if protein else "")
        if product and ident:
            rows.append((ident, product.group(1)))
    return rows


def marker_hits_from_annotation_rows(rows: list[tuple[str, str]]) -> list[MarkerHit]:
    hits: list[MarkerHit] = []
    seen: set[tuple[str, str]] = set()
    for locus, product in rows:
        for marker, patterns in MARKER_PATTERNS.items():
            if any(re.search(pat, product or "", re.I) for pat in patterns):
                key = (marker, locus)
                if key not in seen:
                    hits.append(MarkerHit(marker=marker, locus_tag=locus, product=product, evidence=product))
                    seen.add(key)
    return hits


def marker_hits_from_files(gbk_path: str | Path, kcb_path: str | Path | None = None) -> list[MarkerHit]:
    gbk_text = Path(gbk_path).read_text(encoding="utf-8", errors="ignore")
    rows = _iter_gbk_cds_products(gbk_text)
    if kcb_path:
        kcb_text = Path(kcb_path).read_text(encoding="utf-8", errors="ignore")
        # Prefer KCB query table names when present because it preserves dstA/dstT/dstR names.
        rows.extend(_iter_kcb_query_genes(kcb_text))
    return marker_hits_from_annotation_rows(rows)


def summarize_marker_hits(accession: str, hits: list[MarkerHit]) -> MarkerDebugSummary:
    markers = {h.marker for h in hits}
    support: list[str] = []
    caution: list[str] = []

    # BGC0002086/rosamicin-like
    if "GLYCOSYLTRANSFERASE" in markers and (
        "DTDP_SUGAR_AMINOTRANSFERASE" in markers or "DTDP_SUGAR_LYASE" in markers
    ):
        support.append("MACRO_SUGAR_TAILORING")
    if "ERM_23S_RRNA_METHYLTRANSFERASE" in markers or "ABC_F_RIBOSOMAL_PROTECTION" in markers:
        support.append("MACRO_RIBOSOME_RESISTANCE")
    if sum(1 for h in hits if h.marker == "P450_TAILORING") >= 1 and sum(1 for h in hits if h.marker == "SDR_REDUCTIVE_TAILORING") >= 2:
        support.append("MACRO_P450_SDR_TAILORING")

    # LC529898/desertomycin-like
    modular_count = sum(1 for h in hits if h.marker == "MODULAR_POLYKETIDE_SYNTHASE")
    if modular_count >= 4:
        support.append("LARGE_T1PKS_POLYENE_BACKBONE")
    if "TYPEII_THIOESTERASE" in markers:
        support.append("PKS_TYPEII_TE_SUPPORT")
    if "ACYL_COA_LIGASE" in markers or "ACYLTRANSFERASE" in markers:
        support.append("PKS_ACYLTRANSFER_ACYL_LIGASE_TAILORING")
    if "ABC_TRANSPORTER" in markers or "MFS_TRANSPORTER" in markers:
        support.append("PKS_TRANSPORTER_CONTEXT")
    if "LUXR_REGULATOR" in markers or "TETR_REGULATOR" in markers or "HTH_REGULATOR" in markers:
        support.append("PKS_REGULATORY_CONTEXT")

    if "TRANSPOSASE_BOUNDARY_CAUTION" in markers:
        caution.append("BOUNDARY_TRANSPOSASE_CAUTION")

    family_hint = "bacterial_PKS_marker_debug"
    return MarkerDebugSummary(
        accession=accession,
        family_hint=family_hint,
        support_flags=sorted(set(support)),
        caution_flags=sorted(set(caution)),
        marker_hits=hits,
    )


def summarize_marker_files(accession: str, gbk_path: str | Path, kcb_path: str | Path | None = None) -> MarkerDebugSummary:
    return summarize_marker_hits(accession, marker_hits_from_files(gbk_path, kcb_path))
