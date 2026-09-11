"""Trial-only length-weighted BGC capacity metric (P-LWC).

P-LWC is an additive assembly-sensitivity descriptor.  It never replaces the
corrected BGC count and is deliberately excluded from scoring and triage.
"""
from __future__ import annotations

import re
from typing import Iterable


REPORT_ONLY_CONTRACT = "TRIAL_ONLY_NO_SCORING"
DEFAULT_NOMINAL_FULL_LENGTH_BP = 15_000
NOMINAL_FULL_LENGTH_BP = {
    "NRPS": 30_000,
    "PKS": 30_000,
    "RiPP": 10_000,
    "THIOPEPTIDE": 15_000,
    "SACTIPEPTIDE": 12_000,
    "TERPENE": 15_000,
    "SIDEROPHORE": 12_000,
    "ECTOINE": 5_000,
    "MELANIN": 8_000,
    "BETALACTONE": 12_000,
    "BUTYROLACTONE": 8_000,
    "SACCHARIDE": 20_000,
    "REDOX_COFACTOR": 10_000,
}

_EXACT_ALIASES = {
    "nrps": "NRPS",
    "nrps-like": "NRPS",
    "nrp-metallophore": "NRPS",
    "napaa": "NRPS",
    "pks": "PKS",
    "pks-like": "PKS",
    "t1pks": "PKS",
    "t2pks": "PKS",
    "t3pks": "PKS",
    "transat-pks": "PKS",
    "transat-pks-like": "PKS",
    "ripp": "RiPP",
    "ripp-like": "RiPP",
    "rre-containing": "RiPP",
    "lanthipeptide": "RiPP",
    "lassopeptide": "RiPP",
    "linaridin": "RiPP",
    "ranthipeptide": "RiPP",
    "azole-containing-ripp": "RiPP",
    "thiopeptide": "THIOPEPTIDE",
    "sactipeptide": "SACTIPEPTIDE",
    "terpene": "TERPENE",
    "siderophore": "SIDEROPHORE",
    "metallophore": "SIDEROPHORE",
    "ectoine": "ECTOINE",
    "melanin": "MELANIN",
    "betalactone": "BETALACTONE",
    "butyrolactone": "BUTYROLACTONE",
    "saccharide": "SACCHARIDE",
    "redox-cofactor": "REDOX_COFACTOR",
}


def _clean_product(product: str) -> str:
    value = str(product or "").strip().lower().replace("_", "-")
    return re.sub(r"\s+", "-", value)


def normalize_product_family(product: str) -> tuple[str | None, str]:
    """Return canonical family plus mapping provenance."""
    cleaned = _clean_product(product)
    if not cleaned:
        return None, "EMPTY"
    if cleaned in _EXACT_ALIASES:
        return _EXACT_ALIASES[cleaned], "EXACT_ALIAS"
    if cleaned.startswith("lanthipeptide-class-"):
        return "RiPP", "FAMILY_RULE"
    if "ripp" in cleaned or any(
        token in cleaned
        for token in (
            "cyanobactin", "microviridin", "bottromycin", "thioamitide",
            "lipolanthine", "lassopeptide", "lanthipeptide",
        )
    ):
        return "RiPP", "FAMILY_RULE"
    if "nrps" in cleaned or cleaned.startswith("nrp-") or "nonribosomal" in cleaned:
        return "NRPS", "FAMILY_RULE"
    if "pks" in cleaned or "polyketide" in cleaned:
        return "PKS", "FAMILY_RULE"
    if "metallophore" in cleaned or "siderophore" in cleaned:
        return "SIDEROPHORE", "FAMILY_RULE"
    if "saccharide" in cleaned or "oligosaccharide" in cleaned:
        return "SACCHARIDE", "FAMILY_RULE"
    return None, "DEFAULT_UNMAPPED"


