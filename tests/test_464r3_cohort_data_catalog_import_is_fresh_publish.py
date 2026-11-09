"""A refused private-handoff import leaves the destination as it was; publish never merges."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from mamey.project_catalog import ProjectCatalog, export_private_project_handoff, import_private_project_handoff

_spec = importlib.util.spec_from_file_location(
    "_catalog_fixture_464r3", Path(__file__).resolve().parent / "test_portable_project_catalog_v97391.py")
_fx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fx)


def _export(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    ProjectCatalog(source).register_package(_fx._package(source, "runs/demo/package"))
    return export_private_project_handoff(source, tmp_path / "handoff.zip")


def test_invalid_zip_does_not_create_an_absent_destination(tmp_path: Path) -> None:
    bad = tmp_path / "bad.zip"
    bad.write_bytes(b"not a zip at all")
    target = tmp_path / "deeper" / "target"
    with pytest.raises(Exception):
        import_private_project_handoff(bad, target)
    assert not target.exists()
    assert not target.parent.exists()


def test_destination_filled_during_import_is_not_merged(tmp_path: Path, monkeypatch) -> None:
    handoff = _export(tmp_path)
    target = tmp_path / "target"
    real = ProjectCatalog.verification_report
    state = {"done": False}

    def racing(self):
        result = real(self)
        if not state["done"]:
            state["done"] = True
            target.mkdir(exist_ok=True)
            (target / "other_writer.txt").write_text("theirs")
        return result

    monkeypatch.setattr(ProjectCatalog, "verification_report", racing)
    with pytest.raises(ValueError, match="no longer empty"):
        import_private_project_handoff(handoff, target)
    assert sorted(p.name for p in target.iterdir()) == ["other_writer.txt"]
    assert (target / "other_writer.txt").read_text() == "theirs"
    assert not any(p.name.startswith("mamey_project_import_") for p in tmp_path.iterdir())


def test_clean_import_into_absent_and_empty_destinations(tmp_path: Path) -> None:
    handoff = _export(tmp_path)
    absent = tmp_path / "absent"
    report = import_private_project_handoff(handoff, absent)
    assert report["entry_count"] == 1
    empty = tmp_path / "empty"
    empty.mkdir()
    report = import_private_project_handoff(handoff, empty)
    assert report["entry_count"] == 1
