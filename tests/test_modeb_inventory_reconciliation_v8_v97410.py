from __future__ import annotations

from mamey.cli import build_parser
from mamey.modeb_publication_gate import publication_quality_findings
from mamey.modeb_structure_gate import lint_card
from tests.test_modeb_publication_quality_v9_7_372 import _card


ROSTER = {"ctg1_1"}
SHA = "c" * 64
SECTIONS = (32, 33, 34, 35, 37, 38)
HEADER = (
    "#### Inventory reconciliation\n"
    "| Typed state | Exact member or typed zero | Section-specific role | Evidence receipt | Declared denominator | Evidence state | Limitation | Reconciliation state |\n"
    "|---|---|---|---|---:|---|---|---|\n"
)
ROWS = {
    32: f"| ASSEMBLY_INVENTORY_MEASURED | ctg1_1 | core assembly component | {SHA} | 1 | OBSERVED_SOURCE_BOUND | annotation remains uncertain and cannot establish pathway membership | EXACT_MATCH |",
    33: f"| MODULE_PROGRAM_MEASURED | ctg1_1 | module domain programming candidate | {SHA} | 1 | INFERRED_SOURCE_BOUND | substrate prediction is uncertain and incomplete without biochemical evidence | EXACT_MATCH |",
    34: f"| INITIATION_RELEASE_MEASURED | ctg1_1 | initiation starter loading candidate | {SHA} | 1 | INFERRED_SOURCE_BOUND | release assignment is missing and the initiation model remains uncertain | EXACT_MATCH |",
    35: f"| PROTOCLUSTER_DECOMPOSITION_MEASURED | ctg1_1 | protocluster one component member | {SHA} | 1 | OBSERVED_SOURCE_BOUND | boundary placement remains uncertain because flanking evidence is incomplete | EXACT_MATCH |",
    37: f"| PARTNER_INVENTORY_MEASURED | ctg1_1 | accessory partner enzyme candidate | {SHA} | 1 | INFERRED_SOURCE_BOUND | co-location is a limitation and cannot establish functional participation | EXACT_MATCH |",
    38: f"| RESISTANCE_EFFLUX_INVENTORY_MEASURED | ctg1_1 | resistance efflux transporter candidate | {SHA} | 1 | INFERRED_SOURCE_BOUND | background transport function remains an alternative unresolved explanation | EXACT_MATCH |",
}
ZERO_ROWS = {
    32: f"| NO_ASSEMBLY_COMPONENTS_OBSERVED_TYPED | TYPED_ZERO | assembly component measured zero | {SHA} | 0 | MEASURED_ZERO_SOURCE_BOUND | source coverage is incomplete and absence cannot establish biology | EXACT_MATCH |",
    33: f"| NO_MODULES_ASSIGNABLE_TYPED | TYPED_ZERO | module program measured zero | {SHA} | 0 | MEASURED_ZERO_SOURCE_BOUND | domain evidence is incomplete and assignment remains unresolved | EXACT_MATCH |",
    34: f"| NO_INITIATION_RELEASE_ASSIGNABLE_TYPED | TYPED_ZERO | initiation release measured zero | {SHA} | 0 | MEASURED_ZERO_SOURCE_BOUND | source annotations are incomplete and mechanisms remain unresolved | EXACT_MATCH |",
    35: f"| NO_PROTOCLUSTERS_ASSIGNABLE_TYPED | TYPED_ZERO | protocluster component measured zero | {SHA} | 0 | MEASURED_ZERO_SOURCE_BOUND | boundary evidence is incomplete and decomposition remains unresolved | EXACT_MATCH |",
    37: f"| NO_PARTNERS_OBSERVED_TYPED | TYPED_ZERO | accessory partner measured zero | {SHA} | 0 | MEASURED_ZERO_SOURCE_BOUND | source coverage is incomplete and participation remains unresolved | EXACT_MATCH |",
    38: f"| NO_RESISTANCE_EFFLUX_OBSERVED_TYPED | TYPED_ZERO | resistance efflux measured zero | {SHA} | 0 | MEASURED_ZERO_SOURCE_BOUND | annotation sensitivity is incomplete and absence remains uncertain | EXACT_MATCH |",
}


def _replace(card: str, section: int, body: str) -> str:
    marker = f"## §{section} Section {section}\n"
    start = card.index(marker) + len(marker)
    end = card.index(f"## §{section + 1} Section {section + 1}\n", start)
    return card[:start] + body.strip() + "\n\n" + card[end:]


def _structured_card(*, zero: bool = False) -> str:
    card = _card()
    rows = ZERO_ROWS if zero else ROWS
    for section in SECTIONS:
        card = _replace(card, section, HEADER + rows[section])
    return card


