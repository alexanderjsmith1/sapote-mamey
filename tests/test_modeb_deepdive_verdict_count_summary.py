"""tools/build_modeb_deepdive.py: the printed run summary ("N CONFIRM, N DOWNGRADE, N DROP") must
agree with what the document it just wrote actually says.

Found via a real deliverable run (BC2-408): a --targets-only invocation with no modeb_verdicts.csv
present (vmap == {}) produced a document where every single card rendered "Verdict — CONFIRM" (the
card body and section-header grouping in main() default a missing verdict row to 'CONFIRM' --
`st=(v or {}).get('status','CONFIRM')`), while the run summary line printed "0 CONFIRM, 0
DOWNGRADE, 0 DROP" -- the old counting expression, `vmap.get(t,{}).get('status')=='CONFIRM'`, had
no such default, so a missing vmap entry counted toward none of the three buckets. Fixed by
factoring the count into `_count_verdicts()`, using the same default as the renderer.
"""
from __future__ import annotations

import tools.build_modeb_deepdive as bmd


def test_missing_verdict_rows_default_to_confirm_like_the_renderer_does():
    # No modeb_verdicts.csv row for either target -- vmap is empty, exactly the --targets-only case.
    targets = [("AS-XXX", "BGC001"), ("AS-XXX", "BGC002")]
    vmap = {}
    nc, nd, nr = bmd._count_verdicts(targets, vmap)
    assert (nc, nd, nr) == (2, 0, 0), (
        "every card in this scenario renders 'Verdict — CONFIRM' (the renderer's own default); "
        "the summary count must match, not silently undercount to (0, 0, 0)"
    )


def test_mixed_explicit_and_missing_verdicts_count_correctly():
    targets = [("AS-XXX", "BGC001"), ("AS-XXX", "BGC002"), ("AS-XXX", "BGC003")]
    vmap = {
        ("AS-XXX", "BGC001"): {"status": "DOWNGRADE"},
        ("AS-XXX", "BGC002"): {"status": "DROP"},
        # BGC003 has no row -- must fall back to CONFIRM, same as before.
    }
    nc, nd, nr = bmd._count_verdicts(targets, vmap)
    assert (nc, nd, nr) == (1, 1, 1)


def test_all_explicit_confirm_rows_still_count_once_each():
    targets = [("AS-XXX", "BGC001"), ("AS-XXX", "BGC002")]
    vmap = {
        ("AS-XXX", "BGC001"): {"status": "CONFIRM"},
        ("AS-XXX", "BGC002"): {"status": "CONFIRM"},
    }
    nc, nd, nr = bmd._count_verdicts(targets, vmap)
    assert (nc, nd, nr) == (2, 0, 0)
