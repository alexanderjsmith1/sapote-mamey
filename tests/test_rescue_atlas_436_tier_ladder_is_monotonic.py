"""Tier A must be at least as strict as Tier B on every gate they share.

Finding and fix are Goldenrod's
(`GOLDENROD_436_rggmci_tier_a_missing_alignment_coverage_gate.md`): Tier A omits
the `median_alignment_coverage >= 55` floor that Tier B enforces.

This file adds the regression test that card does not carry, and pins the
property rather than a single example.  The property is *monotonicity*: the tier
names are an ordered ladder (A is documented as the strictest), and
`write_atlas` builds its human-facing strict subset from `TIERS[:2]`.  A row that
clears A must therefore also clear B.  Today it need not, which makes the ladder
incoherent independently of where the floor is set.

That distinction matters for the ruling: "how strict should A be?" is a judgment
call, but "A must not be looser than B" is structural.  >= 55 is the minimum
coherent value, not a preference.
"""
from __future__ import annotations

import pytest

from mamey.rggmci_rescue_atlas import TIERS, evidence_tier


def strong_row(**over):
    """A row clearing every Tier A gate; override one field per test."""
    row = dict(
        rggmci_confidence="HIGH_RG_GMCI_RESCUE",
        unique_subjects_a=5,
        unique_subjects_b=5,
        shared_subjects=0,
        combined_unique_subjects=10,
        reference_protein_coverage=0.40,
        max_reference_rank=1,
        median_identity=40,
        reference_tiling_topology="DISJOINT_ADJACENT_SEGMENTS",
        boundary_a="Edge",
        boundary_b="Interior",
        subject_tiling_verdict="COMPLEMENTARY_SPLIT",
        subject_disjointness=1.0,
        generic_modular_caution=False,
        median_alignment_coverage=90.0,
    )
    row.update(over)
    return row


def clears_tier_b_numeric_gates(row):
    """Tier B's own numeric gates, transcribed from evidence_tier."""
    return (
        row["rggmci_confidence"] == "HIGH_RG_GMCI_RESCUE"
        and min(row["unique_subjects_a"], row["unique_subjects_b"]) >= 2
        and row["shared_subjects"] == 0
        and row["combined_unique_subjects"] >= 6
        and row["reference_protein_coverage"] >= 0.20
        and row["subject_disjointness"] >= 0.85
        and row["median_identity"] >= 30
        and row["median_alignment_coverage"] >= 55
        and row["max_reference_rank"] <= 5
    )


def test_baseline_strong_row_is_tier_a():
    assert evidence_tier(strong_row())[0] == TIERS[0]


@pytest.mark.parametrize("coverage", [0.0, 1.0, 10.0, 25.0, 54.9])
def test_tier_a_requires_the_alignment_coverage_floor(coverage):
    """A row below Tier B's floor must not be labelled control-grade."""
    row = strong_row(median_alignment_coverage=coverage)
    tier, _ = evidence_tier(row)
    assert tier != TIERS[0], (
        f"median_alignment_coverage={coverage}% reached {TIERS[0]} -- the tool's "
        "own control-grade label -- on alignments barely overlapping their subjects"
    )


@pytest.mark.parametrize("coverage", [0.0, 1.0, 10.0, 25.0, 54.9, 55.0, 90.0, 100.0])
def test_tier_ladder_is_monotonic_in_alignment_coverage(coverage):
    """The structural property: anything clearing A must also clear B."""
    row = strong_row(median_alignment_coverage=coverage)
    if evidence_tier(row)[0] == TIERS[0]:
        assert clears_tier_b_numeric_gates(row), (
            f"coverage={coverage}%: row is Tier A but fails Tier B's gates -- "
            "the tier ladder is not ordered"
        )


def test_subject_disjointness_omission_in_tier_a_is_harmless():
    """Recorded so a later pass does not 'fix' a non-defect.

    Tier A omits Tier B's `subject_disjointness >= .85`, but `build_atlas`
    computes disjointness as `1 - overlap/union` and Tier A already requires
    `shared_subjects == 0`, which forces disjointness to 1.0.  The omission is
    unreachable, not a second hole.
    """
    row = strong_row(shared_subjects=0, subject_disjointness=1.0)
    assert evidence_tier(row)[0] == TIERS[0]
    # A row with shared subjects cannot reach Tier A regardless of disjointness.
    assert evidence_tier(strong_row(shared_subjects=1))[0] != TIERS[0]
