"""A lead card says "No KCB anchor was detected" only when KnownClusterBlast reported no hit.

A blank KCB top hit with kcb_evidence_state UNKNOWN_KCB (or no state) means the comparison is
not in the package. The card used to print the no-hit sentence for every blank.
"""
from mamey.chatgpt_commands import _KCB_NOT_IN_PACKAGE, _kcb_absent_text


def test_reported_no_hit_keeps_the_no_anchor_sentence():
    value, sentence = _kcb_absent_text("KNOWNCLUSTERBLAST_NO_HITS_UNVALIDATED")
    assert value == "No KCB hit reported"
    assert sentence.startswith("No KCB anchor was detected for this BGC.")
    assert "not proof of a new compound" in sentence


def test_unknown_or_missing_state_is_not_a_no_hit():
    for state in ("UNKNOWN_KCB", "", None, "something_else"):
        value, sentence = _kcb_absent_text(state)
        assert (value, sentence) == _KCB_NOT_IN_PACKAGE, state
        assert "No KCB anchor was detected" not in sentence
        assert "not a no-hit result" in sentence


def test_clusterblast_fallback_says_kcb_is_not_known():
    value, sentence = _kcb_absent_text("clusterblast_fallback_observed")
    assert value == "No KCB result (ClusterBlast only)"
    assert "No KCB anchor was detected" not in sentence
