"""Synthetic project and sessions only: c10 baselines never collide, and an unarmed check says so."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "c10_tool_drift.py"


def _run(project, mode, sid):
    env = dict(os.environ, SAPOTE_WORKSPACE_ROOT=str(project))
    payload = json.dumps({"session_id": sid}) if sid is not None else "not json"
    return subprocess.run([sys.executable, str(HOOK), "--mode", mode], input=payload, env=env,
                          capture_output=True, text=True, timeout=60)


def _project(tmp_path):
    project = tmp_path / "project"
    (project / "tools").mkdir(parents=True)
    tool = project / "tools" / "a.py"
    tool.write_text("print(1)\n", encoding="utf-8")
    return project, tool


def test_lossy_identifiers_get_separate_baselines(tmp_path):
    project, tool = _project(tmp_path)
    assert _run(project, "baseline", "same/a").returncode == 0
    tool.write_text("print(2)\n", encoding="utf-8")
    assert _run(project, "baseline", "same?a").returncode == 0
    baselines = list((project / "SAPOTE_CONTROL" / "tool_drift").glob("baseline_*.json"))
    assert len(baselines) == 2
    result = _run(project, "check", "same/a")
    assert result.returncode == 0
    assert "MODIFIED: tools/a.py" in result.stdout


def test_unarmed_check_is_not_silent(tmp_path):
    project, _ = _project(tmp_path)
    assert _run(project, "baseline", "other-session").returncode == 0
    result = _run(project, "check", "never-baselined")
    assert result.returncode == 0
    assert "unarmed" in result.stdout and "Nothing was compared" in result.stdout


def test_internal_error_is_not_silent(tmp_path):
    project, _ = _project(tmp_path)
    assert _run(project, "baseline", "s1").returncode == 0
    for baseline in (project / "SAPOTE_CONTROL" / "tool_drift").glob("baseline_*.json"):
        baseline.write_text("{not json", encoding="utf-8")
    result = _run(project, "check", "s1")
    assert result.returncode == 0
    assert "check not completed" in result.stdout


def test_unchanged_tools_stay_quiet(tmp_path):
    project, _ = _project(tmp_path)
    assert _run(project, "baseline", "s2").returncode == 0
    result = _run(project, "check", "s2")
    assert result.returncode == 0 and result.stdout == ""
