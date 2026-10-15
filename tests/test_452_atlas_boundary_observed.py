"""Strict atlas tiers need an observed contig end: a blank or unknown boundary is unmeasured, not boundary support.

Before, `boundary != "Interior"` let a missing locus boundary (read as "") pass the strict A/B boundary gate and earn
the boundary score points.
"""
import pytest

from mamey import rggmci_rescue_atlas as atlas
from mamey.rggmci_rescue_atlas import TIERS, build_atlas, evidence_score, evidence_tier

A = "SYNTH-01 / contig_alpha_full / region001 / BGC001"
B = "SYNTH-01 / contig_beta_full / region002 / BGC002"


def _row(boundary_a, boundary_b, verdict="COMPLEMENTARY_SPLIT"):
    return dict(rggmci_confidence="HIGH_RG_GMCI_RESCUE", unique_subjects_a=5, unique_subjects_b=5, shared_subjects=0,
                combined_unique_subjects=10, reference_protein_coverage=0.40, max_reference_rank=1, median_identity=40,
                reference_tiling_topology="DISJOINT_ADJACENT_SEGMENTS", boundary_a=boundary_a, boundary_b=boundary_b,
                subject_tiling_verdict=verdict, subject_disjointness=1.0, generic_modular_caution=False,
                median_alignment_coverage=90.0)


@pytest.mark.parametrize("a,b", [("", ""), ("", "Interior"), ("unknown", "Interior"), ("edge", "INTERIOR"),
                                 ("Interior", "Interior")])
def test_no_observed_end_is_not_boundary_support(a, b):
    assert evidence_tier(_row(a, b))[0] not in TIERS[:2]
    assert evidence_score(_row(a, b)) == evidence_score(_row("Interior", "Interior"))


@pytest.mark.parametrize("a,b", [("Edge", "Interior"), ("Interior", "Full-contig"), ("", "Edge")])
def test_an_observed_end_still_supports_the_strict_tier(a, b):
    assert evidence_tier(_row(a, b))[0] == TIERS[0]
    assert evidence_score(_row(a, b)) == evidence_score(_row("Interior", "Interior")) + 2


def test_terminus_split_still_supports_without_an_observed_end():
    assert evidence_tier(_row("", "", verdict="TERMINUS_TRUNCATION_SPLIT"))[0] == TIERS[0]


def test_boundary_state_keeps_unmeasured_apart_from_interior():
    assert atlas.boundary_evidence_state(_row("Edge", "")) == "OBSERVED_CONTIG_END"
    assert atlas.boundary_evidence_state(_row("Interior", "Interior")) == "BOTH_INTERIOR"
    assert atlas.boundary_evidence_state(_row("", "Interior")) == "BOUNDARY_UNMEASURED"


def test_atlas_rows_carry_the_boundary_state():
    pair = [{"strain": "SYNTH-01", "identity_a": A, "identity_b": B, "rggmci_confidence": "HIGH_RG_GMCI_RESCUE",
             "subject_tiling_verdict": "COMPLEMENTARY_SPLIT"}]
    loci = [{"complete_identity": A}, {"complete_identity": B, "boundary": "Interior"}]
    ranked, _ = build_atlas(pair, loci, [], {})
    assert ranked[0]["boundary_a"] == "" and ranked[0]["boundary_evidence_state"] == "BOUNDARY_UNMEASURED"
