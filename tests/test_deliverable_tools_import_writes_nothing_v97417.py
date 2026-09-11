"""v9.7.417 — importing a deliverable tool must not put bytes on disk. Measured, not parsed.

`tests/test_tools_import_safe_v97250.py` proves the SHAPE — no top-level work, no unguarded
writes — by reading the AST. This file proves the BEHAVIOUR: it actually imports each script with
`SAPOTE_WORKSPACE_ROOT` pointed at an empty temp directory and asserts nothing appears there.

Why both. An AST gate answers "is the code arranged safely"; only an execution answers "does
importing it write". Measured on the v9.7.416 UNSEALED_01 candidate BEFORE the guards, this probe
caught `build_working_genome_set.py` creating
`sapote_deliverables/WORKING_GENOME_SET_2026-08-03/WORKING_GENOME_SET.csv` on import into a
workspace that had nothing in it at all. The other six raised FileNotFoundError first — which is
the fixture being empty, not those scripts being safe; against a real workspace, where their inputs
exist, they proceed to their writes. That asymmetry is exactly why the shape gate needs a
behavioural partner: six of the seven would have looked innocent in this probe alone.

The scripts still run normally as scripts — the guarded body is unchanged and only indented, and
`tests/test_fair_cohort_analysis_no_dated_glob_v97397.py` continues to drive one of them as a
subprocess.

Claim safety: filesystem hygiene. No score moves and no biological claim is made or admitted.
"""
from __future__ import annotations

import importlib.util
import os
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = ROOT / "deliverable_tools"

# Every deliverable tool whose top level is a script. Kept as an explicit list rather than a glob so
# a new one has to be added deliberately, and so a rename shows up as a failure rather than silence.
SCRIPTS = (
    "build_cohort_index.py",
    "build_novelty_board.py",
    "build_working_genome_set.py",
    "extract_cohort_clusterblast.py",
    "extract_comprehensive_both.py",
    "fair_cohort_analysis.py",
    "rebuild_cohort_comparison.py",
)


@pytest.mark.parametrize("script", SCRIPTS)
def test_importing_writes_nothing(script, tmp_path, monkeypatch):
    path = TOOLS / script
    assert path.is_file(), f"{script} has moved or been renamed; update SCRIPTS"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(workspace))
    monkeypatch.chdir(workspace)              # the tools fall back to cwd when the env var is unset
    monkeypatch.syspath_prepend(str(TOOLS))
    monkeypatch.syspath_prepend(str(ROOT))

    spec = importlib.util.spec_from_file_location(f"import_probe_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)           # must not raise: a guarded script imports cleanly

    created = sorted(p for p in workspace.rglob("*") if p.is_file())
    assert not created, (
        f"importing {script} wrote {[str(p.relative_to(workspace)) for p in created]} into the "
        "workspace. Move the write behind the `__main__` guard.")


@pytest.mark.parametrize("script", SCRIPTS)
def test_script_still_has_a_body_to_run(script):
    """Guard against the lazy repair: deleting the work instead of guarding it."""
    import ast
    tree = ast.parse((TOOLS / script).read_text(encoding="utf-8", errors="replace"))
    guards = [n for n in tree.body
              if isinstance(n, ast.If) and "__name__" in ast.dump(n.test) and "__main__" in ast.dump(n.test)]
    assert len(guards) == 1, f"{script} should have exactly one `__main__` guard"
    assert len(guards[0].body) >= 2, (
        f"{script}'s guard is nearly empty; the script body should have moved INTO it, not away")
