"""Private project handoff import refuses repeated ZIP members and repeated manifest paths.

The member check compared sets, so a second member with the same name, or a manifest listing a
path twice, passed and one copy was never hash-checked.
"""
from __future__ import annotations

import importlib.util
import json
import warnings
import zipfile
from pathlib import Path

import pytest

from mamey.project_catalog import ProjectCatalog, export_private_project_handoff, import_private_project_handoff

_spec = importlib.util.spec_from_file_location(
    "_catalog_fixture_458", Path(__file__).resolve().parent / "test_portable_project_catalog_v97391.py")
_fx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fx)


def _export(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    ProjectCatalog(source).register_package(_fx._package(source, "runs/demo/package"))
    return export_private_project_handoff(source, tmp_path / "handoff.zip")


def _rewrite(src: Path, dst: Path, *, extra=None, manifest_edit=None) -> Path:
    with zipfile.ZipFile(src) as a, zipfile.ZipFile(dst, "w") as b, warnings.catch_warnings():
        warnings.simplefilter("ignore")   # zipfile warns on a duplicate name; that is the point
        for name in a.namelist():
            data = a.read(name)
            if name == "handoff_manifest.json" and manifest_edit:
                m = json.loads(data)
                manifest_edit(m)
                data = json.dumps(m).encode()
            b.writestr(name, data)
        if extra:
            b.writestr(extra[0], extra[1])
    return dst


def test_repeated_member_is_refused(tmp_path: Path) -> None:
    good = _export(tmp_path)
    with zipfile.ZipFile(good) as a:
        name = next(n for n in a.namelist() if n.endswith("inventory.csv"))
    bad = _rewrite(good, tmp_path / "dup_member.zip", extra=(name, b"BGC_ID\nBGC999\n"))
    with pytest.raises(ValueError, match="repeats a member name"):
        import_private_project_handoff(bad, tmp_path / "t1")


def test_repeated_manifest_path_is_refused(tmp_path: Path) -> None:
    good = _export(tmp_path)
    bad = _rewrite(good, tmp_path / "dup_manifest.zip",
                   manifest_edit=lambda m: m["files"].append(dict(m["files"][0])))
    with pytest.raises(ValueError, match="more than once"):
        import_private_project_handoff(bad, tmp_path / "t2")


def test_clean_handoff_still_imports(tmp_path: Path) -> None:
    assert import_private_project_handoff(_export(tmp_path), tmp_path / "t3")["entry_count"] == 1