def nominal_length_profile(products: Iterable[str] | None) -> dict:
    mappings = []
    for product in products or []:
        family, mapping = normalize_product_family(str(product))
        mappings.append({
            "product": str(product),
            "normalized_family": family or "UNMAPPED",
            "mapping": mapping,
            "nominal_bp": (
                NOMINAL_FULL_LENGTH_BP[family]
                if family in NOMINAL_FULL_LENGTH_BP
                else DEFAULT_NOMINAL_FULL_LENGTH_BP
            ),
        })
    if not mappings:
        mappings.append({
            "product": "",
            "normalized_family": "UNMAPPED",
            "mapping": "DEFAULT_NO_PRODUCT",
            "nominal_bp": DEFAULT_NOMINAL_FULL_LENGTH_BP,
        })
    # LWC-01 (v9.7.338): rank genuinely-mapped families ahead of UNMAPPED ones. Previously the
    # selection keyed on nominal_bp first, so an UNMAPPED co-product carrying the 15 kb default
    # could outrank a smaller but real mapped family (e.g. "ectoine; other" picked the 15 kb
    # UNMAPPED default over ectoine's 5 kb), deflating length_fraction and mislabeling the
    # provenance. A mapped family (normalized_family != "UNMAPPED") now wins the tie-break.
    selected = max(
        mappings,
        key=lambda row: (
            row["normalized_family"] != "UNMAPPED",
            int(row["nominal_bp"]),
            str(row["normalized_family"]),
            str(row["product"]),
        ),
    )
    return {
        "nominal_bp": int(selected["nominal_bp"]),
        "nominal_basis_family": selected["normalized_family"],
        "nominal_basis_product": selected["product"],
        "mapping_status": (
            "DEFAULT_UNMAPPED"
            if selected["normalized_family"] == "UNMAPPED"
            else selected["mapping"]
        ),
        "normalized_families": sorted({
            row["normalized_family"] for row in mappings
        }),
        "product_mappings": mappings,
    }


def nominal_length_bp(products):
    """Compatibility wrapper returning only the selected nominal length."""
    return nominal_length_profile(products)["nominal_bp"]


def length_weighted_profile(bgcs):
    rows = []
    for bgc in bgcs:
        length_bp = max(
            0,
            int(getattr(bgc, "end", 0) or 0)
            - int(getattr(bgc, "start", 0) or 0)
            + 1,
        )
        profile = nominal_length_profile(getattr(bgc, "products", []))
        nominal = int(profile["nominal_bp"])
        fraction = min(1.0, length_bp / nominal) if nominal else 0.0
        boundary = str(getattr(bgc, "edge_status", "") or "")
        rows.append({
            "bgc_id": bgc.bgc_id,
            "contig": bgc.contig,
            "products": "; ".join(getattr(bgc, "products", []) or []),
            "normalized_families": "; ".join(profile["normalized_families"]),
            "nominal_basis_family": profile["nominal_basis_family"],
            "nominal_basis_product": profile["nominal_basis_product"],
            "nominal_mapping_status": profile["mapping_status"],
            "length_bp": length_bp,
            "nominal_full_length_bp": nominal,
            "length_fraction": round(fraction, 6),
            "boundary": boundary,
            "assembly_quality_caveat": (
                "ASSEMBLY_EDGE_OR_FULL_CONTIG"
                if boundary != "Interior"
                else ""
            ),
            "metric_status": REPORT_ONLY_CONTRACT,
        })
    return rows


def summary(rows):
    rows = list(rows or [])
    defaulted = sum(
        row.get("nominal_mapping_status") == "DEFAULT_UNMAPPED"
        for row in rows
    )
    return {
        "raw_regions": len(rows),
        "length_weighted_capacity_equivalents": round(
            sum(float(row["length_fraction"]) for row in rows), 4
        ),
        "interior_weighted": round(
            sum(float(row["length_fraction"]) for row in rows if row["boundary"] == "Interior"), 4
        ),
        "edge_weighted": round(
            sum(float(row["length_fraction"]) for row in rows if row["boundary"] == "Edge"), 4
        ),
        "full_contig_weighted": round(
            sum(float(row["length_fraction"]) for row in rows if row["boundary"] == "Full-contig"), 4
        ),
        "default_nominal_regions": defaulted,
        "normalized_nominal_regions": len(rows) - defaulted,
        "status": "TRIAL_ONLY_CAPACITY_METRIC",
        "report_only_contract": REPORT_ONLY_CONTRACT,
        "claim_safety": (
            "P-LWC is an assembly-sensitivity descriptor, not a corrected BGC "
            "count, lead score, product call, novelty metric, or evidence of production."
        ),
    }
