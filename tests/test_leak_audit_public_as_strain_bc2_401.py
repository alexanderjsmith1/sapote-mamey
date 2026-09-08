"""BC2 .401 audit: mamey/dedup_and_guard.py's own docstring documents the v9.7.236 PI decision
-- AS-series strains are PUBLIC by default, implemented in `derive_release()`. But the sibling
`leak_audit()` in the same file was never updated for that decision: it flagged ANY cell
matching the private-identifier regexes in a PUBLIC row, including the row's OWN
`strain`/`BGC_ID` cells -- which, for a genuinely-PUBLIC AS-strain (the majority case in this
cohort), naturally repeat that strain's own AS-XXX identifier.

Reproduced directly against the real pristine function: a minimal, correctly-tagged PUBLIC
AS-strain row reported itself as its own leak.

Scope-honest: `leak_audit()` is not currently called anywhere in the live pipeline (confirmed
via a full-bundle grep for `leak_audit(` call sites -- only its own 2-case test file calls it).
It IS exported and tested, so this closes a real bug before something wires it up trusting its
name and existing tests, not a claim a real leak has ever silently passed through it live.

Fixed by exempting a cell that exactly equals the row's own declared strain, ONLY when that
strain is independently confirmed genuinely PUBLIC via `derive_release()` -- so a row whose own
strain is actually AJS-/PENDING- (mistagged PUBLIC) is still correctly flagged, and a different
strain's private-shaped identifier appearing anywhere else in the row is still caught.

All strain identifiers used here are drawn from tools/test_synthetic_ids.txt.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mamey.dedup_and_guard import leak_audit, derive_release  # noqa: E402


def test_legitimate_public_as_strain_row_is_not_its_own_leak():
    """The actual regression this fix closes."""
    assert derive_release("AS-74") == "PUBLIC", "test premise: AS-74 must derive PUBLIC"
    rows = [{"strain": "AS-74", "BGC_ID": "BGC001", "release": "PUBLIC", "notes": "clean row"}]
    assert leak_audit(rows) == [], "a legitimately PUBLIC AS-strain's own identifier is not a leak"


def test_a_different_strains_private_identifier_in_the_same_row_is_still_caught():
    """No under-catching introduced: a stray reference to a DIFFERENT, private-shaped
    identifier inside an otherwise-legitimate PUBLIC AS-strain row must still be flagged."""
    rows = [{"strain": "AS-74", "BGC_ID": "BGC001", "release": "PUBLIC",
            "notes": "see also AJS-001 for comparison"}]
    leaks = leak_audit(rows)
    assert len(leaks) == 1
    assert "AJS-001" in leaks[0]


def test_own_strain_mistagged_public_when_actually_private_is_still_caught():
    """The exemption must be scoped to genuinely-PUBLIC strains only: a row whose OWN strain
    is AJS-/PENDING- (never public) but was mistakenly release-tagged PUBLIC must still be
    flagged -- the exemption does not blanket-trust the row's `release` field."""
    rows = [{"strain": "AJS-001", "BGC_ID": "BGC002", "release": "PUBLIC"}]
    leaks = leak_audit(rows)
    assert len(leaks) == 1
    assert "AJS-001" in leaks[0]


def test_pending_own_strain_mistagged_public_is_still_caught():
    rows = [{"strain": "PENDING-002", "BGC_ID": "BGC003", "release": "PUBLIC"}]
    leaks = leak_audit(rows)
    assert len(leaks) == 1


def test_no_regression_pre_existing_pending_in_notes_still_caught():
    """Pinning the pre-existing test's own scenario directly, in case a future refactor of
    this file ever drops the shared `tests/test_patches.py` coverage."""
    rows = [{"strain": "S", "BGC_ID": "B1", "release": "PUBLIC", "notes": "derived from PENDING-XXX"}]
    assert len(leak_audit(rows)) == 1


def test_no_regression_private_tagged_row_stays_clean():
    rows = [{"strain": "PENDING-XXX", "BGC_ID": "B1", "release": "PRIVATE", "notes": "x"}]
    assert leak_audit(rows) == []


def test_multiple_as_strains_public_cohort_all_stay_clean():
    """A realistic multi-row shape: several genuinely-PUBLIC AS-strains, none flagged."""
    rows = [
        {"strain": s, "BGC_ID": f"BGC{i:03d}", "release": "PUBLIC"}
        for i, s in enumerate(("AS-001", "AS-74", "AS-200"), 1)
    ]
    assert leak_audit(rows) == []
