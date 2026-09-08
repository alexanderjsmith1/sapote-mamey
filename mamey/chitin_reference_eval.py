"""mamey/chitin_reference_eval.py -- whole-genome chitin/GlcNAc reference-capacity evaluation.

Formalises the per-strain whole-genome chitin reference evaluation workroom
(Codex, "August 21 Codex/PER_STRAIN_CHITIN_REFERENCE_EVALUATION_2026-08-21/working/
build_per_strain_chitin_evaluations, Codex 2026-08-21") into the bundle as a small, testable library. State
names, the architecture-profile logic, and the reference-quality tiers are carried over from
that workroom's spec (its own working/*.py scripts) rather than invented here; the input surface
is generalised from that workroom's 46-strain hardcoded census to any sealed package's CGAD scan
output (mamey/source_scans.py CHITINASE_PATTERNS -> SourceScanBundle.chitinase) paired with an
operator-supplied reference registry.

SCOPE (workroom CHD-001 / CHD-002, both ACTIVE, "superseded only by owner"):
  - Whole-genome, per-strain. The strain is the biological unit of evaluation; a cohort table is
    navigation and context only, never the unit of conclusion.
  - Independent of Mode B / BGC completion. Chitinase/CGAD capacity is a whole-genome trait, not
    a BGC call -- this module is deliberately NOT routed through triage or scoring, and callers
    must not wire it into either.

CLAIM CEILING (workroom CHH-002, ACTIVE): encoded domain capacity only -- never enzyme activity,
expression, chitin utilization, antifungal phenotype, ecological adaptation, novelty, or BGC
causality. Every evaluation object carries CLAIM_CEILING; every rendering of one must show it.

REFERENCE HANDLING: this module never reads, copies, or redistributes reference sequence data.
A reference is identified only by its declared path and SHA-256 in the operator-supplied registry
TSV; ANI/identity values are accepted as already-computed registry columns (the operator's own
fastANI run, kept outside this module by design -- see tools/chitin_reference_eval.py) rather than
executed as a subprocess here. A registry row with no ANI value types as NOT_SCORED, never as an
absence of similarity.

No print() calls in this file -- it is a library; tools/chitin_reference_eval.py is the operator
front door.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

CLAIM_CEILING = (
    "encoded domain capacity only -- not enzyme activity, expression, chitin utilization, "
    "antifungal phenotype, ecological adaptation, novelty, or BGC causality"
)

SCOPE_NOTE = (
    "Whole-genome measurement, independent of Mode B / BGC completion (workroom CHD-001/CHD-002): "
    "the strain is the unit of analysis; this evaluation is not routed through triage or scoring."
)

# mamey/source_scans.py CHITINASE_PATTERNS -- the CGAD scan's own family vocabulary. Kept as the
# single source of truth here so this module never drifts from what CGAD actually measures.
CHITIN_FAMILIES = ("GH18", "GH19", "AA10_LPMO", "CBM_CHITIN", "GlcNAc")

FAMILY_LABEL = {
    "GH18": "GH18 chitinase-family",
    "GH19": "GH19 chitinase-family",
    "AA10_LPMO": "AA10/LPMO oxidative polysaccharide-family",
    "CBM_CHITIN": "chitin-binding module context",
    "GlcNAc": "GlcNAc catabolism / DasR-linked induction context",
}

# Degradative/binding/oxidative families sum to the reported "domains_total"; GlcNAc is context
# and is excluded from that total -- mirroring the workroom's GH16/GH3/NagB context exclusion.
_CORE_FAMILIES = ("GH18", "GH19", "AA10_LPMO", "CBM_CHITIN")

ARCHITECTURE_STATES = (
    "MULTI_ARM_CHITIN_CAPACITY",
    "PARTIAL_COORDINATED_CHITIN_CAPACITY",
    "CHITINASE_FAMILY_CAPACITY_WITHOUT_SUPPORTING_ARMS",
    "NON_ENDOCHITINASE_CHITIN_CONTEXT",
    "MINIMAL_MEASURED_CHITIN_DOMAIN_CAPACITY",
    "ABSENT_NO_MEASURED_CHITIN_DOMAINS",
)

REFERENCE_QUALITY_STATES = (
    "NO_TAXON_MATCHED_REFERENCE_PANEL",
    "TAXON_MATCHED_PANEL_BUT_NO_ANI_AT_MIN_FRACTION",
    "SPECIES_LEVEL_SIMILARITY_CANDIDATE_NOT_TAXONOMIC_CONFIRMATION",
    "HIGHER_SIMILARITY_NONSPECIES_REFERENCE_CONTEXT",
    "DISTANT_AVAILABLE_TAXON_MATCHED_REFERENCE_CONTEXT",
)

REFERENCE_ROW_STATES = (
    "RETURNED_ABOVE_MIN_ALIGNED_FRACTION",
    "NO_OUTPUT_AT_MIN_ALIGNED_FRACTION",
    "NOT_SCORED",  # registry row supplied no ani_pct -- never treated as zero similarity
)

# Workroom thresholds (workroom script build_per_strain_chitin_evaluations::reference_quality), unchanged.
ANI_SPECIES_THRESHOLD = 95.0
ANI_HIGHER_SIMILARITY_THRESHOLD = 90.0
MIN_ALIGNED_FRACTION = 0.2
MIN_ALIGNED_FRACTION_FOR_QUALITY_TIER = 0.5  # workroom's af>=0.5 gate on the species/higher tiers
MINIMAL_DOMAIN_CEILING = 2  # workroom: chitinolytic_domains_total <= 2 -> MINIMAL_*


class ChitinReferenceEvalError(ValueError):
    """Malformed CGAD counts or registry input -- refuse rather than guess."""


@dataclass(frozen=True)
class ChitinCapacityProfile:
    strain_id: str
    counts: dict[str, int]
    domains_total: int
    architecture_state: str
    architecture_text: str
    claim_ceiling: str = CLAIM_CEILING

    def to_dict(self) -> dict[str, Any]:
        return {
            "strain_id": self.strain_id, "counts": dict(self.counts),
            "domains_total": self.domains_total, "architecture_state": self.architecture_state,
            "architecture_text": self.architecture_text, "claim_ceiling": self.claim_ceiling,
        }


@dataclass(frozen=True)
class ReferenceComparisonRow:
    reference_id: str
    reference_taxon: str
    source_path: str
    source_sha256: str
    ani_pct: float | None
    aligned_fragment_fraction: float | None
    reference_domains_total: int | None
    row_state: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference_id": self.reference_id, "reference_taxon": self.reference_taxon,
            "source_path": self.source_path, "source_sha256": self.source_sha256,
            "ani_pct": self.ani_pct, "aligned_fragment_fraction": self.aligned_fragment_fraction,
            "reference_domains_total": self.reference_domains_total, "row_state": self.row_state,
        }


@dataclass(frozen=True)
class ChitinReferenceEvaluation:
    strain_id: str
    profile: ChitinCapacityProfile
    reference_panel: tuple[ReferenceComparisonRow, ...]
    reference_quality: str
    top_reference: ReferenceComparisonRow | None
    scope_note: str = SCOPE_NOTE
    claim_ceiling: str = CLAIM_CEILING

    def to_dict(self) -> dict[str, Any]:
        return {
            "strain_id": self.strain_id, "profile": self.profile.to_dict(),
            "reference_panel": [r.to_dict() for r in self.reference_panel],
            "reference_panel_n": len(self.reference_panel),
            "reference_quality": self.reference_quality,
            "top_reference": self.top_reference.to_dict() if self.top_reference else None,
            "scope_note": self.scope_note, "claim_ceiling": self.claim_ceiling,
        }


def architecture_profile(strain_id: str, counts: dict[str, Any]) -> ChitinCapacityProfile:
    """Type a strain's CGAD family counts into the workroom's architecture-profile vocabulary.

    `counts` is (or is compatible with) mamey source_scans.chitinase["counts"] -- a dict keyed by
    CHITIN_FAMILIES; missing keys are treated as 0. Non-negative-int-coercible values only.
    """
    c: dict[str, int] = {}
    for fam in CHITIN_FAMILIES:
        raw = counts.get(fam, 0)
        try:
            n = int(raw)
        except (TypeError, ValueError):
            raise ChitinReferenceEvalError(f"{strain_id}: non-numeric count for {fam!r}: {raw!r}")
        if n < 0:
            raise ChitinReferenceEvalError(f"{strain_id}: negative count for {fam!r}: {n}")
        c[fam] = n

    endo = c["GH18"] + c["GH19"]
    cbm, lpmo, context = c["CBM_CHITIN"], c["AA10_LPMO"], c["GlcNAc"]
    total = sum(c[fam] for fam in _CORE_FAMILIES)

    if endo and cbm and lpmo:
        state, text = "MULTI_ARM_CHITIN_CAPACITY", (
            "The genome encodes chitinase-family, chitin-binding, and AA10/LPMO-family "
            "components -- a multi-arm capacity profile.")
    elif endo and (cbm or lpmo):
        state, text = "PARTIAL_COORDINATED_CHITIN_CAPACITY", (
            "The genome encodes chitinase-family proteins plus one supporting binding or "
            "oxidative arm, but not the complete three-arm profile.")
    elif endo:
        state, text = "CHITINASE_FAMILY_CAPACITY_WITHOUT_SUPPORTING_ARMS", (
            "Chitinase-family domains are present, while chitin-binding and AA10/LPMO support "
            "is not jointly observed.")
    elif total == 0 and context == 0:
        state, text = "ABSENT_NO_MEASURED_CHITIN_DOMAINS", (
            "No chitinase-family, chitin-binding, or AA10/LPMO-family domains were measured.")
    elif total <= MINIMAL_DOMAIN_CEILING:
        state, text = "MINIMAL_MEASURED_CHITIN_DOMAIN_CAPACITY", (
            "The scan recovered only a minimal degradative/binding-domain profile.")
    else:
        state, text = "NON_ENDOCHITINASE_CHITIN_CONTEXT", (
            "The measured profile is carried by binding, oxidative, or GlcNAc-catabolic context "
            "without a GH18/GH19 endochitinase call.")

    return ChitinCapacityProfile(strain_id=strain_id, counts=c, domains_total=total,
                                  architecture_state=state, architecture_text=text)


def _parse_optional_float(raw: str | None) -> float | None:
    if raw is None:
        return None
    s = raw.strip()
    if not s or s.upper() == "NR":
        return None
    return float(s)


def _parse_optional_int(raw: str | None) -> int | None:
    if raw is None:
        return None
    s = raw.strip()
    if not s or s.upper() == "NR":
        return None
    return int(s)


def build_reference_rows(registry_rows: list[dict[str, str]], strain_taxon: str,
                          genus_aliases: list[str] | None = None) -> list[ReferenceComparisonRow]:
    """Type each operator-registry row that matches the strain's taxon (or a declared alias).

    Never reads the sequence at source_path -- only its declared path/hash pass through.
    A row missing ani_pct types NOT_SCORED (not absence of similarity, not zero identity).
    """
    aliases = set(genus_aliases or []) | {strain_taxon}
    rows: list[ReferenceComparisonRow] = []
    for r in registry_rows:
        taxon = (r.get("taxon") or r.get("genus") or "").strip()
        if taxon not in aliases:
            continue
        ani = _parse_optional_float(r.get("ani_pct"))
        af = _parse_optional_float(r.get("aligned_fragment_fraction"))
        domains = _parse_optional_int(r.get("chitin_domains_total"))
        if ani is None:
            row_state = "NOT_SCORED"
        elif af is not None and af >= MIN_ALIGNED_FRACTION:
            row_state = "RETURNED_ABOVE_MIN_ALIGNED_FRACTION"
        else:
            row_state = "NO_OUTPUT_AT_MIN_ALIGNED_FRACTION"
        rows.append(ReferenceComparisonRow(
            reference_id=r.get("reference_id", "NR") or "NR", reference_taxon=taxon,
            source_path=r.get("source_path", "NR") or "NR",
            source_sha256=r.get("source_sha256", "NR") or "NR",
            ani_pct=ani, aligned_fragment_fraction=af, reference_domains_total=domains,
            row_state=row_state,
        ))
    return rows


def reference_quality(reference_rows: list[ReferenceComparisonRow]) -> str:
    """Workroom reference_quality() tiers, unchanged thresholds."""
    if not reference_rows:
        return "NO_TAXON_MATCHED_REFERENCE_PANEL"
    scored = [r for r in reference_rows if r.ani_pct is not None]
    if not scored:
        return "TAXON_MATCHED_PANEL_BUT_NO_ANI_AT_MIN_FRACTION"
    top = max(scored, key=lambda r: r.ani_pct)
    af = top.aligned_fragment_fraction or 0.0
    if top.ani_pct >= ANI_SPECIES_THRESHOLD and af >= MIN_ALIGNED_FRACTION_FOR_QUALITY_TIER:
        return "SPECIES_LEVEL_SIMILARITY_CANDIDATE_NOT_TAXONOMIC_CONFIRMATION"
    if top.ani_pct >= ANI_HIGHER_SIMILARITY_THRESHOLD and af >= MIN_ALIGNED_FRACTION_FOR_QUALITY_TIER:
        return "HIGHER_SIMILARITY_NONSPECIES_REFERENCE_CONTEXT"
    return "DISTANT_AVAILABLE_TAXON_MATCHED_REFERENCE_CONTEXT"


def evaluate_strain(strain_id: str, cgad_counts: dict[str, Any],
                     registry_rows: list[dict[str, str]], strain_taxon: str,
                     genus_aliases: list[str] | None = None) -> ChitinReferenceEvaluation:
    """Top-level entry point.

    strain_id: the AS/strain identifier (for labelling only -- never routed through triage).
    cgad_counts: mamey source_scans.chitinase["counts"] (or a manifest.json
      source_scans.chitinase.counts dict) -- keyed by CHITIN_FAMILIES.
    registry_rows: parsed rows of the operator-supplied reference registry TSV.
    strain_taxon / genus_aliases: used only to filter the registry to a taxon-matched panel.
    """
    profile = architecture_profile(strain_id, cgad_counts)
    ref_rows = build_reference_rows(registry_rows, strain_taxon, genus_aliases)
    quality = reference_quality(ref_rows)
    scored = [r for r in ref_rows if r.ani_pct is not None]
    top = max(scored, key=lambda r: r.ani_pct) if scored else None
    return ChitinReferenceEvaluation(
        strain_id=strain_id, profile=profile, reference_panel=tuple(ref_rows),
        reference_quality=quality, top_reference=top,
    )


def verify_reference_hash(source_path: str, declared_sha256: str) -> bool | None:
    """Best-effort integrity check for a registry row's declared hash against the live file.

    Returns True/False if the path resolves and is readable, or None if it cannot be checked
    (path missing/unreadable) -- callers must not treat None as a pass. Reads the file only to
    hash it; never copies or redistributes its content.
    """
    if not source_path or not declared_sha256 or declared_sha256.upper() == "NR":
        return None
    if not os.path.isfile(source_path):
        return None
    import hashlib
    h = hashlib.sha256()
    try:
        with open(source_path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest() == declared_sha256
