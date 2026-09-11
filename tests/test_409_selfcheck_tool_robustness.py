"""tests/test_409_selfcheck_tool_robustness.py — CLAUDE_409_selfcheck_tool_robustness lane.

Fail-before / pass-after coverage for three self-diagnostic front doors that crash
on their own edge/help paths (see scratch/round4_sweep/SELFCHECK_HARNESS_RUN.md):

  1. tools/audit_blastp_zero_alignment.py  — no existence check on --overlay/--xml
     single-file inputs -> raw FileNotFoundError traceback instead of a typed exit-2.
  2. tools/audit_documents_wheelhouse.py    — default --profile resolved against the
     process cwd, so the preflight was only runnable from the bundle root.
  3. tools/check_chatgpt_next_paths.py      — hand-rolled argv handling fed "--help"
     to Path().read_text() -> traceback; missing input file did the same.

Each tool is a standalone front door (its stdout IS the receipt), so these tests
drive the real script through a subprocess and assert on exit code + streams.
Behavior on VALID input is unchanged; only the error/help edge paths move.

FAIL-BEFORE on pristine v9.7.408: help/missing-input crash with a Traceback and a
non-typed exit, and the wheelhouse default profile is not found off the bundle root.
PASS-AFTER: clean typed messages, exit 0 on --help, exit 2 on bad input.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


# --- locate the bundle the same way the sibling 409 lanes do ---------------- #
def _bundle_root() -> Path:
    try:
        import mamey  # noqa: F401
        return Path(mamey.__file__).resolve().parent.parent
    except Exception:
        env = os.environ.get("SAPOTE_BUNDLE")
        if env:
            return Path(env).resolve()
        # last resort: walk up looking for a tools/ dir carrying our targets
        here = Path(__file__).resolve()
        for parent in here.parents:
            if (parent / "tools" / "check_chatgpt_next_paths.py").is_file():
                return parent
        pytest.skip("cannot locate the Sapote-Mamey bundle root")


BUNDLE = _bundle_root()
TOOLS = BUNDLE / "tools"


def _run(script: str, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOLS / script), *args],
        capture_output=True, text=True, cwd=str(cwd) if cwd else None,
    )


# ======================================================================== #
# Tool 1: audit_blastp_zero_alignment.py
# ======================================================================== #
def test_blastp_overlay_missing_file_is_typed_exit2_not_traceback():
    r = _run("audit_blastp_zero_alignment.py", "--overlay", "/nope/does_not_exist.csv")
    assert r.returncode == 2, r.stderr
    assert "INPUT_NOT_FOUND" in r.stderr
    assert "Traceback" not in r.stderr


def test_blastp_xml_missing_path_is_typed_exit2_not_traceback():
    r = _run("audit_blastp_zero_alignment.py", "--xml", "/nope/no_such_dir")
    assert r.returncode == 2, r.stderr
    assert "INPUT_NOT_FOUND" in r.stderr
    assert "Traceback" not in r.stderr


def test_blastp_help_exits_zero():
    r = _run("audit_blastp_zero_alignment.py", "--help")
    assert r.returncode == 0
    assert "--overlay" in r.stdout


def test_blastp_valid_overlay_still_exits_zero(tmp_path: Path):
    """Behavior-preserved: a clean overlay with no zero-alignment signature -> exit 0."""
    csv = tmp_path / "AS_x_online_blastp.csv"
    csv.write_text(
        "gene,agreement,blastp_top_def,pct_identity\n"
        "g1,AGREE,some hit,95.0\n"
        "g2,AGREE,another hit,88.0\n",
        encoding="utf-8",
    )
    r = _run("audit_blastp_zero_alignment.py", "--overlay", str(csv))
    assert r.returncode == 0, r.stderr


# ======================================================================== #
# Tool 2: audit_documents_wheelhouse.py
# ======================================================================== #
def test_wheelhouse_default_profile_resolves_off_bundle_root(tmp_path: Path):
    """FAIL-BEFORE: run from a foreign cwd, the default profile was looked up under
    that cwd and the receipt error named documents.txt.
    PASS-AFTER: the default profile resolves against the bundle, so the run gets past
    profile-read and fails (if at all) on the wheelhouse, not the missing profile."""
    missing_wh = tmp_path / "no_such_wheelhouse"  # nonexistent -> WHEELHOUSE_NOT_FOUND
    r = _run("audit_documents_wheelhouse.py", "--wheelhouse", str(missing_wh), cwd=tmp_path)
    report = json.loads(r.stdout)
    error = report.get("error", "")
    assert "documents.txt" not in error, f"default profile not anchored to bundle: {error}"
    assert "WHEELHOUSE_NOT_FOUND" in error


def test_wheelhouse_help_exits_zero():
    r = _run("audit_documents_wheelhouse.py", "--help")
    assert r.returncode == 0
    assert "--wheelhouse" in r.stdout


# ======================================================================== #
# Tool 3: check_chatgpt_next_paths.py
# ======================================================================== #
def test_next_paths_help_exits_zero_not_treated_as_filename():
    r = _run("check_chatgpt_next_paths.py", "--help")
    assert r.returncode == 0
    assert "Traceback" not in r.stderr
    assert "usage" in r.stdout.lower()


def test_next_paths_missing_file_is_typed_exit2_not_traceback():
    r = _run("check_chatgpt_next_paths.py", "/nope/HANDOFF.md")
    assert r.returncode == 2, r.stderr
    assert "INPUT_NOT_FOUND" in r.stderr
    assert "Traceback" not in r.stderr


def test_next_paths_valid_handoff_still_evaluates(tmp_path: Path):
    """Behavior-preserved: a well-formed 8-item handback still passes (exit 0)."""
    md = tmp_path / "HANDOFF.md"
    md.write_text(
        "\n".join(f"{i}. next path number {i} distinct object alpha{i}" for i in range(1, 9)),
        encoding="utf-8",
    )
    r = _run("check_chatgpt_next_paths.py", str(md))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS" in r.stdout


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
