"""TESTS — CLAUDE_409_rglob_seal_coverage (silent recursive-glob coverage gaps).

Fail-before / pass-after coverage for the top-3 ranked ``rglob`` gaps where an
unreadable/unlistable subtree is silently swallowed, so the subtree vanishes from a scan
with NO signal:

  1. packaging.py  _package_files_fail_closed  — the seal's single enumeration chokepoint
     feeding the checksum writer AND validate.py's SEAL-03 untracked scan.
  2. validate.py   validate_citation_compact_outputs — optional-by-presence; a truncated
     scan would report NOT_REQUESTED for a package whose compact artifacts live under the
     unreadable subtree.
  3. mode_b/availability.py  discover_evidence — an unreadable evidence subtree would let a
     Mode B card assert the ABSENCE of evidence that in fact exists.

Run with this lane APPLIED on top of pristine v9.7.408: `pytest TESTS_409_rglob_seal_coverage.py`.

The `test_*_fail_before_*` cases pin the ROOT CAUSE that is invariant of the patch: raw
``pathlib.Path.rglob`` swallows a per-directory ``PermissionError`` and silently under-returns.
The `test_*_pass_after_*` cases assert the patched functions instead fail closed (raise, or
return an explicit FAIL) on the very same unreadable subtree. All checks operate at the FUNCTION
level on synthetic trees under tmp_path — no real bundle, package, or gold run is touched.
"""
import os
import stat
from pathlib import Path

import pytest

from mamey import packaging as pk
from mamey import validate as vd
from mamey.mode_b import availability as av


# ── fixture: a tree with one readable file and one UNREADABLE subtree ─────────
def _make_tree_with_unreadable_subtree(base: Path):
    """Build:  base/readable.txt  and  base/locked/hidden.txt  where base/locked is chmod 000.

    Returns (base, hidden_rel). Registers no cleanup here — caller must restore perms via the
    returned restorer so tmp_path teardown can delete the tree.
    """
    (base / "readable.txt").write_text("visible\n", encoding="utf-8")
    locked = base / "locked"
    locked.mkdir()
    hidden = locked / "hidden.txt"
    hidden.write_text("must-not-vanish\n", encoding="utf-8")
    os.chmod(locked, 0o000)

    def _restore():
        os.chmod(locked, stat.S_IRWXU)

    return base, "locked/hidden.txt", _restore


def _unreadable_or_skip(base: Path):
    """Set up the unreadable subtree, skipping if this environment cannot enforce it
    (e.g. running as root, or a filesystem that ignores dir-mode)."""
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        pytest.skip("running as root: directory-mode 000 does not block enumeration")
    base, hidden_rel, restore = _make_tree_with_unreadable_subtree(base)
    # Verify the OS actually blocks listing; otherwise the whole premise is moot here.
    try:
        os.listdir(base / "locked")
        restore()
        pytest.skip("filesystem does not enforce directory-mode 000")
    except PermissionError:
        pass
    return base, hidden_rel, restore


# ── FAIL-BEFORE: the invariant root cause — Path.rglob swallows the error ─────
def test_fail_before_rglob_silently_skips_unreadable_subtree(tmp_path):
    """The gap this lane closes: raw ``Path.rglob('*')`` returns the readable file and
    SILENTLY omits the file under the unreadable subtree — no exception, no signal."""
    base, hidden_rel, restore = _unreadable_or_skip(tmp_path)
    try:
        found = {p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file()}
        assert "readable.txt" in found
        # The whole bug in one line: the hidden file is neither raised on nor returned.
        assert hidden_rel not in found
    finally:
        restore()


# ── FIX 1 — packaging._package_files_fail_closed ─────────────────────────────
def test_packaging_regression_healthy_tree(tmp_path):
    """REGRESSION: on a healthy tree, only regular files are returned, deterministically sorted."""
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.txt").write_text("b", encoding="utf-8")
    files = pk._package_files_fail_closed(tmp_path)
    rels = [p.relative_to(tmp_path).as_posix() for p in files]
    assert rels == ["a.txt", "sub/b.txt"]  # dirs excluded, sorted


def test_packaging_pass_after_raises_on_unreadable_subtree(tmp_path):
    """PASS-AFTER: an unreadable subtree makes the seal enumeration fail closed (raise) rather
    than silently under-return an incomplete, mis-sealed file list."""
    base, _hidden, restore = _unreadable_or_skip(tmp_path)
    try:
        with pytest.raises(OSError):
            pk._package_files_fail_closed(base)
    finally:
        restore()


def test_packaging_regression_symlink_still_rejected(tmp_path):
    """REGRESSION: the pre-existing symlink containment guard is preserved."""
    (tmp_path / "real.txt").write_text("r", encoding="utf-8")
    try:
        os.symlink(tmp_path / "real.txt", tmp_path / "link.txt")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported here")
    with pytest.raises(pk.PackageContainmentError):
        pk._package_files_fail_closed(tmp_path)


# ── FIX 2 — validate.validate_citation_compact_outputs ───────────────────────
def test_validate_regression_not_requested(tmp_path):
    """REGRESSION: a healthy package with NO citation-compact artifacts is NOT_REQUESTED."""
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    res = vd.validate_citation_compact_outputs(tmp_path)
    assert res["status"] == "NOT_REQUESTED"


def test_validate_pass_after_fails_closed_on_unreadable_subtree(tmp_path):
    """PASS-AFTER: with citation-compact artifacts hidden under an unreadable subtree, the gate
    returns an explicit FAIL — NEVER the silent NOT_REQUESTED that a truncated rglob would give
    (asserting absence from an incomplete scan)."""
    # The only citation-compact marker lives inside the subtree that cannot be read.
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    cc = tmp_path / "citation_compact"
    cc.mkdir()
    (cc / "AS-1_citation_compact.md").write_text("# compact\n", encoding="utf-8")
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        pytest.skip("running as root: directory-mode 000 does not block enumeration")
    os.chmod(cc, 0o000)
    try:
        os.listdir(cc)
        pytest.skip("filesystem does not enforce directory-mode 000")
    except PermissionError:
        pass
    try:
        res = vd.validate_citation_compact_outputs(tmp_path)
        assert res["status"] == "FAIL"
        assert res["status"] != "NOT_REQUESTED"
        assert res.get("errors")
    finally:
        os.chmod(cc, stat.S_IRWXU)


# ── FIX 3 — mode_b.availability.discover_evidence ────────────────────────────
def test_availability_pass_after_raises_on_unreadable_subtree(tmp_path):
    """PASS-AFTER: an unreadable evidence subtree raises rather than letting discover_evidence
    silently under-return (which would let a card assert absence of evidence that exists)."""
    base, _hidden, restore = _unreadable_or_skip(tmp_path)
    contract = {"streams": []}
    try:
        with pytest.raises(OSError):
            av.discover_evidence([], contract, [("src", base)], inspect_tables=False)
    finally:
        restore()


def test_availability_regression_missing_root_still_raises(tmp_path):
    """REGRESSION: the pre-existing missing-root contract (FileNotFoundError) is preserved."""
    with pytest.raises(FileNotFoundError):
        av.discover_evidence([], {"streams": []}, [("src", tmp_path / "does_not_exist")], inspect_tables=False)


def test_availability_regression_healthy_tree_scans(tmp_path):
    """REGRESSION: a healthy evidence tree is scanned without error (returns a list)."""
    (tmp_path / "AS-1_evidence.txt").write_text("evidence\n", encoding="utf-8")
    out = av.discover_evidence([], {"streams": []}, [("src", tmp_path)], inspect_tables=False)
    assert isinstance(out, list)
