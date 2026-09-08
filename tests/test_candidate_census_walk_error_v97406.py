"""Independent finding by Black Cherry-3 (read-only audit of the sealed .405 CODE tier), landed on the
CODEX-406 typed-receipt shape (coverage_complete + traversal_errors[{path,error_type,message}],
status INCOMPLETE). v9.7.406 candidate — regression coverage for the candidate_census.py fail-closed fix.

Reproduces the defect found auditing v9.7.405: `os.walk` without an `onerror` callback silently
skips a subdirectory it cannot open, so debris hiding inside an unreadable subtree was never
counted and the tool still reported `status: CLEAN`. These tests pin the fixed behaviour:
`traversal_errors` is populated and `status` becomes `INCOMPLETE` (not CLEAN, not silently absorbed
into DEBRIS_FOUND) whenever any subtree could not be walked, and the CLI exits non-zero for it.

Uses os.chmod(0o000) to build the fixture, so this file is skipped when running as root (uid 0
ignores POSIX permission bits, e.g. some CI containers) since the repro would not reproduce.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("candidate_census",
                                              ROOT / "tools" / "candidate_census.py")
cc = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(cc)

pytestmark = pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="root ignores POSIX permission bits; the unreadable-subtree fixture cannot reproduce",
)


def _touch(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture
def locked_tree(tmp_path):
    """A tree with one readable file and one *unreadable* subtree that itself contains debris."""
    _touch(tmp_path / "a.py")
    locked = tmp_path / "locked_sub"
    _touch(locked / ".DS_Store")
    _touch(locked / "__pycache__" / "c.cpython-313.pyc")
    os.chmod(locked, 0o000)
    try:
        yield tmp_path, locked
    finally:
        os.chmod(locked, 0o755)  # restore so tmp_path cleanup can remove it


def test_census_does_not_report_clean_when_a_subtree_is_unreadable(locked_tree):
    tmp_path, locked = locked_tree
    report = cc.census(str(tmp_path))
    assert report["status"] == "INCOMPLETE", (
        "an unreadable subtree makes the count provably incomplete -- CLEAN must never be "
        "reported when debris could be hiding in a part of the tree the walk never saw"
    )
    assert report["traversal_errors"], "the permission error must be surfaced, not swallowed"
    assert any(str(locked) in entry["path"] for entry in report["traversal_errors"])


def test_census_walk_error_wins_over_debris_found(tmp_path):
    """Even when *visible* debris is also present, an unreadable subtree still forces
    INCOMPLETE -- the count is incomplete either way, so DEBRIS_FOUND (implying "that's the
    complete list") would still be misleading."""
    _touch(tmp_path / ".DS_Store")
    locked = tmp_path / "locked_sub"
    _touch(locked / "x.py")
    os.chmod(locked, 0o000)
    try:
        report = cc.census(str(tmp_path))
    finally:
        os.chmod(locked, 0o755)
    assert report["debris_total"] == 1
    assert report["status"] == "INCOMPLETE"


def test_cli_exits_nonzero_on_walk_error_even_with_zero_visible_debris(locked_tree, capsys):
    tmp_path, _locked = locked_tree
    rc = cc.main([str(tmp_path)])
    out = capsys.readouterr().out
    receipt = json.loads(out)
    assert receipt["debris_total"] == 0, "no debris visible from the readable part of the tree"
    assert receipt["status"] == "INCOMPLETE"
    assert rc == 1, "an incomplete census must fail closed (non-zero), never exit 0"


def test_clean_tree_still_reports_clean_with_empty_traversal_errors(tmp_path):
    """No-regression check: a fully readable, debris-free tree is unaffected by the fix."""
    _touch(tmp_path / "a.py")
    report = cc.census(str(tmp_path))
    assert report["traversal_errors"] == []
    assert report["status"] == "CLEAN"
