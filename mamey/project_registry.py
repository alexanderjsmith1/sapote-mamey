"""Generic strain privacy, genome-state, and bioassay-scope registry.

Privacy is user-declared at project level.  It is never inferred from a strain
prefix.  Genome availability and bioassay availability are independent axes,
and assay results use typed states so missing work is not collapsed into a
negative biological result.
"""

from __future__ import annotations

import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import hashlib
import io
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping


GENOME_STATES = frozenset({
    "NOT_PROVIDED",
    "AVAILABLE_NOT_ANALYZED",
    "ANALYZED",
    "UNBOUND",
})
PUBLICATION_STATES = frozenset({
    "NOT_PROVIDED",
    "UNPUBLISHED",
    "IN_PREPARATION",
    "SUBMITTED",
    "IN_PRESS",
    "PUBLISHED",
})
MATERIAL_LEVELS = frozenset({
    "CRUDE_EXTRACT",
    "FLASH_FRACTION",
    "HPLC_FRACTION",
    "PURIFIED_COMPOUND",
    "OTHER",
})
ASSAY_RESULT_STATES = frozenset({
    "NOT_TESTED",
    "TESTED_NO_ACTIVITY_AT_RECORDED_CONDITIONS",
    "OBSERVED_ACTIVITY_AT_RECORDED_CONDITIONS",
    "INDETERMINATE",
    "NOT_RETURNED",
    "UNBOUND",
})


class ProjectRegistryError(ValueError):
    """Raised when project metadata is incomplete or internally inconsistent."""


class PrivacyHold(PermissionError):
    """Raised when a requested export is not authorized by declared tiers."""


@dataclass(frozen=True)
class PrivacyTier:
    tier_id: str
    audience_rank: int
    description: str = ""


@dataclass(frozen=True)
class StrainRecord:
    strain_id: str
    privacy_tier: str
    display_label: str = ""
    publication_status: str = "NOT_PROVIDED"
    genome_state: str = "NOT_PROVIDED"
    genome_locator: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AssayRecord:
    assay_id: str
    strain_id: str
    privacy_tier: str
    material_level: str
    result_state: str
    material_id: str = ""
    parent_material_id: str = ""
    fractionation_method: str = ""
    target_ids: tuple[str, ...] = ()
    endpoint: str = ""
    units: str = ""
    concentration_or_dose: str = ""
    replicate_count: int | None = None
    recorded_result: str = ""
    conditions: str = ""
    protocol_locator: str = ""
    source_locator: str = ""
    source_sha256: str = ""
    publication_status: str = "NOT_PROVIDED"


