"""Typed loader for an operator-provisioned reference-strain registry.

The registry is governance/reference metadata, not bundled engine data and not
biological validation. Resolution follows the OFFICIAL_DATA contract: an
explicit ``MAMEY_OFFICIAL_DATA`` root is exclusive; otherwise
``MAMEY_DATA_ROOT/OFFICIAL_DATA`` is exclusive; only without either override
may an in-tree parent ``OFFICIAL_DATA`` directory be discovered.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path


FILENAME = "REFERENCE_STRAIN_REGISTRY.csv"
HEADER = (
    "id", "display", "cohort_class", "target_domain", "is_outgroup",
    "genus", "species", "strain", "accession", "acc_master", "regions",
    "has_mamey_401", "dup_group", "dup_same_assembly", "dup_species",
    "staged_zip", "needs_type_verification", "source_flag",
)
_BOOL_FIELDS = frozenset({
    "is_outgroup", "has_mamey_401", "dup_same_assembly", "dup_species",
    "needs_type_verification",
})
_TRUE = frozenset({"1", "true", "yes", "y"})
_FALSE = frozenset({"0", "false", "no", "n"})


class ReferenceStrainRegistryError(ValueError):
    """Raised when the configured registry is absent, ambiguous, or malformed."""


@dataclass(frozen=True)
class ReferenceStrainRecord:
    id: str
    display: str
    cohort_class: str
    target_domain: str
    is_outgroup: bool | None
    genus: str
    species: str
    strain: str
    accession: str
    acc_master: str
    regions: int | None
    has_mamey_401: bool | None
    dup_group: str
    dup_same_assembly: bool | None
    dup_species: bool | None
    staged_zip: str
    needs_type_verification: bool | None
    source_flag: str

    @property
    def taxon_label(self) -> str:
        """Return recorded taxonomy components without guessing missing values."""
        return " ".join(part for part in (self.genus, self.species, self.strain) if part)


@dataclass(frozen=True)
class ReferenceStrainRegistry:
    source_path: Path
    source_sha256: str
    records: tuple[ReferenceStrainRecord, ...]

    def by_id(self) -> dict[str, ReferenceStrainRecord]:
        return {record.id: record for record in self.records}

    def for_target_domain(self, target_domain: str) -> tuple[ReferenceStrainRecord, ...]:
        wanted = str(target_domain or "").strip().casefold()
        return tuple(record for record in self.records if record.target_domain.casefold() == wanted)


def _candidate_paths() -> list[Path]:
    official = os.environ.get("MAMEY_OFFICIAL_DATA")
    if official:
        return [Path(official).expanduser() / FILENAME]
    data_root = os.environ.get("MAMEY_DATA_ROOT")
    if data_root:
        return [Path(data_root).expanduser() / "OFFICIAL_DATA" / FILENAME]
    here = Path(__file__).resolve()
    return [parent / "OFFICIAL_DATA" / FILENAME for parent in here.parents]


def resolve_reference_strain_registry(path: str | Path | None = None) -> Path:
    candidates = [Path(path).expanduser()] if path is not None else _candidate_paths()
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    rendered = ", ".join(str(candidate) for candidate in candidates)
    raise ReferenceStrainRegistryError(
        f"{FILENAME} is not provisioned; checked: {rendered}. "
        "Bind OFFICIAL_DATA explicitly rather than embedding project rows in the code tier."
    )


def _boolean(value: str, field: str, row_number: int) -> bool | None:
    normalized = value.strip().casefold()
    if not normalized:
        return None
    if normalized in _TRUE:
        return True
    if normalized in _FALSE:
        return False
    raise ReferenceStrainRegistryError(
        f"row {row_number} field {field} must be true/false/yes/no/1/0 or blank"
    )


def _regions(value: str, row_number: int) -> int | None:
    normalized = value.strip()
    if not normalized:
        return None
    try:
        result = int(normalized)
    except ValueError as exc:
        raise ReferenceStrainRegistryError(f"row {row_number} regions must be an integer or blank") from exc
    if result < 0:
        raise ReferenceStrainRegistryError(f"row {row_number} regions must be non-negative")
    return result


def load_reference_strain_registry(path: str | Path | None = None) -> ReferenceStrainRegistry:
    source = resolve_reference_strain_registry(path)
    try:
        raw = source.read_bytes()
        text = raw.decode("utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise ReferenceStrainRegistryError(f"cannot read {source}: {exc}") from exc

    reader = csv.DictReader(text.splitlines())
    fields = tuple(reader.fieldnames or ())
    if fields != HEADER or len(set(fields)) != len(fields):
        raise ReferenceStrainRegistryError(
            "reference-strain registry header mismatch; expected exactly: " + ",".join(HEADER)
        )

    records: list[ReferenceStrainRecord] = []
    seen_ids: set[str] = set()
    for row_number, row in enumerate(reader, start=2):
        values = {field: str(row.get(field) or "").strip() for field in HEADER}
        if not any(values.values()):
            continue
        identifier = values["id"]
        if not identifier:
            raise ReferenceStrainRegistryError(f"row {row_number} requires id")
        if identifier in seen_ids:
            raise ReferenceStrainRegistryError(f"duplicate reference-strain id: {identifier}")
        seen_ids.add(identifier)
        converted = dict(values)
        for field in _BOOL_FIELDS:
            converted[field] = _boolean(values[field], field, row_number)
        converted["regions"] = _regions(values["regions"], row_number)
        records.append(ReferenceStrainRecord(**converted))

    return ReferenceStrainRegistry(
        source_path=source,
        source_sha256=hashlib.sha256(raw).hexdigest(),
        records=tuple(records),
    )


__all__ = [
    "FILENAME", "HEADER", "ReferenceStrainRecord", "ReferenceStrainRegistry",
    "ReferenceStrainRegistryError", "resolve_reference_strain_registry",
    "load_reference_strain_registry",
]
