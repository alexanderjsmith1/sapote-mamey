"""BC2 .401 audit: tools/check_command_pointers.py — the phantom-command guard's own docstring
says it exists to catch a documented `mamey <token>` invocation pointing at nothing (the F-01/
F-02 defect class). It used a plain `os.walk()` (no `onerror`) and a bare `except Exception:
continue` around each file read -- both silently drop coverage with no signal.

Reproduced live against the real pristine script: a genuine phantom command reference hidden
inside either an unreadable directory OR an unreadable individual file is completely invisible
to the scan, which then reports "OK" -- a false PASS on the exact defect class this gate exists
to catch. This gate IS effectively CI-wired (run via `pytest tests/ -q` in
`.github/workflows/ci.yml`, which picks up this file's own sibling test
`test_command_pointers_guard_v9_7_281.py`), so a coverage gap here sits in the CI path.

No permission-restricted path has been observed in this repo's real tree -- the pre-existing
`test_no_phantom_mamey_command_pointers` still passes unchanged under this fix, confirming the
real shipped tree scans clean either way. This closes a reproducible coverage gap, not a claim
that a real phantom command has ever silently slipped past it.

This script has no `--root` parameter (it always scans its own containing bundle, like
`tools/check_module_accretion.py`), so the repro/test necessarily operates on a scratch-copied
real bundle root rather than a synthetic tmp tree.

Permission-bit tests are skipped on platforms where chmod(0) doesn't actually restrict the
owner's own read access (notably: running as root).
"""
from __future__ import annotations

import os
import subprocess
import sys
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "check_command_pointers.py"

# Built by concatenation, not as one literal: the guard under test scans every .py file's own
# RAW TEXT for a backticked `mamey <token>` -- if this string appeared as one contiguous
# literal in this file's own source, this test file would itself trip the very gate it tests.
PHANTOM_CMD_LINE = "`" + "mamey totally-fake-phantom-command" + "`\n"


def _run() -> tuple[str, int]:
    proc = subprocess.run([sys.executable, str(SCRIPT)], cwd=str(ROOT),
                          capture_output=True, text=True, timeout=120)
    # v9.7.401 (per independent pool review): the unreadable-path refusal was moved to
    # stderr (print-ratchet convention). Combine both streams so "reported, not silent" is
    # checked regardless of which channel carries the message -- matches the widening already
    # applied to the sibling safe_walk-consolidation cards' own coverage tests this round.
    return proc.stdout + proc.stderr, proc.returncode


def test_script_present():
    assert SCRIPT.is_file(), "tools/check_command_pointers.py not found"


def test_clean_tree_still_passes():
    out, rc = _run()
    assert rc == 0, f"expected the real shipped tree to pass; got rc={rc}, out={out!r}"
    assert "OK: no phantom" in out


def test_real_phantom_command_still_caught(tmp_path):
    target = ROOT / "_bc2_401_test_probe_phantom.md"
    target.write_text(PHANTOM_CMD_LINE)
    try:
        out, rc = _run()
    finally:
        target.unlink()
    assert rc == 1
    assert "PHANTOM COMMAND POINTERS" in out
    assert "totally-fake-phantom-command" in out


@pytest.fixture
def locked_dir_with_phantom_command():
    locked = ROOT / "_bc2_401_locked_test_subdir"
    locked.mkdir()
    (locked / "phantom.md").write_text(PHANTOM_CMD_LINE)
    os.chmod(locked, 0o000)
    if os.access(locked, os.R_OK):
        os.chmod(locked, 0o755)
        (locked / "phantom.md").unlink()
        locked.rmdir()
        pytest.skip("chmod(0) does not restrict read access for this user (e.g. running as root)")
    try:
        yield locked
    finally:
        os.chmod(locked, 0o755)
        (locked / "phantom.md").unlink()
        locked.rmdir()


def test_unreadable_directory_is_reported_not_silently_passed(locked_dir_with_phantom_command):
    """The actual regression this fix closes: a real phantom command inside an unreadable
    directory must make the gate refuse (exit 1, naming the directory) rather than silently
    report OK."""
    out, rc = _run()
    assert rc == 1, f"expected the gate to refuse on an unscannable subtree; got rc={rc}, out={out!r}"
    assert "COULD NOT FULLY SCAN" in out
    assert "_bc2_401_locked_test_subdir" in out
    assert "OK: no phantom" not in out


@pytest.fixture
def locked_file_with_phantom_command():
    target = ROOT / "_bc2_401_locked_test_file.md"
    target.write_text(PHANTOM_CMD_LINE)
    os.chmod(target, 0o000)
    if os.access(target, os.R_OK):
        os.chmod(target, 0o644)
        target.unlink()
        pytest.skip("chmod(0) does not restrict read access for this user (e.g. running as root)")
    try:
        yield target
    finally:
        os.chmod(target, 0o644)
        target.unlink()


def test_unreadable_file_is_reported_not_silently_passed(locked_file_with_phantom_command):
    """The second regression this fix closes: an unreadable individual FILE (not just a
    directory) previously vanished into a bare `except Exception: continue`."""
    out, rc = _run()
    assert rc == 1, f"expected the gate to refuse on an unreadable file; got rc={rc}, out={out!r}"
    assert "COULD NOT FULLY SCAN" in out
    assert "_bc2_401_locked_test_file.md" in out