def _required_text(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ProjectRegistryError(f"Missing required field: {field_name}")
    return text


def _optional_state(value: Any, allowed: frozenset[str], field_name: str) -> str:
    text = str(value or "NOT_PROVIDED").strip().upper()
    if text not in allowed:
        raise ProjectRegistryError(
            f"Invalid {field_name} {text!r}; expected one of {sorted(allowed)}"
        )
    return text


def _targets(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, Iterable):
        values = list(value)
    else:
        raise ProjectRegistryError("target_ids must be a string or list of strings")
    return tuple(dict.fromkeys(str(item).strip() for item in values if str(item).strip()))


class ProjectRegistry:
    """Validated registry with fail-closed privacy and independent data axes.

    ``audience_rank`` is an access requirement: larger numbers require a more
    privileged audience.  The effective privacy of linked material is the
    maximum rank among the strain, artifact, assay, and result records.
    """

    def __init__(
        self,
        *,
        tiers: Mapping[str, PrivacyTier],
        strains: Mapping[str, StrainRecord],
        assays: Iterable[AssayRecord] = (),
        public_export_tier: str = "",
        source_sha256: str = "",
        source_name: str = "",
    ) -> None:
        self.tiers = dict(tiers)
        self.strains = dict(strains)
        self.assays = tuple(assays)
        self.public_export_tier = str(public_export_tier or "").strip()
        self.source_sha256 = source_sha256
        self.source_name = source_name
        if not self.tiers:
            raise ProjectRegistryError("At least one privacy tier is required")
        if self.public_export_tier and self.public_export_tier not in self.tiers:
            raise ProjectRegistryError(
                f"Unknown public_export_tier: {self.public_export_tier!r}"
            )
        for record in self.strains.values():
            self._require_tier(record.privacy_tier)
        for assay in self.assays:
            if assay.strain_id not in self.strains:
                raise ProjectRegistryError(
                    f"Assay {assay.assay_id!r} references unknown strain {assay.strain_id!r}"
                )
            self._require_tier(assay.privacy_tier)

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
        *,
        source_sha256: str = "",
        source_name: str = "",
    ) -> "ProjectRegistry":
        if str(payload.get("schema_version") or "") not in {"1", "1.0", "sapote_project_registry_v1"}:
            raise ProjectRegistryError("schema_version must be sapote_project_registry_v1")

        tiers: dict[str, PrivacyTier] = {}
        raw_tiers = payload.get("privacy_tiers") or []
        for raw in raw_tiers:
            tier_id = _required_text(raw.get("tier_id"), "privacy_tiers[].tier_id")
            if tier_id in tiers:
                raise ProjectRegistryError(f"Duplicate privacy tier: {tier_id}")
            try:
                rank = int(raw.get("audience_rank"))
            except (TypeError, ValueError):
                raise ProjectRegistryError(
                    f"privacy tier {tier_id!r} requires integer audience_rank"
                ) from None
            if rank < 0:
                raise ProjectRegistryError("audience_rank must be >= 0")
            tiers[tier_id] = PrivacyTier(
                tier_id=tier_id,
                audience_rank=rank,
                description=str(raw.get("description") or "").strip(),
            )

        strains: dict[str, StrainRecord] = {}
        for raw in payload.get("strains") or []:
            strain_id = _required_text(raw.get("strain_id"), "strains[].strain_id")
            if strain_id in strains:
                raise ProjectRegistryError(f"Duplicate strain: {strain_id}")
            strains[strain_id] = StrainRecord(
                strain_id=strain_id,
                privacy_tier=_required_text(raw.get("privacy_tier"), "strains[].privacy_tier"),
                display_label=str(raw.get("display_label") or "").strip(),
                publication_status=_optional_state(
                    raw.get("publication_status"), PUBLICATION_STATES, "publication_status"
                ),
                genome_state=_optional_state(raw.get("genome_state"), GENOME_STATES, "genome_state"),
                genome_locator=str(raw.get("genome_locator") or "").strip(),
                metadata=dict(raw.get("metadata") or {}),
            )

        assays: list[AssayRecord] = []
        seen_assays: set[str] = set()
        for raw in payload.get("assays") or []:
            assay_id = _required_text(raw.get("assay_id"), "assays[].assay_id")
            if assay_id in seen_assays:
                raise ProjectRegistryError(f"Duplicate assay: {assay_id}")
            seen_assays.add(assay_id)
            material = _optional_state(raw.get("material_level"), MATERIAL_LEVELS, "material_level")
            result = _optional_state(raw.get("result_state"), ASSAY_RESULT_STATES, "result_state")
            publication = _optional_state(
                raw.get("publication_status"), PUBLICATION_STATES, "publication_status"
            )
            replicate = raw.get("replicate_count")
            if replicate in (None, ""):
                replicate_value = None
            else:
                try:
                    replicate_value = int(replicate)
                except (TypeError, ValueError):
                    raise ProjectRegistryError(
                        f"Assay {assay_id!r} replicate_count must be an integer"
                    ) from None
                if replicate_value < 0:
                    raise ProjectRegistryError("replicate_count must be >= 0")
            assays.append(AssayRecord(
                assay_id=assay_id,
                strain_id=_required_text(raw.get("strain_id"), "assays[].strain_id"),
                privacy_tier=_required_text(raw.get("privacy_tier"), "assays[].privacy_tier"),
                material_level=material,
                result_state=result,
                material_id=str(raw.get("material_id") or "").strip(),
                parent_material_id=str(raw.get("parent_material_id") or "").strip(),
                fractionation_method=str(raw.get("fractionation_method") or "").strip(),
                target_ids=_targets(raw.get("target_ids")),
                endpoint=str(raw.get("endpoint") or "").strip(),
                units=str(raw.get("units") or "").strip(),
                concentration_or_dose=str(raw.get("concentration_or_dose") or "").strip(),
                replicate_count=replicate_value,
                recorded_result=str(raw.get("recorded_result") or "").strip(),
                conditions=str(raw.get("conditions") or "").strip(),
                protocol_locator=str(raw.get("protocol_locator") or "").strip(),
                source_locator=str(raw.get("source_locator") or "").strip(),
                source_sha256=str(raw.get("source_sha256") or "").strip(),
                publication_status=publication,
            ))

        return cls(
            tiers=tiers,
            strains=strains,
            assays=assays,
            public_export_tier=str(payload.get("public_export_tier") or "").strip(),
            source_sha256=source_sha256,
            source_name=source_name,
        )

    def _require_tier(self, tier_id: str) -> PrivacyTier:
        try:
            return self.tiers[str(tier_id)]
        except KeyError:
            raise ProjectRegistryError(f"Unknown privacy tier: {tier_id!r}") from None

    def require_strain(self, strain_id: str) -> StrainRecord:
        try:
            return self.strains[str(strain_id)]
        except KeyError:
            raise PrivacyHold(
                f"Strain {strain_id!r} has no explicit project privacy declaration"
            ) from None

    def assays_for(self, strain_id: str) -> tuple[AssayRecord, ...]:
        self.require_strain(strain_id)
        return tuple(assay for assay in self.assays if assay.strain_id == strain_id)

    def effective_privacy_tier(
        self,
        strain_id: str,
        linked_tiers: Iterable[str] = (),
    ) -> str:
        record = self.require_strain(strain_id)
        candidates = [record.privacy_tier, *[str(item) for item in linked_tiers]]
        return max(candidates, key=lambda tier_id: self._require_tier(tier_id).audience_rank)

    def authorize_export(
        self,
        strain_id: str,
        audience_tier: str,
        linked_tiers: Iterable[str] = (),
    ) -> dict[str, Any]:
        audience = self._require_tier(audience_tier)
        required_id = self.effective_privacy_tier(strain_id, linked_tiers)
        required = self._require_tier(required_id)
        allowed = audience.audience_rank >= required.audience_rank
        return {
            "allowed": allowed,
            "strain_id": strain_id,
            "audience_tier": audience.tier_id,
            "audience_rank": audience.audience_rank,
            "effective_privacy_tier": required.tier_id,
            "required_rank": required.audience_rank,
            "reason": "AUDIENCE_AUTHORIZED" if allowed else "PRIVACY_TIER_HOLD",
        }

    def legacy_release(self, strain_id: str, linked_tiers: Iterable[str] = ()) -> str:
        """Compatibility bridge for existing PUBLIC/PRIVATE consumers.

        PUBLIC is possible only when the project explicitly names a
        ``public_export_tier`` and that tier is authorized for the record.  A
        missing public tier fails closed to PRIVATE.  Strain-name prefixes are
        never consulted.
        """
        if not self.public_export_tier:
            self.require_strain(strain_id)
            return "PRIVATE"
        decision = self.authorize_export(strain_id, self.public_export_tier, linked_tiers)
        return "PUBLIC" if decision["allowed"] else "PRIVATE"

    def assay_summary(self, strain_id: str) -> dict[str, Any]:
        assays = self.assays_for(strain_id)
        targets = sorted({target for assay in assays for target in assay.target_ids})
        material_levels = sorted({assay.material_level for assay in assays})
        result_states: dict[str, int] = {}
        for assay in assays:
            result_states[assay.result_state] = result_states.get(assay.result_state, 0) + 1
        return {
            "assay_data_state": "AVAILABLE" if assays else "NOT_PROVIDED",
            "assay_record_count": len(assays),
            "unique_target_count": len(targets),
            "target_ids": targets,
            "material_levels": material_levels,
            "result_state_counts": dict(sorted(result_states.items())),
            "claim_guard": (
                "NOT_TESTED, NOT_RETURNED, UNBOUND, and absent records are workflow states, "
                "not biological inactivity. TESTED_NO_ACTIVITY_AT_RECORDED_CONDITIONS is "
                "condition-bounded and must not be generalized."
            ),
        }

    def strain_snapshot(self, strain_id: str) -> dict[str, Any]:
        record = self.require_strain(strain_id)
        assays = self.assays_for(strain_id)
        linked_tiers = [assay.privacy_tier for assay in assays]
        effective_tier = self.effective_privacy_tier(strain_id, linked_tiers)
        return {
            "schema_version": "sapote_project_registry_snapshot_v1",
            "source": {
                "name": self.source_name,
                "sha256": self.source_sha256,
            },
            "privacy_contract": {
                "strain_privacy_tier": record.privacy_tier,
                "effective_package_privacy_tier": effective_tier,
                "privacy_tier_source": "USER_DECLARED_PROJECT_REGISTRY",
                "public_export_tier": self.public_export_tier or "NOT_DECLARED",
                "legacy_release": self.legacy_release(strain_id, linked_tiers),
                "rule": "Effective privacy is the most restrictive linked tier; unknown strains fail closed.",
            },
            "strain": asdict(record),
            "genome_axis": {
                "state": record.genome_state,
                "locator": record.genome_locator,
            },
            "bioassay_axis": self.assay_summary(strain_id),
            "assays": [asdict(assay) for assay in assays],
        }


