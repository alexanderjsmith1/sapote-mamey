"""test_portable_portfolio_configuration_v97405.py -- mamey/portfolio_config.py + its operator
front door tools/validate_portfolio_config.py (B8/v9.7.405, rebased from
CODEX_391_PORTABLE_PORTFOLIO_CONFIGURATION_2026-08-29 onto mamey/project_registry.py -- see the
rebase note at the top of mamey/portfolio_config.py).

Synthetic fixtures only: fake strain/assay identifiers, tmp_path-only paths.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
PY = sys.executable

from mamey.portfolio_config import (
    PORTFOLIO_SCHEMA,
    PortfolioConfigError,
    load_portfolio_binding,
    write_portfolio_binding,
)


def _registry_payload() -> dict:
    return {
        "schema_version": "sapote_project_registry_v1",
        "privacy_tiers": [
            {"tier_id": "LAB_INTERNAL", "audience_rank": 0, "description": "lab-only"},
            {"tier_id": "COLLABORATOR", "audience_rank": 1, "description": "named collaborators"},
            {"tier_id": "PUBLIC", "audience_rank": 2, "description": "public"},
        ],
        "public_export_tier": "PUBLIC",
        "strains": [
            {
                "strain_id": "SYN-001",
                "privacy_tier": "LAB_INTERNAL",
                "genome_state": "ANALYZED",
                "publication_status": "UNPUBLISHED",
            },
            {
                "strain_id": "SYN-002",
                "privacy_tier": "PUBLIC",
                "genome_state": "NOT_PROVIDED",
                "publication_status": "PUBLISHED",
            },
        ],
        "assays": [
            {
                "assay_id": "A1", "strain_id": "SYN-001", "privacy_tier": "LAB_INTERNAL",
                "material_level": "CRUDE_EXTRACT", "result_state": "NOT_TESTED",
            },
            {
                "assay_id": "A2", "strain_id": "SYN-001", "privacy_tier": "LAB_INTERNAL",
                "material_level": "HPLC_FRACTION",
                "result_state": "OBSERVED_ACTIVITY_AT_RECORDED_CONDITIONS",
                "target_ids": ["SYN-TARGET-1"],
            },
        ],
    }


def _write_project(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "project"
    root.mkdir()
    registry_path = root / "project_registry.json"
    registry_path.write_text(json.dumps(_registry_payload()), encoding="utf-8")
    config_path = root / "portfolio.json"
    config_path.write_text(json.dumps({
        "schema_version": PORTFOLIO_SCHEMA,
        "project_registry": "project_registry.json",
    }), encoding="utf-8")
    return root, config_path


# ---------------------------------------------------------------------------
# load_portfolio_binding
# ---------------------------------------------------------------------------

def test_load_portfolio_binding_rolls_up_every_declared_strain(tmp_path):
    root, config_path = _write_project(tmp_path)
    binding = load_portfolio_binding(root, config_path)
    assert binding.registry_relative_path == "project_registry.json"
    assert binding.public_export_tier == "PUBLIC"
    assert binding.availability["strain_count"] == 2
    rows = {row["strain_id"]: row for row in binding.availability["strains"]}
    assert rows["SYN-001"]["privacy_tier"] == "LAB_INTERNAL"
    assert rows["SYN-001"]["assay_record_count"] == 2
    assert rows["SYN-001"]["assay_data_state"] == "AVAILABLE"
    assert rows["SYN-002"]["assay_record_count"] == 0
    assert rows["SYN-002"]["assay_data_state"] == "NOT_PROVIDED"
    assert "activity" in binding.claim_ceiling.lower()


def test_load_portfolio_binding_config_schema_version_enforced(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "project_registry.json").write_text(json.dumps(_registry_payload()), encoding="utf-8")
    bad_config = root / "portfolio.json"
    bad_config.write_text(json.dumps({"schema_version": "wrong", "project_registry": "project_registry.json"}), encoding="utf-8")
    with pytest.raises(PortfolioConfigError, match="schema_version"):
        load_portfolio_binding(root, bad_config)


def test_load_portfolio_binding_registry_path_must_be_relative_and_contained(tmp_path):
    root, config_path = _write_project(tmp_path)
    (tmp_path / "outside_registry.json").write_text(
        json.dumps(_registry_payload()), encoding="utf-8"
    )
    config_path.write_text(json.dumps({
        "schema_version": PORTFOLIO_SCHEMA,
        "project_registry": "../outside_registry.json",
    }), encoding="utf-8")
    with pytest.raises(
        PortfolioConfigError,
        match="project_registry must be a nonempty relative logical path",
    ):
        load_portfolio_binding(root, config_path)


def test_load_portfolio_binding_config_must_not_escape_project_root(tmp_path):
    root, config_path = _write_project(tmp_path)
    outside = tmp_path / "outside_config.json"
    outside.write_text(config_path.read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(PortfolioConfigError, match="escapes"):
        load_portfolio_binding(root, outside)


def test_load_portfolio_binding_invalid_registry_raises_portfolio_error(tmp_path):
    root, config_path = _write_project(tmp_path)
    (root / "project_registry.json").write_text(json.dumps({"schema_version": "sapote_project_registry_v1"}), encoding="utf-8")
    with pytest.raises(PortfolioConfigError, match="privacy tier"):
        load_portfolio_binding(root, config_path)


def test_load_portfolio_binding_requires_explicit_project_root():
    with pytest.raises(PortfolioConfigError, match="explicit project root"):
        load_portfolio_binding("", "portfolio.json")


# ---------------------------------------------------------------------------
# write_portfolio_binding
# ---------------------------------------------------------------------------

def test_write_portfolio_binding_writes_additive_provenance_file(tmp_path):
    root, config_path = _write_project(tmp_path)
    binding = load_portfolio_binding(root, config_path)
    out = write_portfolio_binding(root, binding)
    assert out == root / "lab_quest_outputs" / "portfolio_binding.json"
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["schema"] == "mamey_portfolio_binding_v1"
    assert payload["availability"]["strain_count"] == 2
    assert "claim_ceiling" in payload


# ---------------------------------------------------------------------------
# operator front door: tools/validate_portfolio_config.py
# ---------------------------------------------------------------------------

def _run_tool(args):
    return subprocess.run([PY, str(TOOLS / "validate_portfolio_config.py"), *args],
                           capture_output=True, text=True)


def test_cli_binds_and_prints_json(tmp_path):
    root, config_path = _write_project(tmp_path)
    proc = _run_tool(["--project-root", str(root), "--config", str(config_path)])
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["availability"]["strain_count"] == 2


def test_cli_write_binding_flag_writes_file(tmp_path):
    root, config_path = _write_project(tmp_path)
    proc = _run_tool(["--project-root", str(root), "--config", str(config_path), "--write-binding"])
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert (root / "lab_quest_outputs" / "portfolio_binding.json").is_file()
    assert payload["binding_path"] == str(root / "lab_quest_outputs" / "portfolio_binding.json")


def test_cli_refuses_bad_config_nonzero_exit(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    proc = _run_tool(["--project-root", str(root), "--config", "nope.json"])
    assert proc.returncode != 0
    assert proc.stdout == ""
