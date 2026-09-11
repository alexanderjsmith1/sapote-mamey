"""Bind a portable multi-strain project registry to one explicit project root.

This module turns the operator-declared project privacy/evidence registry (see
`mamey/project_registry.py`) into an explicit, hash-bound project configuration for the optional
Lab Quest interface. It reports only typed availability, privacy-tier, and workflow-state
metadata. It never derives activity, potency, ecological association, product identity, or a
genome-to-assay causal link.

Rebase note (B8/v9.7.405): the original Codex candidate for this module
(CODEX_391_PORTABLE_PORTFOLIO_CONFIGURATION_2026-08-29) bound to a separate
`mamey/privacy_profile.py` + `mamey/evidence_registry.py` pair. That pair was never landed in this
bundle; `mamey/project_registry.py` (BC-4, landed) is the actual producer of the sealed package's
`privacy_tier`/`privacy_assignment_state` fields (see `mamey/models.py`) and is the single source
of truth for privacy tiers and heterogeneous strain/assay evidence in this cut. This module
consumes `project_registry.py`'s `ProjectRegistry` directly rather than adding a third/fourth
privacy mechanism -- the portable-project-configuration *shape* (a small pointer config file naming
one registry file, both hash-bound and contained below the project root) is carried over from the
Codex candidate; the registry format underneath it is not.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from .project_registry import ProjectRegistry, ProjectRegistryError, load_project_registry


PORTFOLIO_SCHEMA = "sapote_project_portfolio_v1"
PORTFOLIO_BINDING_SCHEMA = "mamey_portfolio_binding_v1"


class PortfolioConfigError(ValueError):
    """Raised when a portable portfolio configuration is absent, stale, or invalid."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _root(value: str | Path) -> Path:
    if value is None or (isinstance(value, str) and not value.strip()):
        raise PortfolioConfigError("an explicit project root is required")
    root = Path(value).expanduser().resolve()
    if not root.is_dir():
        raise PortfolioConfigError("project root is not a directory")
    return root


def _relative_path(root: Path, raw: object, label: str) -> tuple[str, Path]:
    text = str(raw or "").strip()
    candidate = PurePosixPath(text)
    if not text or candidate.is_absolute() or ".." in candidate.parts or candidate.parts[0] in {"", "."}:
        raise PortfolioConfigError(f"{label} must be a nonempty relative logical path")
    path = root.joinpath(*candidate.parts).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise PortfolioConfigError(f"{label} escapes the selected project root") from exc
    if not path.is_file():
        raise PortfolioConfigError(f"{label} is not an existing regular file")
    return candidate.as_posix(), path


@dataclass(frozen=True)
class PortfolioBinding:
    config_relative_path: str
    config_sha256: str
    registry_relative_path: str
    registry_sha256: str
    public_export_tier: str
    availability: dict[str, Any]

    @property
    def claim_ceiling(self) -> str:
        return (
            "Portfolio availability reports evidence inventory, privacy tiers, material lineage, "
            "and workflow-state metadata only. It does not establish activity, potency, "
            "production, identity, replication, ecology, genomic causality, scientific "
            "acceptance, release approval, or publication readiness."
        )

    def as_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["schema"] = PORTFOLIO_BINDING_SCHEMA
        result["claim_ceiling"] = self.claim_ceiling
        return result


def _portfolio_availability(registry: ProjectRegistry) -> dict[str, Any]:
    """Roll up every declared strain's privacy/genome/assay state -- navigation only."""
    rows: list[dict[str, Any]] = []
    for strain_id in sorted(registry.strains):
        record = registry.strains[strain_id]
        assays = registry.assays_for(strain_id)
        linked_tiers = [assay.privacy_tier for assay in assays]
        effective_tier = registry.effective_privacy_tier(strain_id, linked_tiers)
        summary = registry.assay_summary(strain_id)
        rows.append({
            "strain_id": strain_id,
            "privacy_tier": record.privacy_tier,
            "effective_privacy_tier": effective_tier,
            "genome_state": record.genome_state,
            "publication_status": record.publication_status,
            "assay_data_state": summary["assay_data_state"],
            "assay_record_count": summary["assay_record_count"],
            "unique_target_count": summary["unique_target_count"],
            "material_levels": summary["material_levels"],
            "result_state_counts": summary["result_state_counts"],
        })
    return {"strain_count": len(rows), "strains": rows}


def load_portfolio_binding(project_root: str | Path, config_path: str | Path) -> PortfolioBinding:
    """Load a project configuration and revalidate the project registry it names."""
    root = _root(project_root)
    raw_config = Path(config_path).expanduser()
    if not raw_config.is_absolute():
        raw_config = root / raw_config
    try:
        logical_config = raw_config.resolve().relative_to(root).as_posix()
    except ValueError as exc:
        raise PortfolioConfigError("portfolio config escapes the selected project root") from exc
    config_relative, config = _relative_path(root, logical_config, "portfolio config")
    try:
        raw = json.loads(config.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PortfolioConfigError(f"portfolio config is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict) or raw.get("schema_version") != PORTFOLIO_SCHEMA:
        raise PortfolioConfigError(f"portfolio config schema_version must be {PORTFOLIO_SCHEMA}")
    registry_relative, registry_path = _relative_path(root, raw.get("project_registry"), "project_registry")
    try:
        registry = load_project_registry(registry_path)
    except ProjectRegistryError as exc:
        raise PortfolioConfigError(str(exc)) from exc
    return PortfolioBinding(
        config_relative_path=config_relative,
        config_sha256=_sha256(config),
        registry_relative_path=registry_relative,
        registry_sha256=_sha256(registry_path),
        public_export_tier=registry.public_export_tier or "NOT_DECLARED",
        availability=_portfolio_availability(registry),
    )


def write_portfolio_binding(project_root: str | Path, binding: PortfolioBinding) -> Path:
    """Write additive project-root provenance, never inside a sealed package."""
    root = _root(project_root)
    path = root / "lab_quest_outputs" / "portfolio_binding.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(binding.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path
