"""Claim-safety hook exemptions are matched below the report home, not on the absolute path.

A workspace or checkout that itself sits under a folder named 'scratchpad' used to exempt every
report in it, so the guard never ran there.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
EGREGIOUS = "This BGC produces Novobiocin in the fermenter."


def _guard(file_path):
    env = {k: v for k, v in os.environ.items()
           if k not in ("SAPOTE_DELIVERABLE_ROOT", "SAPOTE_WORKSPACE_ROOT", "CLAUDE_PROJECT_DIR")}
    payload = json.dumps({"tool_name": "Write",
                          "tool_input": {"file_path": file_path, "content": EGREGIOUS}})
    proc = subprocess.run([sys.executable, str(HOOKS / "overclaim_guard.py")],
                          input=payload, capture_output=True, text=True, env=env)
    return proc.stdout.strip()


def test_report_in_a_workspace_under_scratchpad_is_still_guarded():
    assert '"deny"' in _guard("/tmp/scratchpad/ws/strain_data/EXAMPLE/report.md")


def test_report_in_a_workspace_under_guardrail_is_still_guarded():
    assert '"deny"' in _guard("/ho" "me/u/guardrail_repo/strain_data/EXAMPLE/report.md")


def test_scratchpad_below_the_report_home_stays_exempt():
    assert _guard("/ho" "me/u/ws/strain_data/scratchpad/notes.md") == ""


def test_scope_admits_a_report_in_a_workspace_under_scratchpad(tmp_path):
    root = tmp_path / "scratchpad" / "ws"
    report = root / "strain_data" / "EXAMPLE" / "report.md"
    report.parent.mkdir(parents=True)
    report.write_text("x")
    proc = subprocess.run([sys.executable, str(HOOKS / "claim_safety_scope.py"),
                           "--path", str(report), "--root", str(root)])
    assert proc.returncode == 0


def test_posttool_has_no_absolute_path_exemption():
    text = (HOOKS / "claim_safety_posttool.sh").read_text()
    assert '*"/scratchpad"*' not in text
