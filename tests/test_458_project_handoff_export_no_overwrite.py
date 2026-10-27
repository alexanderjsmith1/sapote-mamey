"""Private project handoff export refuses an existing archive and never leaves a partial one.

It opened the output with ZipFile(output, "w"): an existing handoff was replaced, and a failure
part-way left a truncated archive at the final path.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

import mamey.project_catalog as pc
from mamey.project_catalog import ProjectCatalog, export_private_project_handoff

_spec = importlib.util.spec_from_file_location(
    "_catalog_fixture_458e", Path(__file__).resolve().parent / "test_portable_project_catalog_v97391.py")
_fx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fx)


def _source(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    ProjectCatalog(source).register_package(_fx._package(source, "runs/demo/package"))
    return source


def test_existing_archive_is_not_replaced(tmp_path: Path) -> None:
    out = tmp_path / "handoff.zip"
    out.write_bytes(b"an earlier handoff")
    with pytest.raises(ValueError, match="already exists"):
        export_private_project_handoff(_source(tmp_path), out)
    assert out.read_bytes() == b"an earlier handoff"


def test_failed_export_leaves_no_archive(tmp_path: Path, monkeypatch) -> None:
    source = _source(tmp_path)
    out = tmp_path / "handoff.zip"
    real = pc.json.dumps

    def boom(obj, *a, **k):
        if isinstance(obj, dict) and obj.get("schema") == pc.HANDOFF_SCHEMA:
            raise OSError("disk full")
        return real(obj, *a, **k)

    monkeypatch.setattr(pc.json, "dumps", boom)
    with pytest.raises(OSError):
        export_private_project_handoff(source, out)
    assert not out.exists()
    assert not list(tmp_path.glob(".handoff.zip.*"))
