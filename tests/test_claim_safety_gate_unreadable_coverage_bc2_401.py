"""Regression test for `mamey/claim_safety_gate.py::candidate_text_files()` /
`run_claim_safety_gate()` (v9.7.401, BC2, `.401` round tick 10).

`candidate_text_files()` used bare `root.rglob("*")`, which silently swallows a per-directory
`OSError` -- an unreadable subdirectory's contents are simply absent from the scan, with no
signal. Reproduced live against the real pristine function: an overclaim-carrying report
("produces the antibiotic streptomycin") hidden inside a permission-locked subdirectory of a
package is completely invisible -- `run_claim_safety_gate()` returned zero candidate files and
reported `claim_safety_status: "NOT_REQUESTED"`, which reads even MORE benign than a false
"PASS" would. `claim_safety_status` is, per this module's own comment history, "the field
CLAUDE.md documents as the authoritative handoff to the judgment kernel" -- the highest-stakes
instance of this round's recurring `rglob()`-silent-coverage-gap pattern found so far.

`run_claim_safety_gate()` takes an arbitrary `package_dir` argument (unlike some sibling
`tools/` scripts, which always scan their own containing bundle), so this test operates entirely
on `tmp_path` fixtures rather than a scratch-copied real bundle root.

Permission-bit tests are skipped on platforms where chmod(0) doesn't actually restrict the
owner's own read access (notably: running as root).
"""
from __future__ import annotations

import os

import pytest

from mamey.claim_safety_gate import run_claim_safety_gate

_OVERCLAIM_TEXT = ("The BGC001 cluster produces the antibiotic streptomycin under standard "
                   "fermentation conditions.\n")
_SAFE_TEXT = ("The BGC001 cluster shows capacity consistent with a streptomycin-family "
              "compound.\n")


def test_clean_empty_package_reports_not_requested(tmp_path):
    result = run_claim_safety_gate(tmp_path)
    assert result["claim_safety_status"] == "NOT_REQUESTED"
    assert result["files_checked"] == []
    assert result["finding_count"] == 0
    assert result["findings"] == []


def test_missing_package_dir_reports_not_requested(tmp_path):
    missing = tmp_path / "does_not_exist"
    result = run_claim_safety_gate(missing)
    assert result["claim_safety_status"] == "NOT_REQUESTED"
    assert result["files_checked"] == []
    assert result["finding_count"] == 0


def test_readable_overclaim_still_caught(tmp_path):
    (tmp_path / "AS-74_report.md").write_text(_OVERCLAIM_TEXT)
    result = run_claim_safety_gate(tmp_path)
    assert result["claim_safety_status"] == "FAIL"
    assert result["files_checked"] == ["AS-74_report.md"]
    assert result["finding_count"] == 1
    assert "streptomycin" in result["findings"][0]["finding"]


def test_readable_safe_text_still_passes(tmp_path):
    (tmp_path / "AS-74_report.md").write_text(_SAFE_TEXT)
    result = run_claim_safety_gate(tmp_path)
    assert result["claim_safety_status"] == "PASS"
    assert result["files_checked"] == ["AS-74_report.md"]
    assert result["finding_count"] == 0


@pytest.fixture
def locked_subdir_with_overclaim(tmp_path):
    locked = tmp_path / "locked_sub"
    locked.mkdir()
    (locked / "AS-74_report.md").write_text(_OVERCLAIM_TEXT)
    os.chmod(locked, 0o000)
    if os.access(locked, os.R_OK):
        os.chmod(locked, 0o755)
        pytest.skip("chmod(0) does not restrict read access for this user (e.g. running as root)")
    try:
        yield tmp_path, locked
    finally:
        os.chmod(locked, 0o755)


def test_unreadable_subdir_is_reported_not_silently_not_requested(locked_subdir_with_overclaim):
    """The actual regression this fix closes: an overclaim hidden inside an unreadable
    subdirectory must make the gate report FAIL (naming the unreadable path) rather than the
    misleadingly benign NOT_REQUESTED with zero files checked and zero findings."""
    package_dir, locked = locked_subdir_with_overclaim
    result = run_claim_safety_gate(package_dir)
    assert result["claim_safety_status"] == "FAIL", result
    assert result["files_checked"] == []
    assert result["finding_count"] == 1
    assert result["findings"][0]["path"] == str(locked)
    assert "unreadable" in result["findings"][0]["error"]
    assert "incomplete" in result["findings"][0]["error"]


def test_unreadable_subdir_alongside_readable_clean_file_still_fails(locked_subdir_with_overclaim):
    """A genuinely clean, readable sibling file must NOT mask the unreadable-subtree finding --
    the scan is incomplete regardless of what the readable portion looked like."""
    package_dir, locked = locked_subdir_with_overclaim
    (package_dir / "AS-74_report.md").write_text(_SAFE_TEXT)
    result = run_claim_safety_gate(package_dir)
    assert result["claim_safety_status"] == "FAIL", result
    assert result["files_checked"] == ["AS-74_report.md"]
    assert result["finding_count"] == 1
    assert result["findings"][0]["path"] == str(locked)
