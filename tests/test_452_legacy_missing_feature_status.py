import json
import pytest
from mamey.legacy_feature_gate import default_legacy_rows, validate_legacy_rows, write_legacy_gate_outputs, FIELDNAMES
from mamey.csv_safety import SafeDictWriter

@pytest.mark.parametrize("state,expected", [("missing", "FAIL"), ("needs_test", "HOLD"), ("deferred", "HOLD")])
def test_recovery_note_does_not_turn_missing_or_unverified_feature_into_pass(tmp_path, state, expected):
    rows = default_legacy_rows()
    rows[0]["current_status"] = state
    rows[0]["recovery_action"] = "review pending"
    matrix = tmp_path / "matrix.csv"
    with matrix.open("w", newline="") as handle:
        writer = SafeDictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    result = write_legacy_gate_outputs(matrix, tmp_path / "output")
    assert result["status"] == expected
    receipt = json.loads((tmp_path / "output/LEGACY_FEATURE_GATE_RECEIPT.json").read_text())
    if expected == "HOLD":
        assert receipt["failure_count"] == 0
        assert receipt["unverified_features"] == [rows[0]["legacy_feature"]]

def test_active_default_feature_matrix_still_passes():
    assert validate_legacy_rows(default_legacy_rows()) == []