def load_project_registry(path: str | Path) -> ProjectRegistry:
    source = Path(path)
    raw = source.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, Mapping):
        raise ProjectRegistryError("Project registry root must be a JSON object")
    return ProjectRegistry.from_dict(
        payload,
        source_sha256=hashlib.sha256(raw).hexdigest(),
        source_name=source.name,
    )


def write_strain_registry_surfaces(
    package_dir: str | Path,
    registry: ProjectRegistry,
    strain_id: str,
) -> dict[str, Any]:
    """Write the declared strain snapshot and a flat assay companion table."""
    root = Path(package_dir)
    root.mkdir(parents=True, exist_ok=True)
    snapshot = registry.strain_snapshot(strain_id)
    (root / "project_registry_snapshot.json").write_text(
        json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8"
    )

    fields = [
        "assay_id", "strain_id", "privacy_tier", "material_level", "material_id",
        "parent_material_id", "fractionation_method", "target_ids", "endpoint", "units",
        "concentration_or_dose", "replicate_count", "result_state", "recorded_result",
        "conditions", "protocol_locator", "source_locator", "source_sha256",
        "publication_status",
    ]
    stream = io.StringIO(newline="")
    writer = _SafeDictWriter(stream, fieldnames=fields, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for assay in registry.assays_for(strain_id):
        row = asdict(assay)
        row["target_ids"] = ";".join(assay.target_ids)
        writer.writerow(row)
    (root / "bioassay_scope.tsv").write_text(stream.getvalue(), encoding="utf-8")
    return {
        "snapshot": "project_registry_snapshot.json",
        "bioassay_scope": "bioassay_scope.tsv",
        "privacy_tier": snapshot["privacy_contract"]["effective_package_privacy_tier"],
        "legacy_release": snapshot["privacy_contract"]["legacy_release"],
        "genome_state": snapshot["genome_axis"]["state"],
        "assay_record_count": snapshot["bioassay_axis"]["assay_record_count"],
    }
