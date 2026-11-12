"""The wet-lab decision matrix must not turn a missing AB/AF score into LOW (score 0.00).

A blank or placeholder score cell is missing evidence (mamey/missing_values.py). A row with no score
at all is UNRESOLVED, the state the matrix already uses for a value it cannot score. A measured 0
is still LOW, and one present score is still used when the other is missing.
"""
from mamey import compile_report as CR


def test_both_scores_blank_is_unresolved_not_low():
    for blank in ("", "  ", None, "NA", "n/a", "-"):
        action, reason = CR._decision_for({"AB_auto": blank, "AF_auto": blank, "Corrected_rank": "12"})
        assert action == "UNRESOLVED", blank
        assert "score 0.00" not in reason
        assert "missing score is not a low score" in reason


def test_row_without_score_columns_is_unresolved():
    action, _ = CR._decision_for({"Corrected_rank": "4", "Novelty_auto": "MED"})
    assert action == "UNRESOLVED"


def test_one_present_score_is_still_used():
    assert CR._decision_for({"AB_auto": "", "AF_auto": "0.45", "Corrected_rank": "12"})[0] == "MEDIUM ACT"
    assert CR._decision_for({"AB_auto": "0.9", "Corrected_rank": "1"})[0] == "PRIORITY ISO"


def test_measured_zero_is_still_low():
    action, reason = CR._decision_for({"AB_auto": "0", "AF_auto": "0", "Corrected_rank": "12"})
    assert action == "LOW" and "score 0.00" in reason


def test_exclusions_still_come_first():
    assert CR._decision_for({"Standing_rule": "saccharide", "Corrected_rank": "5"})[0] == "EXCL"


def test_unparsable_value_is_still_named():
    action, reason = CR._decision_for({"AB_auto": "high", "AF_auto": "", "Corrected_rank": "12"})
    assert action == "UNRESOLVED" and "AB_auto" in reason
