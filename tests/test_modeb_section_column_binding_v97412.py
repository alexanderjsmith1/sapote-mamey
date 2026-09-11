import pytest
from mamey.modeb_publication_gate import _section_matrix_findings


def findings(row):
    rows = [[f"§{n}", "SUBSTANTIVE", "source", "RETAIN", "review note"]
            for n in range(1, 49)]
    rows[0] = row
    return {f["code"] for f in _section_matrix_findings(rows) if f["section"] == 1}


def test_state_token_in_evidence_cannot_rescue_invalid_state():
    assert "SECTION_RECONCILIATION_STATE" in findings(
        ["§1", "BOGUS", "SUBSTANTIVE", "RETAIN", "note"])


def test_history_token_in_evidence_cannot_rescue_invalid_history():
    assert "SECTION_PREDECESSOR_DISPOSITION" in findings(
        ["§1", "SUBSTANTIVE", "RETAIN", "BOGUS", "note"])


@pytest.mark.parametrize("state", ["SUBSTANTIVE", "REASONED_NOT_APPLICABLE", "REVIEWED_SCOPE_LIMIT"])
def test_valid_state_and_history_in_their_columns(state):
    assert not findings(["§1", state, "source", "RETAIN", "note"])


def test_short_row_fails_without_index_error():
    assert "SECTION_RECONCILIATION_STATE" in findings(["§1"])
