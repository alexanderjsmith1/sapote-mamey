"""Known-bad mutation target for the gold depth-floor completeness guard."""
from __future__ import annotations

from mamey.validate import validate_package
from tests.test_v9_7_335_tier1_gates_known_bad_input import _make_min_package


def test_missing_depth_assignment_fails_gold_completeness(tmp_path):
    pkg = _make_min_package(tmp_path)
    inventory = pkg / "AS-TEST_2_inventory.csv"
    inventory.write_text(
        inventory.read_text(encoding="utf-8").replace("BGC002,abbreviated_ledger", "BGC002,"),
        encoding="utf-8",
    )
    result = validate_package(pkg, enrichment_check=True)
    assert result["gold_completeness"] == "FAIL", result.get("gold_note")
    assert result["status"] == "FAIL", result
