"""Synteny concordance must span the full [0,1] score range.

`order_concordance` reports orientation-aware rank agreement as
`max(concordant, discordant) / total`.  That expression is bounded below by
0.5, because for any ordering either the concordant or the discordant count is
at least half the pairs.  The ranker then spends that value directly as a
0-10 point score component, so a locus whose matched genes sit in the worst
possible order still collects half the available synteny points, while a locus
with too few pairs to assess collects none.

Adding a third, randomly ordered match therefore *raises* the composite score.
These tests pin the corrected scale: 0 means "no better than arbitrary order",
1 means "perfectly collinear (either orientation)".
"""
from __future__ import annotations

import itertools
import sys

import pytest
from pathlib import Path

BUNDLE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BUNDLE))
sys.path.insert(0, str(BUNDLE / "tools"))

from tools.definitive_bgc_ranker import order_concordance, evidence_tier  # noqa: E402


def pairs(reference_order):
    return [
        {"query_order": i, "reference_order": o}
        for i, o in enumerate(reference_order)
    ]


def test_fewer_than_three_pairs_is_unassessable():
    assert order_concordance(pairs([1, 2])) is None


def test_collinear_forward_and_reverse_both_score_one():
    assert order_concordance(pairs([1, 2, 3, 4])) == 1.0
    assert order_concordance(pairs([4, 3, 2, 1])) == 1.0


def test_worst_possible_order_scores_the_combinatorial_floor_not_half():
    """The load-bearing assertion: no ordering may earn free points.

    With ``t = C(n,2)`` pairwise comparisons, ``max(concordant, discordant)``
    cannot fall below ``ceil(t/2)``, so the irreducible floor on the rescaled
    value is ``(t % 2) / t`` -- exactly 0 whenever ``t`` is even, and a
    vanishing ``1/t`` when ``t`` is odd.  Before the rescale the floor was a
    flat 0.5 for every ``n``, i.e. five free points out of ten.
    """
    for n in (3, 4, 5, 6, 7, 8):
        total = n * (n - 1) // 2
        expected_floor = (total % 2) / total
        worst = min(
            order_concordance(pairs(list(p)))
            for p in itertools.permutations(range(1, n + 1))
        )
        assert worst == pytest.approx(expected_floor, abs=1e-9), (
            f"n={n}: worst achievable concordance is {worst!r}, expected the "
            f"combinatorial floor {expected_floor!r}; a maximally scrambled "
            f"locus is collecting {10 * worst:.2f}/10 synteny points"
        )
        assert worst < 0.35, f"n={n}: floor {worst!r} is still materially above zero"


def test_no_ordering_ever_scores_below_zero():
    for n in (3, 5, 6):
        for p in itertools.permutations(range(1, n + 1)):
            assert 0.0 <= order_concordance(pairs(list(p))) <= 1.0


def test_three_scrambled_pairs_do_not_beat_two_clean_pairs():
    """The discontinuity this defect creates, stated as a score comparison."""
    two_clean = order_concordance(pairs([1, 2]))
    three_scrambled = order_concordance(pairs([2, 1, 3]))
    assert two_clean is None
    two_points = 10 * 0  # the ranker spends None as zero
    three_points = 10 * three_scrambled
    # n=3 leaves an irreducible 1/3 floor (three comparisons cannot tie), so the
    # residual credit is bounded at ~3.34 points rather than the pre-fix 6.67.
    assert three_points <= two_points + 3.34, (
        f"adding one badly-ordered match gained {three_points - two_points:.2f} "
        "points of synteny credit"
    )


def _metrics(synteny, **over):
    base = {
        "matched_gene_pairs": 5,
        "reciprocal_coverage_f1": 0.70,
        "reference_core_completeness": 0.80,
        "median_effective_similarity": 70,
        "orientation_aware_order_concordance": synteny,
        "boundary": "Interior",
        "clear_specific_gene_count": 2,
        "rggmci_genuine_high": False,
    }
    base.update(over)
    return base


def test_tier_gate_behaviour_is_preserved_across_the_rescale():
    """A rescale must not silently re-tier loci: check both ends of the gate."""
    # Perfectly collinear still reaches tier A.
    assert evidence_tier(_metrics(1.0)).startswith("A_")
    # Unassessable (None) still passes the synteny gate, as before.
    assert evidence_tier(_metrics(None)).startswith("A_")
    # Arbitrary order must NOT clear the gate.
    assert not evidence_tier(_metrics(0.0)).startswith("A_")
