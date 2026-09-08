"""DKP/CDPS marker family scanner and claim-safety classifiers.

This module is intentionally conservative.  It detects candidate
cyclodipeptide/diketopiperazine loci from source annotations and antiSMASH
product calls, but it does not name a product.  Product identity remains a
chemistry/manual-review question.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from .crosswalk import contig_key  # T-4: shared contig normaliser
from .models import BGCRecord, CDSFeature, DomainFeature

CDPS_TERMS = (
    "cdps",
    "cyclodipeptide synthase",
    "cyclodipeptide-synthase",
    "cyclodipeptide_synthase",
    "diketopiperazine synthase",
    "pf16715",
)
CDO_CONTEXT_TERMS = (
    "cyclodipeptide oxidase",
    "albonoursin biosynthesis",
    "alba",
    "nitroreductase",
    "pf00881",
)
TAILORING_TERMS = (
    "prenyltransferase",
    "cytochrome p450",
    "p450",
    "methyltransferase",
    "flavin-dependent monooxygenase",
    "fmo",
    "oxygenase",
)
REGULATOR_TERMS = (
    "regulator",
    "transcriptional",
    "luxr",
    "tetr",
    "sarp",
    "laci",
    "gntr",
    "response regulator",
)
HOUSEKEEPING_TERMS = (
    "glutamate dehydrogenase",
    "nadp-specific glutamate dehydrogenase",
    "dehydrogenase",
    "kinase",
    "ribosomal",
    "dna polymerase",
    "rna polymerase",
    "transposase",
    "integrase",
    "housekeeping",
)


def _text(*parts: Any) -> str:
    vals: list[str] = []
    for p in parts:
        if p is None:
            continue
        if isinstance(p, dict):
            for k, v in p.items():
                vals.append(str(k))
                if isinstance(v, (list, tuple)):
                    vals.extend(str(x) for x in v[:8])
                else:
                    vals.append(str(v))
        elif isinstance(p, (list, tuple, set)):
            vals.extend(str(x) for x in p)
        else:
            vals.append(str(p))
    return " ".join(vals).lower()


def _has_any(hay: str, terms: Iterable[str]) -> bool:
    return any(term.lower() in hay for term in terms)


def cds_text(cds: CDSFeature) -> str:
    return _text(cds.locus_tag, cds.product, cds.qualifiers)


def domain_text(domain: DomainFeature) -> str:
    return _text(domain.locus_tag, domain.domain, domain.database, domain.qualifiers)


def is_cdps_cds(cds: CDSFeature) -> bool:
    return _has_any(cds_text(cds), CDPS_TERMS)


def is_cdps_domain(domain: DomainFeature) -> bool:
    return _has_any(domain_text(domain), CDPS_TERMS)


def classify_query_gene(label: str | None, product: str | None, qualifiers: dict[str, Any] | None = None,
                        pct_identity: float | None = None, coverage: float | None = None,
                        subject_accession: str | None = None, query_accession: str | None = None) -> str:
    """Classify a per-gene KCB/MIBiG hit before it can influence confidence."""
    h = _text(label, product, qualifiers or {})
    if (pct_identity is not None and coverage is not None and pct_identity >= 99.0 and coverage >= 98.0):
        if query_accession and subject_accession and query_accession == subject_accession:
            return "self-hit"
        if "putative" not in h and _has_any(h, CDPS_TERMS + CDO_CONTEXT_TERMS):
            # still potentially self-like; caller can exclude if the query is deposited
            return "self-hit_or_exact_reference"
    if _has_any(h, CDPS_TERMS + CDO_CONTEXT_TERMS):
        return "biosynthetic-diagnostic"
    if _has_any(h, TAILORING_TERMS):
        return "biosynthetic-tailoring"
    if _has_any(h, HOUSEKEEPING_TERMS):
        return "housekeeping/conserved"
    return "unclassified_context"


def _nearby(cds: CDSFeature, bgc: BGCRecord, flank: int = 10000) -> bool:
    return contig_key(cds.contig) == contig_key(bgc.contig) and not (cds.end < bgc.start - flank or cds.start > bgc.end + flank)


@dataclass
class DKPCall:
    strain: str
    bgc_id: str
    source_gbk: str
    contig: str
    start: int
    end: int
    boundary: str
    products: str
    marker_family: str
    diagnostic_cdps_present: str
    cdps_loci: str
    cdo_adjacent: str
    cdo_loci: str
    tailoring_context: str
    tailoring_loci: str
    regulator_context: str
    regulator_loci: str
    bgc_context: str
    confidence: str
    dkp_grade: str
    claim_ceiling: str
    product_claim_ceiling: str
    notes: str


def scan_dkp_cdps(strain: str, bgcs: list[BGCRecord], cds_list: list[CDSFeature],
                  domains: list[DomainFeature] | None = None, flank: int = 10000) -> dict[str, Any]:
    domains = domains or []
    calls: list[DKPCall] = []
    cdps_cds = [cds for cds in cds_list if is_cdps_cds(cds)]
    cdo_cds = [cds for cds in cds_list if _has_any(cds_text(cds), CDO_CONTEXT_TERMS)]
    tailoring_cds = [cds for cds in cds_list if _has_any(cds_text(cds), TAILORING_TERMS)]
    regulator_cds = [cds for cds in cds_list if _has_any(cds_text(cds), REGULATOR_TERMS)]
    cdps_domains = [d for d in domains if is_cdps_domain(d)]

    for bgc in bgcs:
        product_cdps = any(re.search(r"\bCDPS\b|cyclodipeptide|diketopiperazine", p, flags=re.I) for p in bgc.products)
        nearby_cdps = [c for c in cdps_cds if _nearby(c, bgc, flank=flank)]
        nearby_cdo = [c for c in cdo_cds if _nearby(c, bgc, flank=flank)]
        nearby_tailoring = [c for c in tailoring_cds if _nearby(c, bgc, flank=flank)]
        nearby_reg = [c for c in regulator_cds if _nearby(c, bgc, flank=flank)]
        nearby_cdps_domains = [d for d in cdps_domains if contig_key(d.contig) == contig_key(bgc.contig) and not (d.end < bgc.start - flank or d.start > bgc.end + flank)]

        if not (product_cdps or nearby_cdps or nearby_cdps_domains):
            continue

        in_region = any((c.start >= bgc.start and c.end <= bgc.end) for c in nearby_cdps) or product_cdps
        bgc_context = "antiSMASH_region" if in_region else "recovered_outside_antiSMASH_boundary"
        cdo_adjacent = bool(nearby_cdo)
        has_tailoring = bool(nearby_tailoring)
        has_reg = bool(nearby_reg)
        if cdo_adjacent:
            grade = "DKP-A_candidate_dehydro_DKP"
            conf = "HIGH" if bgc.edge_status == "Interior" else "MEDIUM"
        elif bgc.edge_status == "Edge":
            grade = "DKP-C_boundary_uncertain"
            conf = "MEDIUM"
        else:
            grade = "DKP-B_bare_or_saturated_CDP"
            conf = "MEDIUM" if product_cdps or nearby_cdps else "LOW"
        notes = []
        if has_tailoring:
            notes.append("tailoring nearby; decorated DKP possible")
        if has_reg:
            notes.append("regulator nearby")
        if not cdo_adjacent:
            notes.append("no co-located CDO/AlbA-like oxidase found by source terms")

        calls.append(DKPCall(
            strain=strain,
            bgc_id=bgc.bgc_id,
            source_gbk=bgc.source_gbk,
            contig=bgc.contig,
            start=bgc.start,
            end=bgc.end,
            boundary=bgc.edge_status,
            products="; ".join(bgc.products),
            marker_family="DKP_CDPS_cyclodipeptide",
            diagnostic_cdps_present="yes",
            cdps_loci=";".join(filter(None, [c.locus_tag for c in nearby_cdps])) or ("product_call:CDPS" if product_cdps else ";".join(filter(None, [d.locus_tag for d in nearby_cdps_domains]))),
            cdo_adjacent="yes" if cdo_adjacent else "no",
            cdo_loci=";".join(filter(None, [c.locus_tag for c in nearby_cdo])),
            tailoring_context="yes" if has_tailoring else "no",
            tailoring_loci=";".join(filter(None, [c.locus_tag for c in nearby_tailoring[:8]])),
            regulator_context="yes" if has_reg else "no",
            regulator_loci=";".join(filter(None, [c.locus_tag for c in nearby_reg[:8]])),
            bgc_context=bgc_context,
            confidence=conf,
            dkp_grade=grade,
            claim_ceiling="candidate DKP-scaffold BGC; specific dipeptide/product requires isolation",
            product_claim_ceiling="same-family-not-same-product; do not assert purincyclamide/albonoursin without chemistry",
            notes="; ".join(notes),
        ))

    return {
        "status": "SOURCE_DERIVED",
        "marker_family": "DKP_CDPS_cyclodipeptide",
        "count": len(calls),
        "calls": [asdict(c) for c in calls],
        "gene_classification_rule": "diagnostic CDPS/CDO may support class; tailoring supports context; housekeeping/self hits excluded from product confidence",
    }