def _v8(card: str, *, enabled: bool = True, roster=ROSTER) -> set[str]:
    return {row["code"] for row in publication_quality_findings(
        card, canonical_loci=roster, check_inventory_reconciliation_v8=enabled)
        if "_V8_" in row["code"]}


def test_measured_and_typed_zero_inventories_clear_v8():
    assert _v8(_structured_card()) == set()
    assert _v8(_structured_card(zero=True)) == set()


def test_v8_is_opt_in_and_closes_retained_contradictory_prose_bypass():
    assert _v8(_card(), enabled=False) == set()
    codes = _v8(_card())
    assert all(f"SECTION_{section}_V8_INVENTORY_RECONCILIATION_MISSING" in codes
               for section in SECTIONS)


def test_unnamed_and_out_of_roster_members_fail():
    card = _structured_card().replace("| ctg1_1 | core assembly", "| unnamed member | core assembly", 1)
    assert "SECTION_32_V8_MEMBER_IDENTITY_INVALID" in _v8(card)
    card = _structured_card().replace("| ctg1_1 | core assembly", "| ctg9_9 | core assembly", 1)
    assert "SECTION_32_V8_MEMBER_OUTSIDE_ROSTER" in _v8(card)


def test_duplicate_members_and_denominator_mismatch_fail():
    card = _replace(_structured_card(), 32, HEADER + ROWS[32] + "\n" + ROWS[32])
    codes = _v8(card)
    assert "SECTION_32_V8_MEMBER_DUPLICATE" in codes
    assert "SECTION_32_V8_DENOMINATOR_MISMATCH" not in codes
    card = _structured_card().replace("| 1 | OBSERVED_SOURCE_BOUND", "| 6 | OBSERVED_SOURCE_BOUND", 1)
    assert "SECTION_32_V8_DENOMINATOR_MISMATCH" in _v8(card)


def test_conflicting_denominators_fail_even_when_unique_members():
    card = _replace(
        _structured_card(), 32,
        HEADER + ROWS[32] + "\n" + ROWS[32].replace("ctg1_1", "ctg1_2").replace("| 1 |", "| 2 |"))
    codes = _v8(card, roster={"ctg1_1", "ctg1_2"})
    assert "SECTION_32_V8_DENOMINATOR_CONFLICT" in codes


def test_zero_and_member_rows_are_exclusive():
    card = _replace(_structured_card(), 38, HEADER + ROWS[38] + "\n" + ZERO_ROWS[38])
    assert "SECTION_38_V8_ZERO_MEMBER_MIXED" in _v8(card)


def test_typed_zero_literal_denominator_and_evidence_state_are_fixed():
    card = _structured_card(zero=True).replace("TYPED_ZERO", "ctg1_1", 1)
    assert "SECTION_32_V8_TYPED_ZERO_INVALID" in _v8(card)
    card = _structured_card(zero=True).replace("| 0 | MEASURED_ZERO_SOURCE_BOUND", "| 1 | OBSERVED_SOURCE_BOUND", 1)
    codes = _v8(card)
    assert "SECTION_32_V8_ZERO_EVIDENCE_STATE_MISMATCH" in codes
    assert "SECTION_32_V8_DENOMINATOR_MISMATCH" in codes


def test_section_role_receipt_evidence_limitation_and_reconciliation_are_checked():
    card = _structured_card().replace("module domain programming candidate", "resistance efflux transporter", 1)
    assert "SECTION_33_V8_ROLE_UNTYPED" in _v8(card)
    card = _structured_card().replace(SHA, "not-a-hash", 1)
    assert "SECTION_32_V8_RECEIPT_INVALID" in _v8(card)
    card = _structured_card().replace("OBSERVED_SOURCE_BOUND", "PRESENT", 1)
    assert "SECTION_32_V8_EVIDENCE_STATE_INVALID" in _v8(card)
    card = _structured_card().replace("annotation remains uncertain and cannot establish pathway membership", "looks fine", 1)
    assert "SECTION_32_V8_LIMITATION_MISSING" in _v8(card)
    card = _structured_card().replace("EXACT_MATCH", "PARTIAL", 1)
    assert "SECTION_32_V8_RECONCILIATION_NOT_EXACT" in _v8(card)


def test_structure_gate_forwards_v8():
    codes = {row["code"] for row in lint_card(
        _card(), check_publication_quality=True,
        check_inventory_reconciliation_v8=True, canonical_loci=ROSTER)}
    assert "SECTION_35_V8_INVENTORY_RECONCILIATION_MISSING" in codes


def test_cli_exposes_separate_v8_switch():
    args = build_parser().parse_args(
        ["verify-modeb", "candidate.md", "--inventory-reconciliation-v8"])
    assert args.inventory_reconciliation_v8 is True
    assert args.semantic_claim_models_v7 is False
