from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from mamey.project_catalog import ProjectCatalog, export_private_project_handoff, import_private_project_handoff
from mamey.portfolio_config import PORTFOLIO_SCHEMA, load_portfolio_binding, write_portfolio_binding


def _package(root: Path, relative: str, strain: str = "DEMO-001") -> Path:
    package = root / relative
    package.mkdir(parents=True)
    (package / "manifest.json").write_text(json.dumps({
        "strain_id": strain,
        "bundle_version": "9.7.391",
        "workflow_version": "1.9.140",
        "privacy_tier": "EMBARGOED",
        "privacy_assignment_state": "PROFILE_ASSIGNED",
    }), encoding="utf-8")
    (package / "DEMO-001_2_inventory.csv").write_text("BGC_ID\nBGC001\n", encoding="utf-8")
    return package


def test_catalog_uses_relative_locator_and_rechecks_manifest_hash(tmp_path: Path) -> None:
    root = tmp_path / "project"
    package = _package(root, "runs/demo/package")
    entry = ProjectCatalog(root).register_package(package)
    assert entry.package_relative_path == "runs/demo/package"
    assert entry.privacy_tier == "EMBARGOED"
    assert ProjectCatalog(root).verified_packages() == (package,)
    (package / "manifest.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="stale"):
        ProjectCatalog(root).verified_packages()


def test_catalog_refuses_package_outside_explicit_root(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="below the explicit project root"):
        ProjectCatalog(tmp_path / "project").register_package(_package(tmp_path / "outside", "package"))


def test_private_handoff_is_relative_hash_bound_and_imports_to_empty_root(tmp_path: Path) -> None:
    source = tmp_path / "source"
    ProjectCatalog(source).register_package(_package(source, "runs/demo/package"))
    archive = export_private_project_handoff(source, tmp_path / "handoff.zip")
    target = tmp_path / "target"
    report = import_private_project_handoff(archive, target)
    assert report["entry_count"] == 1
    assert report["handoff_class"] == "PRIVATE_PROJECT_HANDOFF_ONLY"
    assert ProjectCatalog(target).verified_packages()[0].relative_to(target).as_posix() == "runs/demo/package"


def test_import_refuses_nonempty_destination_and_path_traversal(tmp_path: Path) -> None:
    source = tmp_path / "source"
    ProjectCatalog(source).register_package(_package(source, "runs/demo/package"))
    archive = export_private_project_handoff(source, tmp_path / "handoff.zip")
    target = tmp_path / "target"
    target.mkdir()
    (target / "already_here").write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="empty destination"):
        import_private_project_handoff(archive, target)


def _bind_portfolio(root: Path) -> None:
    """B8/v9.7.405: set up a project_registry.json + portfolio.json + written binding, matching
    the CODEX_391_PORTFOLIO_AWARE_PRIVATE_HANDOFF_2026-08-29 lineage adapted onto
    mamey/project_registry.py (see mamey/project_catalog.py::_portfolio_files)."""
    registry_payload = {
        "schema_version": "sapote_project_registry_v1",
        "privacy_tiers": [{"tier_id": "LAB_INTERNAL", "audience_rank": 0}],
        "strains": [{"strain_id": "DEMO-001", "privacy_tier": "LAB_INTERNAL"}],
    }
    (root / "project_registry.json").write_text(json.dumps(registry_payload), encoding="utf-8")
    (root / "portfolio.json").write_text(json.dumps({
        "schema_version": PORTFOLIO_SCHEMA,
        "project_registry": "project_registry.json",
    }), encoding="utf-8")
    binding = load_portfolio_binding(root, root / "portfolio.json")
    write_portfolio_binding(root, binding)


def test_private_handoff_travels_with_a_bound_portfolio_and_verifies_on_import(tmp_path: Path) -> None:
    source = tmp_path / "source"
    ProjectCatalog(source).register_package(_package(source, "runs/demo/package"))
    _bind_portfolio(source)
    archive = export_private_project_handoff(source, tmp_path / "handoff.zip")
    target = tmp_path / "target"
    report = import_private_project_handoff(archive, target)
    assert report["entry_count"] == 1
    assert (target / "lab_quest_outputs" / "portfolio_binding.json").is_file()
    assert (target / "portfolio.json").is_file()
    assert (target / "project_registry.json").is_file()


def test_private_handoff_refuses_a_stale_portfolio_binding(tmp_path: Path) -> None:
    source = tmp_path / "source"
    ProjectCatalog(source).register_package(_package(source, "runs/demo/package"))
    _bind_portfolio(source)
    binding_path = source / "lab_quest_outputs" / "portfolio_binding.json"
    payload = json.loads(binding_path.read_text(encoding="utf-8"))
    payload["registry_sha256"] = "0" * 64
    binding_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="stale"):
        export_private_project_handoff(source, tmp_path / "handoff.zip")


def test_private_handoff_with_no_portfolio_binding_omits_it(tmp_path: Path) -> None:
    source = tmp_path / "source"
    ProjectCatalog(source).register_package(_package(source, "runs/demo/package"))
    archive = export_private_project_handoff(source, tmp_path / "handoff.zip")
    with zipfile.ZipFile(archive) as zf:
        manifest = json.loads(zf.read("handoff_manifest.json"))
    assert "portfolio" not in manifest


def test_private_handoff_refuses_legacy_absolute_source_locator(tmp_path: Path) -> None:
    root = tmp_path / "project"
    package = _package(root, "runs/demo/package")
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    manifest["input_zip"] = "/old-machine/private/input.zip"
    (package / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    ProjectCatalog(root).register_package(package)
    with pytest.raises(ValueError, match="absolute locator"):
        export_private_project_handoff(root, tmp_path / "handoff.zip")
