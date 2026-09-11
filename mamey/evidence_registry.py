"""Validate a portable, heterogeneous strain evidence registry.

The registry preserves the operational lineage ``strain -> material -> assay``:
a material may be a crude extract, flash fraction, or HPLC fraction, and an
assay row may name a panel and target. It does not derive activity, potency,
compound identity, or a BGC-to-assay link.
"""
from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

REQUIRED_HEADERS = ("record_id", "strain_id", "material_id", "parent_material_id", "preparation_event_id", "evidence_type", "material_level", "assay_state", "panel_id", "target_id", "replicate_state", "privacy_tier", "source_locator", "claim_ceiling")
ALLOWED_EVIDENCE_TYPES = {"genome", "material", "assay", "analytical", "other"}
ALLOWED_MATERIAL_LEVELS = {"genome", "crude_extract", "flash_fraction", "hplc_fraction", "other"}
ALLOWED_ASSAY_STATES = {"NOT_SCREENED", "SCREENED", "RESULTS_BOUND", "PLANNING_ONLY"}


class EvidenceRegistryError(ValueError):
    """Raised when an evidence registry is malformed or ambiguous."""


def validate_evidence_registry(path: str | Path, *, profile=None) -> dict:
    """Read a TSV/CSV registry and return an evidence-availability summary."""
    registry_path = Path(path)
    delimiter = "\t" if registry_path.suffix.lower() == ".tsv" else ","
    try:
        with registry_path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter=delimiter)
            headers = tuple(reader.fieldnames or ())
            missing = [header for header in REQUIRED_HEADERS if header not in headers]
            if missing:
                raise EvidenceRegistryError(f"missing required headers: {', '.join(missing)}")
            rows = list(reader)
    except OSError as exc:
        raise EvidenceRegistryError(f"cannot read evidence registry {registry_path}: {exc}") from exc
    if not rows:
        raise EvidenceRegistryError("evidence registry must contain at least one data row")
    seen: set[str] = set()
    by_strain: dict[str, Counter] = defaultdict(Counter)
    materials: dict[str, dict] = {}
    assay_rows: list[tuple[int, dict]] = []
    for number, row in enumerate(rows, start=2):
        for header in REQUIRED_HEADERS:
            if not str(row.get(header) or "").strip():
                raise EvidenceRegistryError(f"row {number}: blank {header}")
        record_id = row["record_id"].strip()
        if record_id in seen:
            raise EvidenceRegistryError(f"row {number}: duplicate record_id {record_id!r}")
        seen.add(record_id)
        evidence_type = row["evidence_type"].strip()
        material_level = row["material_level"].strip()
        if evidence_type not in ALLOWED_EVIDENCE_TYPES:
            raise EvidenceRegistryError(f"row {number}: unsupported evidence_type")
        if material_level not in ALLOWED_MATERIAL_LEVELS:
            raise EvidenceRegistryError(f"row {number}: unsupported material_level")
        if row["assay_state"].strip() not in ALLOWED_ASSAY_STATES:
            raise EvidenceRegistryError(f"row {number}: unsupported assay_state")
        strain_id = row["strain_id"].strip()
        if profile is not None:
            expected_tier = profile.assignments.get(strain_id, profile.default_tier)
            if row["privacy_tier"].strip() != expected_tier:
                raise EvidenceRegistryError(f"row {number}: privacy_tier does not match exact/default profile tier")
        if evidence_type == "material":
            material_id = row["material_id"].strip()
            if material_id in materials:
                raise EvidenceRegistryError(f"row {number}: duplicate material record for {material_id!r}")
            materials[material_id] = row
        if evidence_type == "assay":
            if not row["panel_id"].strip() or not row["target_id"].strip():
                raise EvidenceRegistryError(f"row {number}: assay row requires panel_id and target_id")
            assay_rows.append((number, row))
        by_strain[strain_id][evidence_type] += 1
    for number, row in assay_rows:
        material = materials.get(row["material_id"].strip())
        if material is None:
            raise EvidenceRegistryError(f"row {number}: assay material_id has no material record")
        if material["strain_id"].strip() != row["strain_id"].strip():
            raise EvidenceRegistryError(f"row {number}: assay strain_id differs from its material record")
    for material_id, row in materials.items():
        parent = row["parent_material_id"].strip()
        if parent and parent != "ROOT" and parent not in materials:
            raise EvidenceRegistryError(f"material {material_id!r}: parent_material_id has no material record")
        if row["material_level"].strip() in {"flash_fraction", "hplc_fraction"} and parent in {"", "ROOT"}:
            raise EvidenceRegistryError(f"material {material_id!r}: fraction requires a non-root parent_material_id")
    return {
        "status": "PASS", "record_count": len(rows), "strain_count": len(by_strain),
        "material_count": len(materials), "assay_record_count": len(assay_rows),
        "by_strain": {strain: dict(sorted(counts.items())) for strain, counts in sorted(by_strain.items())},
        "claim_ceiling": "Availability and lineage metadata only; registry rows do not establish activity, potency, identity, production, replication, or genomic causality.",
    }
