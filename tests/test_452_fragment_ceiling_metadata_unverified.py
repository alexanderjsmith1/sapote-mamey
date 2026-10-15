"""Unknown fragment metadata gives a typed UNKNOWN ceiling state, not a silent no-trip (P300-075)."""
import math

from mamey.fragment_ceiling import (CEILING_CLEAR, CEILING_TRIPPED, CEILING_UNKNOWN, DOWNGRADE_CEILING,
                                    apply_to_bgc, fragment_ceiling_state, fragment_claim_ceiling)


def test_invalid_length_on_a_named_backbone_fragment_is_unknown():
    for kb in (None, "", "bad", math.nan, math.inf, -math.inf, -5, 0, True):
        state, reason = fragment_ceiling_state("teicoplanin A2-1", "Edge", kb)
        assert state == CEILING_UNKNOWN, kb
        assert reason.startswith("METADATA_UNVERIFIED")
        trip, why = fragment_claim_ceiling("teicoplanin A2-1", "Edge", kb)
        assert trip is False and why == reason


def test_missing_or_unadmitted_edge_status_is_unknown():
    for edge in (None, "", "None", "contig_edge"):
        state, reason = fragment_ceiling_state("teicoplanin A2-1", edge, 20.0)
        assert state == CEILING_UNKNOWN and "edge status" in reason


def test_guard_not_applicable_or_interior_stays_clear():
    assert fragment_ceiling_state("coelichelin", "Edge", None) == (CEILING_CLEAR, None)
    assert fragment_ceiling_state("teicoplanin", "Interior", None) == (CEILING_CLEAR, None)
    assert fragment_ceiling_state("small-thing", "Edge", None, reference_size_kb=20.0) == (CEILING_CLEAR, None)


def test_measured_decisions_are_unchanged():
    assert fragment_ceiling_state("Teicoplanin A2-1", "Edge", 15.9)[0] == CEILING_TRIPPED
    assert fragment_ceiling_state("teicoplanin", "Full-contig", 44.9)[0] == CEILING_TRIPPED
    assert fragment_ceiling_state("teicoplanin", "Edge", 45.0) == (CEILING_CLEAR, None)
    assert fragment_ceiling_state("teicoplanin", "Edge", 70.0) == (CEILING_CLEAR, None)
    assert fragment_ceiling_state("novel-macrolactam", "Edge", 28.0, reference_size_kb=130.0)[0] == CEILING_TRIPPED
    assert fragment_claim_ceiling("Teicoplanin A2-1", "Edge", 15.9)[0] is True
    assert fragment_claim_ceiling("teicoplanin", "Edge", 70.0) == (False, None)


class _NoMetadata:
    """A record that names a backbone but carries no edge status and no coordinates."""
    closest_candidate_kcb_product = "Teicoplanin A2-1"
    product_claim_ceiling = "candidate product-level similarity, manual check required"
    needs_manual_kcb_check = "no"

    def __init__(self):
        self.notes = []


def test_apply_holds_unverified_metadata_without_downgrading():
    b = _NoMetadata()
    assert apply_to_bgc(b) is None
    assert b.product_claim_ceiling == "candidate product-level similarity, manual check required"
    assert b.product_claim_ceiling != DOWNGRADE_CEILING
    assert b.needs_manual_kcb_check == "yes"
    assert any(n.startswith("FRAGMENT_CEILING_METADATA_UNVERIFIED") for n in b.notes)


def test_apply_holds_a_non_finite_length():
    b = _NoMetadata()
    b.edge_status = "Edge"
    b.length_kb = math.nan
    assert apply_to_bgc(b) is None
    assert b.needs_manual_kcb_check == "yes" and "cluster length" in b.notes[0]
