"""Private project handoff import runs every verification on the staged tree before copying.

A handoff whose files match their own hashes but whose catalog records a stale package manifest
hash, or whose portfolio hashes disagree with its manifest, was refused only after the copy had
already written into the destination.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

from mamey.project_catalog import ProjectCatalog, export_private_project_handoff, import_private_project_handoff

_spec = importlib.util.spec_from_file_location(
    "_catalog_fixture_464", Path(__file__).resolve().parent / "test_portable_project_catalog_v97391.py")
_fx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fx)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _export(tmp_path: Path, portfolio: bool = False) -> Path:
    source = tmp_path / "source"
    ProjectCatalog(source).register_package(_fx._package(source, "runs/demo/package"))
    if portfolio:
        _fx._bind_portfolio(source)
    return export_private_project_handoff(source, tmp_path / "handoff.zip")


def _rewrite(src: Path, dst: Path, *, stale_catalog: bool = False, portfolio_edit: bool = False) -> Path:
    with zipfile.ZipFile(src) as a:
        members = {name: a.read(name) for name in a.namelist()}
    manifest = json.loads(members["handoff_manifest.json"])
    if stale_catalog:
        name = next(n for n in members if n.endswith("project_catalog.json"))
        catalog = json.loads(members[name])
        catalog["entries"][0]["manifest_sha256"] = "0" * 64
        members[name] = json.dumps(catalog).encode()
        for record in manifest["files"]:
            if record["path"] == name:
                record["bytes"], record["sha256"] = len(members[name]), _sha(members[name])
        manifest["catalog_sha256"] = _sha(members[name])
    if portfolio_edit:
        manifest["portfolio"]["registry_sha256"] = "0" * 64
    members["handoff_manifest.json"] = json.dumps(manifest).encode()
    with zipfile.ZipFile(dst, "w") as b:
        for name, data in members.items():
            b.writestr(name, data)
    return dst


def _files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*")] if root.exists() else []


def test_stale_manifest_hash_is_refused_before_any_copy(tmp_path: Path) -> None:
    bad = _rewrite(_export(tmp_path), tmp_path / "stale.zip", stale_catalog=True)
    target = tmp_path / "target"
    with pytest.raises(ValueError, match="stale"):
        import_private_project_handoff(bad, target)
    assert _files(target) == []


def test_portfolio_hash_mismatch_is_refused_before_any_copy(tmp_path: Path) -> None:
    bad = _rewrite(_export(tmp_path, portfolio=True), tmp_path / "pf.zip", portfolio_edit=True)
    target = tmp_path / "target"
    with pytest.raises(ValueError, match="portfolio binding hash mismatch"):
        import_private_project_handoff(bad, target)
    assert _files(target) == []


def test_clean_handoff_still_imports(tmp_path: Path) -> None:
    report = import_private_project_handoff(_export(tmp_path, portfolio=True), tmp_path / "target")
    assert report["entry_count"] == 1
