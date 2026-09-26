"""v9.7.443: deliverable builders refuse to write inside the code bundle.

Each script takes ROOT from SAPOTE_WORKSPACE_ROOT, else the current directory. Run from the bundle
root with no workspace set, they wrote sapote_deliverables/ (or bgc_markers.json) into the sealed
bundle. Each now checks its real output path first and stops with the reason. With a workspace
set, the check stays out of the way.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

CASES = [
    ("deliverable_tools/bgc_widget.py", ["--strain", "AS-TEST"]),
    ("deliverable_tools/roster_v2.py", ["--strain", "AS-TEST"]),
    ("deliverable_tools/insert_tree_into_report.py", ["--strain", "AS-TEST"]),
    ("deliverable_tools/build_cohort_index.py", []),
    ("deliverable_tools/build_novelty_board.py", []),
    ("deliverable_tools/extract_cohort_clusterblast.py", []),
    ("deliverable_tools/extract_comprehensive_both.py", []),
    ("deliverable_tools/fair_cohort_analysis.py", []),
    ("deliverable_tools/rebuild_cohort_comparison.py", []),
    ("tools/build_bgc_markers.py", []),
]


def _env(**extra):
    env = {k: v for k, v in os.environ.items() if k not in ("SAPOTE_WORKSPACE_ROOT", "SAPOTE_ROOT")}
    env.update(extra)
    return env


def _run(script, args, env):
    return subprocess.run([sys.executable, str(ROOT / script), *args], cwd=str(ROOT), env=env,
                          capture_output=True, text=True, timeout=120)


@pytest.mark.parametrize("script,args", CASES, ids=[Path(c[0]).stem for c in CASES])
def test_refuses_from_the_bundle_root_and_creates_nothing(script, args):
    before = {p.name for p in ROOT.iterdir()}
    r = _run(script, args, _env())
    assert r.returncode != 0
    assert "OUTPUT_INSIDE_BUNDLE" in (r.stdout + r.stderr)
    assert {p.name for p in ROOT.iterdir()} == before
    assert not (ROOT / "sapote_deliverables").exists()
    assert not (ROOT / "bgc_markers.json").exists()


@pytest.mark.parametrize("script,args", CASES, ids=[Path(c[0]).stem for c in CASES])
def test_a_workspace_outside_the_bundle_is_not_refused(script, args, tmp_path):
    # build_bgc_markers takes its folder as the first argument, not from SAPOTE_WORKSPACE_ROOT.
    if script.endswith("build_bgc_markers.py"):
        args = [str(tmp_path)]
    r = _run(script, args, _env(SAPOTE_WORKSPACE_ROOT=str(tmp_path)))
    assert "OUTPUT_INSIDE_BUNDLE" not in (r.stdout + r.stderr)
