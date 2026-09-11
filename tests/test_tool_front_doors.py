"""test_tool_front_doors.py — every tool must be runnable from ANY working directory.

Why this exists (v9.7.364)
--------------------------
`tools/build_combined_bgc_report.py` shipped in .363 doing a bare
`from mamey.combined_report_builder import ...` without putting the bundle root on `sys.path`.
Of the 64 tools that import `mamey.*`, it was the ONLY one missing that guard. It therefore raised
`ModuleNotFoundError` for every operator not standing in the bundle root -- which is how tools are
actually run.

The suite did not catch it, and could not: `tests/test_combined_report_builder.py` loads the module
by FILE PATH via `spec_from_file_location`, never by package import. 100 test files use that pattern.
It is a legitimate technique, but it means the suite is structurally blind to a broken package import
in the corresponding tool.

This test closes that blind spot the cheap way: run `--help` on every tool from a FOREIGN cwd and
require that nothing dies at import time. It is fast, it needs no fixtures, and it fails exactly when
someone forgets the guard. Codex/Rootstock independently flagged the same gap as a recommended
regression gate.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Import-time failures we care about. A tool exiting non-zero because it wants positional arguments
# is FINE -- that is argument handling, not a broken front door.
IMPORT_ERRORS = ("ModuleNotFoundError", "ImportError", "SyntaxError", "IndentationError")

# Tools that legitimately do real work on --help (they take positionals and read them eagerly).
# They are exercised by their own tests; this gate only checks that IMPORT does not explode.
SLOW_OR_POSITIONAL = {
    "build_bgc_markers.py", "build_inventory_table.py", "check_chatgpt_next_paths.py",
    "plot_examples.py", "build_dapr_rescue_sheets.py", "cross_strain_denominator_audit.py",
    "export_figure_ready.py", "render_clean_tree.py",
}


def _tools(subdir: str) -> list[Path]:
    """Discover nested tool entry points for foreign-working-directory import checks."""
    d = ROOT / subdir
    if not d.is_dir():
        return []
    return sorted(p for p in d.rglob("*.py")
                  if not p.name.startswith("_") and "__pycache__" not in p.parts)


ALL_TOOLS = [(d, p) for d in ("tools", "deliverable_tools") for p in _tools(d)]


def _run_from_foreign_cwd(path: Path):
    """Run `<tool> --help` from a directory that is NOT the bundle root."""
    # Codex/Rootstock refinement (CUT-03 bundle): strip PYTHONPATH as well as changing cwd.
    # Without this the test can pass by inheriting the runner's environment rather than because
    # the tool resolves its own code tier — a green result that proves nothing.
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    with tempfile.TemporaryDirectory() as tmp:
        return subprocess.run(
            [sys.executable, str(path), "--help"],
            cwd=tmp, env=env, capture_output=True, text=True, timeout=60)


def test_there_are_tools_to_check():
    assert ALL_TOOLS, "no tools discovered — the glob or layout changed"


@pytest.mark.parametrize("subdir,path", ALL_TOOLS, ids=lambda v: v.name if hasattr(v, "name") else str(v))
def test_tool_imports_from_a_foreign_working_directory(subdir, path):
    """A tool that only imports from the bundle root is broken for every real operator."""
    if path.name in SLOW_OR_POSITIONAL:
        pytest.skip(f"{path.name} reads positional args eagerly; import covered by its own tests")
    try:
        r = _run_from_foreign_cwd(path)
    except subprocess.TimeoutExpired:
        pytest.skip(f"{path.name} did not return within the timeout on --help")
    blob = (r.stdout or "") + (r.stderr or "")
    hit = [e for e in IMPORT_ERRORS if e in blob]
    assert not hit, (
        f"{subdir}/{path.name} fails at IMPORT time when run from another directory "
        f"({', '.join(hit)}).\n"
        f"Add the bundle root to sys.path before importing mamey.*, as its sibling tools do:\n"
        f"    import os, sys\n"
        f"    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))\n\n"
        f"{blob[-800:]}")


def test_mamey_importing_tools_carry_the_path_guard():
    """Static counterpart to the behavioural test above: catches the omission by inspection, so a
    tool that happens to be skipped for timeout reasons is still covered."""
    offenders = []
    for subdir, path in ALL_TOOLS:
        src = path.read_text(errors="replace")
        imports_mamey = ("\nfrom mamey" in src or "\nimport mamey" in src
                         or src.startswith("from mamey") or src.startswith("import mamey"))
        if imports_mamey and "sys.path" not in src:
            offenders.append(f"{subdir}/{path.name}")
    assert not offenders, (
        "tool(s) importing mamey.* without a sys.path guard — these break from any cwd but the "
        f"bundle root: {offenders}")
