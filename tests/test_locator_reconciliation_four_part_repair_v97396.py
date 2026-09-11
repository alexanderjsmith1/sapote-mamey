"""Repair 11: exact-locus locator reconciliation is four-part and fail-closed."""
import csv
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "tools"))

import locator_reconciliation as lr  # noqa: E402


ROW = {
    "Strain": "EXPECTED-STRAIN",
    "Contig": "NODE_14_length_159225_cov_15",
    "Node_ID": "NODE_14",
    "antiSMASH_Region": "region001",
    "BGC_ID": "BGC007",
    "Assembly_Locator": "legacy display locator",
}
GOOD = (
    "# Mode B — EXPECTED-STRAIN / NODE_14_length_159225_cov_15 / "
    "region001 / BGC007\n"
)


def verdict(card=GOOD, row=None):
    return lr.reconcile_card_verdict(card, ROW if row is None else row)


def test_complete_exact_identity_passes_and_displays_in_required_order():
    got = verdict()
    assert got["status"] == "PASS"
    assert got["exit_code"] == 0
    assert got["identity_display"] == (
        "EXPECTED-STRAIN / NODE_14_length_159225_cov_15 / region001 / BGC007"
    )


def test_original_adversarial_wrong_strain_and_alias_is_refused():
    got = verdict(
        "# Mode B — WRONG-STRAIN / NODE_14_length_159225_cov_15 / region001 / BGC999\n"
    )
    assert got["status"] == "MISMATCH"
    assert got["exit_code"] == 1
    assert got["refusal_reason"] == "IDENTITY_CONFLICT"
    assert {e["field"] for e in got["errors"]} == {"strain", "bgc_alias"}


def test_zero_exact_identity_refused_even_when_legacy_fields_are_complete():
    card = (
        "## BGC007 (EXPECTED-STRAIN · region001)\n"
        "**Node/Contig:** NODE_14_length_159225_cov_15\n"
        "**BGC:** BGC007\n"
    )
    got = verdict(card)
    assert got["status"] == "UNPARSEABLE"
    assert got["refusal_reason"] == "ZERO_EXACT_IDENTITIES"
    assert got["secondary_fields"]["card"]


def test_multiple_exact_identity_headers_refused_even_when_identical():
    got = verdict(GOOD + "\n" + GOOD)
    assert got["status"] == "MISMATCH"
    assert got["refusal_reason"] == "MULTIPLE_EXACT_IDENTITIES"


def test_each_missing_component_is_refused_without_body_fallback():
    for index in range(4):
        parts = ["EXPECTED-STRAIN", "NODE_14_length_159225_cov_15", "region001", "BGC007"]
        parts[index] = "?"
        card = "# Mode B — " + " / ".join(parts) + "\n**antiSMASH region:** region001\n"
        got = verdict(card)
        assert got["status"] == "UNPARSEABLE", (index, got)
        assert got["refusal_reason"] == "INCOMPLETE_EXACT_IDENTITY"


def test_expected_identity_missing_component_is_refused():
    incomplete = dict(ROW)
    incomplete.pop("Strain")
    got = verdict(row=incomplete)
    assert got["status"] == "UNPARSEABLE"
    assert got["refusal_reason"] == "EXPECTED_IDENTITY_INCOMPLETE"


def test_conflicting_expected_fields_are_refused():
    conflicting = dict(ROW, strain_id="OTHER-STRAIN")
    got = verdict(row=conflicting)
    assert got["status"] == "MISMATCH"
    assert got["refusal_reason"] == "EXPECTED_IDENTITY_CONFLICT"


def test_no_rounding_casefold_or_short_node_fallback():
    cases = (
        "# Mode B — expected-strain / NODE_14_length_159225_cov_15 / region001 / BGC007\n",
        "# Mode B — EXPECTED-STRAIN / NODE_14 / region001 / BGC007\n",
        "# Mode B — EXPECTED-STRAIN / NODE_14_length_159225_cov_15 / region1 / BGC007\n",
        "# Mode B — EXPECTED-STRAIN / NODE_14_length_159225_cov_15 / region001 / BGC7\n",
    )
    for card in cases:
        got = verdict(card)
        assert got["status"] == "MISMATCH", (card, got)
        assert got["refusal_reason"] == "IDENTITY_CONFLICT"


def test_legacy_and_display_aliases_are_typed_secondary_fields_only():
    got = verdict()
    assert got["status"] == "PASS"
    secondary = got["secondary_fields"]["triage"]
    assert {item["kind"] for item in secondary} == {
        "DISPLAY_NODE_ALIAS", "LEGACY_ASSEMBLY_LOCATOR"
    }


def test_batch_csv_carries_typed_refusal_and_secondary_fields(tmp_path):
    rows = lr.reconcile_batch([{
        "card_text": "## BGC007 (EXPECTED-STRAIN · region001)\n",
        "triage_row": ROW,
    }])
    assert rows[0]["refusal_reason"] == "ZERO_EXACT_IDENTITIES"
    parsed = json.loads(rows[0]["secondary_fields"])
    assert parsed["card"]
    out = tmp_path / "header_locator_reconciliation.csv"
    lr.write_reconciliation_csv(rows, out)
    with out.open(newline="", encoding="utf-8") as handle:
        written = next(csv.DictReader(handle))
    assert written["refusal_reason"] == "ZERO_EXACT_IDENTITIES"
    assert written["identity_display"] == ""
