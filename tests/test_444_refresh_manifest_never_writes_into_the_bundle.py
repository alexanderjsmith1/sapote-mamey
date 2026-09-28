"""The figure-source manifest refresher must never write into the bundle.

tools/refresh_figure_source_manifest.py rewrites MANIFEST.json in the folder it sits in. It is meant to run inside
an exported tree-figure source package. Before v9.7.444 it ignored its arguments, so the tool front-door test's
`--help` call rewrote tools/MANIFEST.json on every run, hashing whatever sat in tools/ (a Finder .DS_Store included).
That file was an accident of this (first shipped in v9.7.428) and is no longer part of the bundle.
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "refresh_figure_source_manifest.py"


def _run(script: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True, timeout=60)


def test_bundle_ships_no_tools_manifest():
    assert not (ROOT / "tools" / "MANIFEST.json").exists()


def test_help_writes_nothing(tmp_path):
    pkg = tmp_path / "package"
    pkg.mkdir()
    shutil.copy2(SCRIPT, pkg / SCRIPT.name)
    r = _run(pkg / SCRIPT.name, "--help")
    assert r.returncode == 0 and "usage" in r.stdout.lower()
    assert not (pkg / "MANIFEST.json").exists()


def test_refuses_inside_a_bundle_layout(tmp_path):
    (tmp_path / "mamey").mkdir()
    (tmp_path / "mamey" / "__init__.py").write_text("")
    (tmp_path / "tools").mkdir()
    shutil.copy2(SCRIPT, tmp_path / "tools" / SCRIPT.name)
    (tmp_path / "tools" / "stray.txt").write_text("x")
    r = _run(tmp_path / "tools" / SCRIPT.name)
    assert r.returncode == 2 and "refusing" in r.stderr
    assert not (tmp_path / "tools" / "MANIFEST.json").exists()


def test_still_refreshes_an_exported_package(tmp_path):
    pkg = tmp_path / "package"
    pkg.mkdir()
    shutil.copy2(SCRIPT, pkg / SCRIPT.name)
    (pkg / "tree.nwk").write_text("(A,B);\n")
    r = _run(pkg / SCRIPT.name)
    assert r.returncode == 0, r.stderr
    assert "tree.nwk" in (pkg / "MANIFEST.json").read_text()
