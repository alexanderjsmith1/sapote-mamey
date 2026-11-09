"""build_deliverable_menu_widget: an existing --out (including the shipped default) needs --replace."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "build_deliverable_menu_widget.py"


def _run(*args):
    return subprocess.run([sys.executable, str(TOOL), *map(str, args)], capture_output=True, text=True, cwd=ROOT)


def test_existing_out_is_refused_and_kept(tmp_path):
    out = tmp_path / "menu.html"
    out.write_text("keep me")
    result = _run("--out", out)
    assert result.returncode == 2
    assert "refused" in result.stderr
    assert out.read_text() == "keep me"


def test_default_out_is_the_shipped_page_and_is_refused():
    shipped = ROOT / "bundle_support" / "deliverable_menu_widget.html"
    before = shipped.read_bytes()
    result = _run()
    assert result.returncode == 2
    assert shipped.read_bytes() == before


def test_new_out_is_written_and_replace_rewrites(tmp_path):
    out = tmp_path / "menu.html"
    assert _run("--out", out).returncode == 0
    assert out.read_text().startswith("<!doctype html>")
    out.write_text("old")
    assert _run("--out", out, "--replace").returncode == 0
    assert out.read_text().startswith("<!doctype html>")
