"""Two ledger rows with the card's priority rank are a finding, not a silent first-row pick.

The checker used the first row with the rank, so a matching first row hid a
conflicting duplicate.
"""
import csv

from tests.test_audit_modeb_support_card import VALID_CARD
from tools.audit_modeb_support_card import audit_card

FIELDS = ["priority_rank", "markdown_path", "value_tier", "qc_status",
          "expected_genes", "direct_hit_union", "no_significant_hit"]


def _codes(tmp_path, tiers):
    card = tmp_path / "card.md"
    card.write_text(VALID_CARD, encoding="utf-8")
    ledger = tmp_path / "ledger.csv"
    with ledger.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for tier in tiers:
            writer.writerow({"priority_rank": "200", "markdown_path": str(card), "value_tier": tier,
                             "qc_status": "PASS", "expected_genes": "1", "direct_hit_union": "1",
                             "no_significant_hit": "0"})
    result = audit_card(card, ledger=ledger, check_sources=False)
    return {f["code"] for f in result.findings}, result.pass_gate


def test_duplicate_rank_fails(tmp_path):
    codes, passed = _codes(tmp_path, ["USEFUL_WITH_LIMITATIONS", "HOLD"])
    assert "LEDGER_DUPLICATE_RANK" in codes and not passed


def test_single_matching_row_passes(tmp_path):
    codes, passed = _codes(tmp_path, ["USEFUL_WITH_LIMITATIONS"])
    assert passed, codes
