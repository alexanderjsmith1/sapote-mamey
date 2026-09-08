"""v9.7.86 C1: BUILD_STAMP patch= line is derived from the CHANGELOG head, not stale.

Guards the version-hygiene miss where BUILD_STAMP.patch= described pre-v9.7.85 content
and never mentioned the cut's headline change.
"""
from __future__ import annotations
import re, sys, pathlib
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from sync_version import changelog_headline   # noqa: E402


def _stamp_patch():
    txt = (ROOT / "BUILD_STAMP.txt").read_text(encoding="utf-8")
    m = re.search(r"(?m)^patch=(.*)$", txt)
    return m.group(1) if m else ""


def test_build_stamp_patch_matches_changelog_head():
    head = changelog_headline()
    assert head, "could not derive a headline from CHANGELOG.md"
    assert _stamp_patch() == head, "BUILD_STAMP patch= is out of sync with CHANGELOG head"


def test_build_stamp_patch_references_current_cut():
    # the patch line must be derived from (and therefore match) the current CHANGELOG head,
    # not a hardcoded per-cut keyword — version-agnostic so it doesn't rot each release.
    head = changelog_headline()
    assert _stamp_patch() == head and head, "patch line must equal the CHANGELOG-derived headline"


def test_changelog_headline_does_not_overrun_into_prior_entry():
    # the derived headline must come only from the top entry, not bleed into v9.7.85's P-7
    head = changelog_headline()
    assert "P-7" not in head, "headline bled into the prior CHANGELOG entry"
