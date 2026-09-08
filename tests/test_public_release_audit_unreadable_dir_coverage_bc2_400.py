"""BC2 .400 audit: tools/public_release_audit.py's own docstring promises the whole-tree scan
flags "an unreadable tracked file (never silently skipped)" -- and it does, via the
`_UNREADABLE` sentinel in `_decode()`. But that per-FILE guarantee only fires for a file
`root.rglob("*")` actually yields; `rglob()` silently swallows a per-directory `OSError`, so a
whole directory it cannot descend into is never reached at all -- its contents (including a
genuine `BANNED_IDENTITY` leak) are simply absent from a scan that then reports itself clean.
This is the identical failure shape as `tools/check_no_brace_paths.py` and
`tools/check_duplicate_dict_keys.py` (fixed earlier this round), but here in the actual
leak-prevention audit that protects the "never leak a genuinely private strain ID" invariant --
the highest-stakes instance of this pattern found this round.

Reproduced directly against the real `audit()` function (imported, not reimplemented): a real
`BANNED_IDENTITY` hit inside a permission-locked subdirectory, alongside an otherwise-clean
minimal valid root, reports `audit(root) == []` (clean) pre-fix -- a false PASS on the exact
defect class this module exists to catch.

Also covers a genuine edge case caught while building this fix: `os.walk(..., onerror=...)`
calls `onerror` even for a top path that simply does NOT exist (`FileNotFoundError`) -- unlike
`rglob()`, which silently yields nothing for a missing path with no error at all. A naive
port would have turned "no mamey/data/ directory in this tree" (legitimate, common, not an
error) into a false "unreadable directory" finding on every tree lacking that optional
subdirectory. The fix explicitly special-cases a missing top path back to rglob's original
silent-empty behavior.

Permission-bit tests are skipped on platforms where chmod(0) doesn't actually restrict the
owner's own read access (notably: running as root).
"""
from __future__ import annotations

import os
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
import public_release_audit as audit_mod


def _minimal_root(tmp_path: pathlib.Path) -> pathlib.Path:
    (tmp_path / "mamey").mkdir()
    (tmp_path / "mamey" / "__init__.py").write_text('__version__ = "1.0.0"\n')
    (tmp_path / "BUILD_STAMP.txt").write_text("build=20260901v97400bc2\n")
    return tmp_path


@pytest.fixture
def locked_dir_with_real_leak(tmp_path):
    """A minimal valid root with one permission-locked subdirectory containing a genuine
    BANNED_IDENTITY hit."""
    root = _minimal_root(tmp_path)
    locked = root / "locked_sub"
    locked.mkdir()
    # a real banned-identity literal, picked from the module's own live BANNED_IDENTITY tuple
    # so this test tracks the real list rather than a synthetic stand-in.
    banned_literal = audit_mod.BANNED_IDENTITY[0]
    (locked / "leaked_notes.md").write_text(f"internal note referencing {banned_literal}\n")
    os.chmod(locked, 0o000)
    if os.access(locked, os.R_OK):
        os.chmod(locked, 0o755)
        pytest.skip("chmod(0) does not restrict read access for this user (e.g. running as root)")
    yield root, banned_literal
    os.chmod(locked, 0o755)  # restore so pytest/tmp_path cleanup can remove it


def test_unreadable_directory_with_a_real_leak_is_reported_not_silently_passed(locked_dir_with_real_leak):
    """The actual regression this fix closes: a real BANNED_IDENTITY leak inside an unreadable
    directory must surface as a finding, not silently report a clean scan."""
    root, banned_literal = locked_dir_with_real_leak
    hits = audit_mod.audit(root)
    assert hits, "expected the audit to report a finding for the unscannable directory"
    assert any("unreadable tracked directory" in h and "locked_sub" in h for h in hits)


def test_missing_optional_mamey_data_dir_is_not_a_false_positive(tmp_path):
    """The edge case caught while building this fix: os.walk's onerror fires even for a
    missing top path (unlike rglob, which is silent). A tree with no mamey/data/ at all
    (legitimate and common) must still scan clean -- not report a phantom 'unreadable
    directory' finding."""
    root = _minimal_root(tmp_path)
    assert not (root / "mamey" / "data").exists()
    assert audit_mod.audit(root) == []


def test_ordinary_readable_leak_still_fails_same_as_before(tmp_path):
    """No regression: a real, readable BANNED_IDENTITY leak still fails exactly as before --
    this fix only changes the silent-skip case, not the direct-detection case."""
    root = _minimal_root(tmp_path)
    banned_literal = audit_mod.BANNED_IDENTITY[0]
    (root / "docs").mkdir()
    (root / "docs" / "notes.md").write_text(f"references {banned_literal}\n")
    hits = audit_mod.audit(root)
    assert any(f"banned identity {banned_literal!r}" in h for h in hits)


def test_clean_tree_still_passes(tmp_path):
    """No regression: an ordinary, fully-readable, clean tree still scans clean."""
    root = _minimal_root(tmp_path)
    assert audit_mod.audit(root) == []


def test_unreadable_directory_inside_mamey_data_flags_the_cohort_id_scan_specifically(tmp_path):
    """The narrower mamey/data cohort-AS-id loop has its own independent unreadable-dir
    check (not just the whole-tree scan), so an unscannable directory there is named as
    incomplete for that specific scan too."""
    root = _minimal_root(tmp_path)
    data_dir = root / "mamey" / "data"
    data_dir.mkdir()
    locked = data_dir / "locked_sub"
    locked.mkdir()
    (locked / "roster.csv").write_text("AS-001,genus\n")
    os.chmod(locked, 0o000)
    if os.access(locked, os.R_OK):
        os.chmod(locked, 0o755)
        pytest.skip("chmod(0) does not restrict read access for this user (e.g. running as root)")
    try:
        hits = audit_mod.audit(root)
        assert any("cohort-id scan incomplete" in h for h in hits)
    finally:
        os.chmod(locked, 0o755)
