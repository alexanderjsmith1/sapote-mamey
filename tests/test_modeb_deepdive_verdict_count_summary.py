"""tools/build_modeb_deepdive.py: the printed run summary must agree with what the document says.

408 found a --targets-only run with no modeb_verdicts.csv printing "0 CONFIRM, 0 DOWNGRADE, 0 DROP"
while every card rendered "Verdict — CONFIRM". 408 aligned the count with the CONFIRM default.
.458 removes that default: a target with no verdict row is NO_VERDICT, rendered as evidence only,
and counted as "without a verdict".
"""
from __future__ import annotations

import tools.build_modeb_deepdive as bmd


def test_missing_verdict_rows_count_as_no_verdict_like_the_renderer():
    targets = [("AS-XXX", "BGC001"), ("AS-XXX", "BGC002")]
    assert bmd._count_verdicts(targets, {}) == (0, 0, 0, 2)


def test_mixed_explicit_and_missing_verdicts_count_correctly():
    targets = [("AS-XXX", "BGC001"), ("AS-XXX", "BGC002"), ("AS-XXX", "BGC003")]
    vmap = {
        ("AS-XXX", "BGC001"): {"status": "DOWNGRADE"},
        ("AS-XXX", "BGC002"): {"status": "DROP"},
        # BGC003 has no row: no verdict, not CONFIRM.
    }
    assert bmd._count_verdicts(targets, vmap) == (0, 1, 1, 1)


def test_all_explicit_confirm_rows_still_count_once_each():
    targets = [("AS-XXX", "BGC001"), ("AS-XXX", "BGC002")]
    vmap = {
        ("AS-XXX", "BGC001"): {"status": "CONFIRM"},
        ("AS-XXX", "BGC002"): {"status": "CONFIRM"},
    }
    assert bmd._count_verdicts(targets, vmap) == (2, 0, 0, 0)
