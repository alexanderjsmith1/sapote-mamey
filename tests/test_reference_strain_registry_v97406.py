from __future__ import annotations

import csv
from pathlib import Path

import pytest

from mamey.reference_strain_registry import (
    HEADER,
    ReferenceStrainRegistryError,
    load_reference_strain_registry,
)


def _write(path: Path, rows: list[dict[str, str]], header=HEADER) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(header))
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in header} for row in rows)
    return path


def _row(identifier: str, **updates) -> dict[str, str]:
    row = {field: "" for field in HEADER}
    row.update({
        "id": identifier,
        "display": "Synthetic reference",
        "cohort_class": "REFERENCE",
        "target_domain": "synthetic-domain",
        "is_outgroup": "false",
        "genus": "Genus",
        "species": "species",
        "strain": "strain-token",
        "accession": "GCF_000000001.1",
        "regions": "7",
        "has_mamey_401": "yes",
        "dup_same_assembly": "0",
        "dup_species": "no",
        "needs_type_verification": "true",
        "source_flag": "SYNTHETIC_FIXTURE",
    })
    row.update(updates)
    return row


def test_loads_exact_schema_with_typed_values_and_source_hash(tmp_path):
    path = _write(tmp_path / "REFERENCE_STRAIN_REGISTRY.csv", [_row("REF-001")])
    registry = load_reference_strain_registry(path)
    record = registry.records[0]
    assert record.id == "REF-001"
    assert record.regions == 7
    assert record.has_mamey_401 is True
    assert record.dup_species is False
    assert record.needs_type_verification is True
    assert record.taxon_label == "Genus species strain-token"
    assert len(registry.source_sha256) == 64
    assert registry.by_id()["REF-001"] is record
    assert registry.for_target_domain("SYNTHETIC-DOMAIN") == (record,)


def test_rejects_header_drift_duplicate_id_and_bad_typed_values(tmp_path):
    bad_header = tuple(field for field in HEADER if field != "source_flag")
    with pytest.raises(ReferenceStrainRegistryError, match="header mismatch"):
        load_reference_strain_registry(_write(tmp_path / "header.csv", [_row("REF-001")], bad_header))
    with pytest.raises(ReferenceStrainRegistryError, match="duplicate"):
        load_reference_strain_registry(_write(tmp_path / "duplicate.csv", [_row("REF-001"), _row("REF-001")]))
    with pytest.raises(ReferenceStrainRegistryError, match="must be true/false"):
        load_reference_strain_registry(_write(tmp_path / "bool.csv", [_row("REF-001", is_outgroup="maybe")]))
    with pytest.raises(ReferenceStrainRegistryError, match="non-negative"):
        load_reference_strain_registry(_write(tmp_path / "regions.csv", [_row("REF-001", regions="-1")]))


def test_explicit_official_data_override_is_exclusive(tmp_path, monkeypatch):
    missing = tmp_path / "selected"
    fallback = tmp_path / "fallback" / "OFFICIAL_DATA"
    _write(fallback / "REFERENCE_STRAIN_REGISTRY.csv", [_row("REF-001")])
    monkeypatch.setenv("MAMEY_OFFICIAL_DATA", str(missing))
    monkeypatch.setenv("MAMEY_DATA_ROOT", str(tmp_path / "fallback"))
    with pytest.raises(ReferenceStrainRegistryError, match="not provisioned"):
        load_reference_strain_registry()
