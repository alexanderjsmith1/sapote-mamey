"""BC2 .400 audit: tools/check_no_brace_paths.py's own docstring states its entire purpose is
to make the brace-path mkdir mistake "fail the build instead of shipping." The implementation
used `ROOT.rglob("*")`, which silently swallows a per-directory OSError -- an unreadable
directory (permission-restricted; a git-object-style directory mode; any tree assembled from a
source that didn't preserve normal read permissions) is skipped with no signal, and its
contents are simply absent from the scan. Downstream this is indistinguishable from "this
directory legitimately contains no brace-named paths": the gate prints "brace-path check OK"
and exits 0 even when a real, unexpanded-mkdir-style brace directory sits just inside a
subtree it could not read.

Reproduced directly against the real tool (subprocess, not a reimplementation): a tree with one
permission-locked subdirectory containing a brace-named file passes clean (exit 0) on the
pristine script; the same tree correctly fails (exit 1, naming the unreadable directory as
UNVERIFIED) on the fixed script, which replaces the plain rglob with `os.walk(...,
onerror=...)` so a scan failure is observable and turned into a loud finding instead of a
silent pass -- matching this gate's own stated "fail the build" philosophy. This is scope-
appropriate hardening of a validation gate's own coverage guarantee (per this lane's own remit:
"coverage boundaries that go silent instead of flagging"), not a claim that a permission-locked
directory has been observed in a real shipped bundle -- it has not.

Permission-bit tests are skipped on platforms where chmod(0) doesn't actually restrict the
owner's own read access (notably: running as root).
"""
from __future__ import annotations

import os
import subprocess
import sys
import pathlib

import pytest

TOOL = pathlib.Path(__file__).resolve().parents[1] / "tools" / "check_no_brace_paths.py"


def _run(root: pathlib.Path) -> tuple[str, int]:
    proc = subprocess.run([sys.executable, str(TOOL), str(root)],
                           capture_output=True, text=True)
    # Composer widening (.400 staging, with the print-ratchet stderr conversion): the
    # unreadable-dir refusal is emitted on the ERROR channel; the invariant under test is
    # "reported, not silent" on either stream.
    return proc.stdout + proc.stderr, proc.returncode


@pytest.fixture
def locked_dir_with_brace_file(tmp_path):
    """A subdirectory made unreadable, containing a brace-named file inside it."""
    sub = tmp_path / "locked_sub"
    sub.mkdir()
    (sub / "{brace}.txt").write_text("x")
    os.chmod(sub, 0o000)
    if os.access(sub, os.R_OK):
        os.chmod(sub, 0o755)
        pytest.skip("chmod(0) does not restrict read access for this user (e.g. running as root)")
    yield tmp_path
    os.chmod(sub, 0o755)  # restore so pytest/tmp_path cleanup can remove it


def test_tool_present():
    assert TOOL.is_file(), "tools/check_no_brace_paths.py not found"


def test_unreadable_directory_is_reported_not_silently_passed(locked_dir_with_brace_file):
    """The actual regression this fix closes: a brace path inside an unreadable directory must
    make the gate FAIL and name the unreadable directory, not silently print 'OK'."""
    out, rc = _run(locked_dir_with_brace_file)
    assert rc == 1, f"expected the gate to fail on an unscannable subtree; got rc={rc}, out={out!r}"
    assert "COULD NOT FULLY SCAN" in out
    assert "locked_sub" in out
    assert "brace-path check OK" not in out


def test_clean_tree_with_no_permission_issues_still_passes(tmp_path):
    """No regression: an ordinary, fully-readable tree with no brace paths still passes."""
    nested = tmp_path / "some" / "nested" / "dir"
    nested.mkdir(parents=True)
    (nested / "normal_file.txt").write_text("x")
    out, rc = _run(tmp_path)
    assert rc == 0
    assert "brace-path check OK" in out


def test_readable_brace_path_still_fails_same_as_before(tmp_path):
    """No regression: a real, readable brace-named path still fails the gate exactly as
    before -- this fix only changes the silent-skip case, not the direct-detection case."""
    (tmp_path / "{oops}.txt").write_text("x")
    out, rc = _run(tmp_path)
    assert rc == 1
    assert "BRACE-PATH CHECK FAILED" in out
    assert "{oops}.txt" in out
