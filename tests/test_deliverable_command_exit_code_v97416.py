"""Portable regression coverage for .416 command and identity contracts."""
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def _run_surface_leads_hitting_the_guard(tmp_path):
    """Drive `surface-leads` through the CLI with a pre-existing canonical deliverable and no
    --out/--force, so the canonical-overwrite guard refuses. Returns the CompletedProcess."""
    data = tmp_path / "data"
    source = data / "strain_data/whole_bgc_majority_read_2026-08-05"
    source.mkdir(parents=True)
    (source / "whole_bgc_majority_read_cohort.csv").write_text("flags\n", encoding="utf-8")
    canonical = data / "strain_data/flagged_lead_surfacing_2026-08-05"
    canonical.mkdir(parents=True)
    (canonical / "flagged_lead_surfacing.csv").write_text("OWNER,DELIVERABLE\n", encoding="utf-8")
    cmd = [sys.executable, str(ROOT / "mamey_run.py"), "surface-leads"]
    result = subprocess.run(
        cmd, cwd=tmp_path,
        env=dict(os.environ, MAMEY_DATA_ROOT=str(data), PYTHONDONTWRITEBYTECODE="1"),
        capture_output=True, text=True, timeout=60,
    )
    return result, canonical


def test_guard_refusal_is_not_reported_as_success(tmp_path):
    result, canonical = _run_surface_leads_hitting_the_guard(tmp_path)
    # the guard must have protected the owner's file either way
    assert (canonical / "flagged_lead_surfacing.csv").read_text(encoding="utf-8") == "OWNER,DELIVERABLE\n"
    # the defect: exit 0 despite writing nothing. Fixed: a refusal is a non-zero exit.
    assert result.returncode != 0, (
        "guard refused the overwrite but the command exited 0 (success); a caller cannot tell "
        "'regenerated' from 'refused'. stderr=" + result.stderr
    )


def test_refusal_message_is_actionable(tmp_path):
    result, _ = _run_surface_leads_hitting_the_guard(tmp_path)
    # the user should be told how to proceed (the guard's own hint), not just see "skipped"
    assert "force" in result.stderr.lower() or "in-place" in result.stderr.lower(), result.stderr


def test_success_still_exits_zero(tmp_path):
    """A clean run with --out to a fresh dir must still exit 0 — the fix only changes failure paths."""
    data = tmp_path / "data"
    source = data / "strain_data/whole_bgc_majority_read_2026-08-05"
    source.mkdir(parents=True)
    (source / "whole_bgc_majority_read_cohort.csv").write_text("flags\n", encoding="utf-8")
    out = tmp_path / "fresh out"
    cmd = [sys.executable, str(ROOT / "mamey_run.py"), "surface-leads", "--out", str(out)]
    result = subprocess.run(
        cmd, cwd=tmp_path,
        env=dict(os.environ, MAMEY_DATA_ROOT=str(data), PYTHONDONTWRITEBYTECODE="1"),
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
