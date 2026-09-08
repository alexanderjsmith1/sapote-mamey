"""BC2 .400 audit: tools/check_duplicate_dict_keys.py's own docstring states its whole purpose
is catching SILENT data loss from a duplicate dict-literal key. `collect()` used
`rp.rglob("*.py")`, which silently swallows a per-directory OSError -- an unreadable
subdirectory's contents are simply absent from the scan, no signal. The gate's own v9.7.395
fix already refuses to report PASS when the TOTAL scan finds zero files -- but that guard does
not fire when at least one OTHER directory was readable, so a real collision sitting inside an
unscannable directory alongside ordinary readable files still reports PASS: the exact silent
data-loss failure this gate exists to catch, hidden by a partial, unsignalled scan gap.

This gate is wired into `tools/repo_health.py`'s "[hard] collisions" check, which
`tools/release_cut.sh` and `.github/workflows/ci.yml` both invoke -- unlike a purely
standalone script, a coverage gap here sits directly in the release/CI path. That said: no
permission-restricted directory has been observed in this repo's real `mamey/`, `tools/`, or
`tests/` trees (the existing `test_shipped_tree_still_passes_and_reports_scan_count` /
`test_gate_passes_on_the_shipped_tree` tests confirm the real trees scan clean under this
fix too) -- this closes a reproducible coverage gap in a CI-wired gate, not a claim that a real
collision has ever silently slipped through it.

Reproduced directly against the real tool (subprocess, not a reimplementation).
"""
from __future__ import annotations

import os
import subprocess
import sys
import pathlib

import pytest

TOOL = pathlib.Path(__file__).resolve().parents[1] / "tools" / "check_duplicate_dict_keys.py"


def _run(root: pathlib.Path) -> tuple[str, str, int]:
    proc = subprocess.run([sys.executable, str(TOOL), "--root", str(root)],
                           capture_output=True, text=True)
    return proc.stdout, proc.stderr, proc.returncode


@pytest.fixture
def locked_dir_with_real_collision(tmp_path):
    """One ordinary readable .py file (so the total-scan is nonzero) plus one unreadable
    subdirectory containing a real, silently-data-losing dict-literal collision."""
    visible = tmp_path / "visible"
    visible.mkdir()
    (visible / "fine.py").write_text('D2 = {"a": 1, "b": 2}\n')

    locked = tmp_path / "locked_sub"
    locked.mkdir()
    (locked / "bad.py").write_text('D = {"AS-XXX": 1, "AS-XXX": 2}\n')
    os.chmod(locked, 0o000)
    if os.access(locked, os.R_OK):
        os.chmod(locked, 0o755)
        pytest.skip("chmod(0) does not restrict read access for this user (e.g. running as root)")
    yield tmp_path
    os.chmod(locked, 0o755)  # restore so pytest/tmp_path cleanup can remove it


def test_tool_present():
    assert TOOL.is_file(), "tools/check_duplicate_dict_keys.py not found"


def test_unreadable_directory_is_reported_not_silently_passed(locked_dir_with_real_collision):
    """The actual regression this fix closes: a real collision inside an unreadable directory,
    with at least one OTHER file readable (so the v9.7.395 zero-files guard does not fire),
    must make the gate error out (exit 2) rather than silently print PASS."""
    out, err, rc = _run(locked_dir_with_real_collision)
    assert rc == 2, f"expected the gate to refuse PASS on a partial scan; got rc={rc}, out={out!r}, err={err!r}"
    assert "could not be scanned" in err
    assert "locked_sub" in err
    assert "PASS" not in out


def test_clean_tree_with_no_permission_issues_still_passes(tmp_path):
    """No regression: an ordinary, fully-readable tree with no collisions still passes."""
    (tmp_path / "ok.py").write_text('D = {"a": 1, "b": 2}\n')
    out, err, rc = _run(tmp_path)
    assert rc == 0
    assert "PASS" in out


def test_readable_collision_still_fails_same_as_before(tmp_path):
    """No regression: a real, readable collision still fails the gate exactly as before --
    this fix only changes the silent-skip case, not the direct-detection case."""
    (tmp_path / "bad.py").write_text('D = {"x": 1, "x": 2}\n')
    out, err, rc = _run(tmp_path)
    assert rc == 1
    assert "FAIL" in out or "FAIL" in err
    assert "SILENTLY DISCARDED" in err
