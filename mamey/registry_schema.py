"""Shared registry schema for Sapote/Mamey marker and cassette libraries.

This module is intentionally dependency-light so it can be vendored into the
standalone ChatGPT bundle.  The registry objects are plain dataclasses with
stable IDs, evidence tiers, regex/HMM targets, claim ceilings, wet-lab routing,
and citation/source fields.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Literal

EvidenceTier = Literal["TIER_1_DIAGNOSTIC", "TIER_2_CLASS_SUPPORTING", "TIER_3_CONTEXT_TAILORING", "TIER_4_GENERIC", "TIER_5_OVERINTERPRETATION_RISK"]
ClaimCeiling = Literal["CONFIRMED", "HIGH", "MODERATE", "LOW", "VERY_LOW", "INVENTORY_ONLY"]
TargetType = Literal["regex", "hmm", "pfam", "tigrfam", "smcog", "motif", "antiSMASH_label", "manual"]
WetLabRoute = Literal[
    "antibacterial_fractionation", "antifungal_fractionation", "dual_bioassay_fractionation",
    "lcms_msms", "uv_vis", "genetic_validation", "tfbs_induction", "hmm_blast_confirm",
    "long_read_rescue", "safety_cytotoxicity", "ecology_assay", "inventory_only"
]

@dataclass(frozen=True)
class Target:
    """A searchable signal used by a marker or cassette."""
    type: TargetType
    value: str
    min_bitscore: float | None = None
    evalue: float | None = None
    required_context: str | None = None
    note: str | None = None

@dataclass(frozen=True)
class Marker:
    """Atomic marker record: one gene/domain/motif/signature family."""
    id: str
    name: str
    library: str
    category: str
    evidence_tier: EvidenceTier
    claim_ceiling: ClaimCeiling
    targets: tuple[Target, ...]
    wet_lab_routes: tuple[WetLabRoute, ...] = ("hmm_blast_confirm",)
    description: str = ""
    positive_interpretation: str = ""
    negative_interpretation: str = "Absence in source-derived scans is not a true null unless the required input scope was available."
    claim_safety: str = "Use as triage evidence until confirmed by HMMER/BLAST, curated domain calls, LC-MS/MS, genetics, or fraction co-elution."
    citation: str = "Sapote-Mamey v1.9.3 harmonized bundle; source_scans.py."  # version-sync-ok: records harmonization-provenance version, not the running engine
    source_locator: str = ""
    version_added: str = "v1.9.4-registry-draft"
    synonyms: tuple[str, ...] = ()

@dataclass(frozen=True)
class Cassette:
    """Composite cassette record: a reusable multi-marker pathway or routing signature."""
    id: str
    name: str
    library: str
    family: str
    evidence_tier: EvidenceTier
    claim_ceiling: ClaimCeiling
    required_markers: tuple[str, ...] = ()
    optional_markers: tuple[str, ...] = ()
    forbidden_markers: tuple[str, ...] = ()
    targets: tuple[Target, ...] = ()
    wet_lab_routes: tuple[WetLabRoute, ...] = ("hmm_blast_confirm",)
    description: str = ""
    positive_interpretation: str = ""
    claim_safety: str = "Cassette calls are source-derived first-pass evidence unless confirmed by curated HMM/BLAST and BGC-context review."
    citation: str = "Sapote-Mamey v1.9.3 harmonized bundle; source_scans.py."  # version-sync-ok: records harmonization-provenance version, not the running engine
    source_locator: str = ""
    version_added: str = "v1.9.4-registry-draft"
    synonyms: tuple[str, ...] = ()


def registry_to_dict(records: tuple[Marker | Cassette, ...]) -> list[dict[str, Any]]:
    """Return JSON/CSV-friendly dictionaries for registry export."""
    return [asdict(r) for r in records]


def validate_stable_ids(records: tuple[Marker | Cassette, ...], prefix: str) -> None:
    """Fail fast if IDs are duplicated or do not use the expected prefix."""
    seen: set[str] = set()
    for record in records:
        if not record.id.startswith(prefix):
            raise ValueError(f"{record.id} does not start with expected prefix {prefix}")
        if record.id in seen:
            raise ValueError(f"duplicate registry id: {record.id}")
        seen.add(record.id)
