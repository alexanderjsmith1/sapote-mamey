"""Guard: no shipped path may contain shell brace characters (W2)."""
import pathlib
import importlib.util

_TOOL = pathlib.Path(__file__).resolve().parent.parent / "tools" / "check_no_brace_paths.py"
_spec = importlib.util.spec_from_file_location("check_no_brace_paths", _TOOL)
chk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(chk)

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_no_brace_paths_in_tier():
    bad = [str(p) for p in ROOT.rglob("*") if "{" in p.name or "}" in p.name]
    assert bad == [], f"brace path(s) present: {bad}"
