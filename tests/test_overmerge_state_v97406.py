"""E5: flag-only antiSMASH cand_cluster structure classification."""
from mamey.models import BGCRecord
from mamey.parsers import cand_cluster_kinds, overmerge_state
from mamey.scoring import triage_bgcs


class _Feature:
    type = "cand_cluster"

    def __init__(self, kind):
        self.qualifiers = {"kind": [kind]}


def _bgc(state, breakdown):
    bgc = BGCRecord("BGC001", "synthetic_node", 1, 1, 100000, 100000,
                    products=["NRPS", "T1PKS"], edge_status="Interior")
    bgc.protocluster_count = len(breakdown)
    bgc.protocluster_breakdown = breakdown
    bgc.overmerge_state = state
    return bgc


def test_neighbouring_interleaved_and_multiple_single_are_suspect():
    for kinds in (["neighbouring"], ["interleaved"], ["single", "single"]):
        assert overmerge_state(kinds) == "OVERMERGE_SUSPECT"


def test_chemical_hybrid_is_coherent_even_with_underlying_single_rows():
    assert overmerge_state(["single", "single", "chemical_hybrid"]) == "COHERENT_CHEMICAL_HYBRID"


def test_parser_preserves_kinds_and_unknown_is_not_assumed_coherent():
    features = [_Feature("neighbouring"), _Feature("single"), _Feature("")]
    assert cand_cluster_kinds(features) == ["neighbouring", "single", "unknown"]
    assert overmerge_state([]) == "NOT_VERIFIABLE"


def test_suspect_state_deinflates_but_coherent_state_does_not():
    breakdown = [{"product": "NRPS"}, {"product": "T1PKS"}]
    suspect = triage_bgcs([_bgc("OVERMERGE_SUSPECT", breakdown)])[0]
    coherent = triage_bgcs([_bgc("COHERENT_CHEMICAL_HYBRID", breakdown)])[0]
    assert max(suspect.ab_score, suspect.af_score, suspect.novelty_score) <= max(
        coherent.ab_score, coherent.af_score, coherent.novelty_score
    )
    assert suspect.bgc_id == coherent.bgc_id == "BGC001"
