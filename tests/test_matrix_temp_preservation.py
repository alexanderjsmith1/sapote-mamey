"""CSV staging-file safety only: no scoring, XLSX generation or biological rows."""
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("matrix_candidate", ROOT / "tools/build_wetlab_matrix.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def setup(tmp_path, monkeypatch):
    pkg = tmp_path / "package"
    pkg.mkdir()
    manifest = pkg / "manifest.json"
    manifest.write_text(json.dumps({"strain_id": "SOFTWARE", "bgcs": []}))
    out = tmp_path / "output"
    out.mkdir()
    destination = out / "SOFTWARE_WetLab_Decision_Matrix.csv"
    foreign = Path(str(destination) + ".tmp")
    def forbidden(*args):
        pytest.fail("scoring must not run")
    monkeypatch.setattr(tool, "score_bgc", forbidden)
    monkeypatch.setattr(tool, "atomic_save", lambda *args, **kwargs: None)
    monkeypatch.setitem(sys.modules, "openpyxl", SimpleNamespace(Workbook=lambda: SimpleNamespace(active=SimpleNamespace(title="", append=lambda row: None))))
    monkeypatch.setattr(sys, "argv", ["build_wetlab_matrix.py", "--package-dir", str(pkg), "--out-dir", str(out)])
    return manifest, destination, foreign


@pytest.mark.parametrize("kind", ["ordinary", "symlink", "hardlink"])
def test_foreign_predictable_temp_survives_success(tmp_path, monkeypatch, kind):
    manifest, output, foreign = setup(tmp_path, monkeypatch)
    if kind == "ordinary":
        foreign.write_bytes(b"foreign staging evidence")
    elif kind == "symlink":
        foreign.symlink_to(manifest)
    else:
        os.link(manifest, foreign)
    source_before = manifest.read_bytes()
    foreign_before = foreign.read_bytes()
    inode_before = foreign.lstat().st_ino
    tool.main()
    assert manifest.read_bytes() == source_before
    assert foreign.exists() and foreign.read_bytes() == foreign_before
    assert foreign.lstat().st_ino == inode_before
    assert foreign.is_symlink() == (kind == "symlink")
    assert output.is_file() and not output.is_symlink()
    with output.open(newline="") as handle:
        rows = list(csv.reader(handle))
    assert len(rows) == 1 and rows[0][0] == "locator"
    assert sorted(p.name for p in output.parent.iterdir()) == sorted([output.name, foreign.name])


@pytest.mark.parametrize("foreign_kind", ["none", "ordinary", "symlink", "hardlink"])
def test_write_failure_preserves_output_and_source_and_cleans_own_temp(tmp_path, monkeypatch, foreign_kind):
    manifest, output, foreign = setup(tmp_path, monkeypatch)
    output.write_bytes(b"previous complete CSV")
    if foreign_kind == "ordinary":
        foreign.write_bytes(b"foreign staging evidence")
    elif foreign_kind == "symlink":
        foreign.symlink_to(manifest)
    elif foreign_kind == "hardlink":
        os.link(manifest, foreign)
    def snapshot():
        return {str(p.relative_to(tmp_path)): hashlib.sha256(p.read_bytes()).hexdigest() for p in tmp_path.rglob("*") if p.is_file()}
    before = snapshot()
    class BrokenWriter:
        def __init__(self, handle, **kwargs):
            self.handle = handle
        def writeheader(self):
            self.handle.write("partial staged header")
            raise RuntimeError("synthetic write failure")
    monkeypatch.setattr(tool, "_SafeDictWriter", BrokenWriter)
    with pytest.raises(RuntimeError, match="synthetic write failure"):
        tool.main()
    assert snapshot() == before
    assert output.read_bytes() == b"previous complete CSV"


def test_header_only_output_without_foreign_temp_keeps_existing_behavior(tmp_path, monkeypatch):
    manifest, output, foreign = setup(tmp_path, monkeypatch)
    before = manifest.read_bytes()
    tool.main()
    assert manifest.read_bytes() == before and not foreign.exists()
    assert len(output.read_text().splitlines()) == 1
    assert len(list(output.parent.iterdir())) == 1
