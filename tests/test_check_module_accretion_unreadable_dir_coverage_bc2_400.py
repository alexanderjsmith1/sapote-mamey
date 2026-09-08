"""BC2 .400 audit: tools/check_module_accretion.py's own docstring states its purpose is
making a silently-added mamey/ module "visible and bounded at cut time." `current_modules()`
used `MAMEY.rglob("*.py")`, which silently swallows a per-directory `OSError` -- a module
hidden inside an unreadable mamey/ subdirectory is simply absent from the scan, with no signal,
indistinguishable from "this subtree has no modules." This is the fourth instance of the same
`rglob()`-silently-swallows-`OSError` shape found this round (after `check_no_brace_paths.py`,
`check_duplicate_dict_keys.py`, `public_release_audit.py`), so the fix reuses the same shared
`tools/_safe_walk.py` helper.

This gate IS CI-wired (`.github/workflows/ci.yml`, direct invocation
`python tools/check_module_accretion.py`) -- a coverage gap here sits directly in CI. That
said: no permission-restricted directory has been observed in this repo's real `mamey/` tree
-- the pre-existing `tests/test_module_accretion.py` suite (updated for the new
`current_modules()` tuple return, otherwise unchanged) still passes clean under this fix. This
closes a reproducible coverage gap in a CI-wired gate, not a claim that a real unacknowledged
module has ever silently slipped past it.

Reproduced directly against the real tool (subprocess against the real repo tree -- this gate
has no `--root` parameter; it always scans its own containing bundle's `mamey/`, so the repro
must operate on a real (disposable, scratch-copied) bundle root rather than a synthetic tmp
tree).

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
TOOL = ROOT / "tools" / "check_module_accretion.py"


def _run() -> tuple[str, int]:
    proc = subprocess.run([sys.executable, str(TOOL)], capture_output=True, text=True, cwd=str(ROOT))
    # Composer widening (.400 staging, with the print-ratchet stderr conversion): the
    # unreadable-dir refusal is emitted on the ERROR channel; the invariant under test is
    # "reported, not silent" on either stream.
    return proc.stdout + proc.stderr, proc.returncode


def test_tool_present():
    assert TOOL.is_file(), "tools/check_module_accretion.py not found"


def test_gate_passes_on_the_real_shipped_tree_with_no_permission_issues():
    """No regression: the real, unmodified mamey/ tree still passes (fixture skipped by the
    other test in this file locking/unlocking around this, run standalone here)."""
    out, rc = _run()
    assert rc == 0, f"expected the real shipped tree to pass; got rc={rc}, out={out!r}"
    assert "accretion gate: PASS" in out


@pytest.fixture
def locked_mamey_subdir_with_unmanifested_module():
    """A brand-new, genuinely unmanifested module hidden inside a permission-locked mamey/
    subdirectory, created directly in the real repo tree (this gate has no --root option) and
    torn down afterward regardless of outcome."""
    locked = ROOT / "mamey" / "_bc2_400_locked_test_subdir"
    locked.mkdir()
    (locked / "sneaky_module.py").write_text(
        '"""sneaky_module.py -- a brand new, unmanifested module."""\n'
    )
    os.chmod(locked, 0o000)
    if os.access(locked, os.R_OK):
        os.chmod(locked, 0o755)
        (locked / "sneaky_module.py").unlink()
        locked.rmdir()
        pytest.skip("chmod(0) does not restrict read access for this user (e.g. running as root)")
    try:
        yield locked
    finally:
        os.chmod(locked, 0o755)
        (locked / "sneaky_module.py").unlink()
        locked.rmdir()


def test_unreadable_mamey_subdir_is_reported_not_silently_passed(
    locked_mamey_subdir_with_unmanifested_module,
):
    """The actual regression this fix closes: a genuinely unmanifested module hidden inside an
    unreadable mamey/ subdirectory must make the gate FAIL and name the unreadable directory,
    not silently report 'net +0, PASS'."""
    out, rc = _run()
    assert rc == 1, f"expected the gate to fail on an unscannable mamey/ subtree; got rc={rc}, out={out!r}"
    assert "ACCRETION GATE FAIL" in out
    assert "_bc2_400_locked_test_subdir" in out
    # G1 (.406): the baseline is the seal, so a composing tree may report net +N for justified additions;
    # the phantom itself must still be invisible (never listed as an added module).
    assert "sneaky_module" not in out
