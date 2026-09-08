from __future__ import annotations

from mamey.cli import build_parser
from mamey.modeb_publication_gate import publication_quality_findings
from mamey.modeb_structure_gate import lint_card
from tests.test_modeb_publication_quality_v9_7_372 import _card


SELECTED = "AS-1 / NODE_1_length_1000_cov_10 / region001 / BGC001"
COMPARATOR = "AS-2 / NODE_2_length_2000_cov_20 / region002 / BGC002"
SHA = "d" * 64
HEADER = (
    "#### Selection process\n"
    "| Selection state | Selected exact identity | Comparator exact identity or terminal state | Candidate-set denominator | Candidate-set receipt | Selected observed metrics | Comparator metrics or terminal basis | Predeclared selection rule | Rule evaluation | Bounded information-gain reason | Discriminating next action |\n"
    "|---|---|---|---:|---|---|---|---|---|---|---|\n"
)
ROW = (
    f"| COMPARATIVE_SELECTION_MEASURED | {SELECTED} | {COMPARATOR} | 2 | {SHA} | "
    "observed priority score 8 and exact-roster coverage 10 of 10 | "
    "observed comparator priority score 5 and exact-roster coverage 8 of 10 | "
    "predeclared rule selects the higher priority score when roster coverage is at least 90 percent | "
    "RULE_MET | this candidate offers bounded information gain only and does not establish biological merit | "
    "compare both exact loci with matched sequence profiles and measure coverage identity and topology results |"
)
TERMINAL = (
    f"| SINGLE_CANDIDATE_SET_TYPED | {SELECTED} | NO_COMPARATOR_SINGLE_CANDIDATE_SET | 1 | {SHA} | "
    "observed priority score 8 and exact-roster coverage 10 of 10 | "
    "the frozen candidate set receipt contains only one eligible candidate with denominator 1 | "
    "predeclared rule selects the top eligible candidate when coverage is at least 90 percent | "
    "SINGLE_CANDIDATE_TERMINAL | this candidate offers bounded information gain only and does not establish biological merit | "
    "sequence the exact locus and measure coverage identity and boundary results against reference profiles |"
)


def _replace(card: str, body: str) -> str:
    marker = "## §2 Section 2\n"
    start = card.index(marker) + len(marker)
    end = card.index("## §3 Section 3\n", start)
    return card[:start] + body.strip() + "\n\n" + card[end:]


def _codes(card: str, enabled: bool = True) -> set[str]:
    return {row["code"] for row in publication_quality_findings(
        card, check_selection_process_v9=enabled) if "_V9_" in row["code"]}


def test_comparative_and_single_candidate_rows_clear_v9():
    assert _codes(_replace(_card(), HEADER + ROW)) == set()
    assert _codes(_replace(_card(), HEADER + TERMINAL)) == set()


def test_v9_is_separate_opt_in_and_closes_selection_empty_prose():
    assert _codes(_card(), enabled=False) == set()
    assert "SECTION_2_V9_SELECTION_PROCESS_MISSING" in _codes(_card())


def test_complete_selected_and_comparator_identities_are_required_and_distinct():
    card = _replace(_card(), HEADER + ROW.replace(SELECTED, "AS-1 / BGC001", 1))
    assert "SECTION_2_V9_SELECTED_IDENTITY_INCOMPLETE" in _codes(card)
    card = _replace(_card(), HEADER + ROW.replace(COMPARATOR, SELECTED, 1))
    assert "SECTION_2_V9_COMPARATOR_EQUALS_SELECTED" in _codes(card)


def test_comparative_denominator_must_be_at_least_two():
    card = _replace(_card(), HEADER + ROW.replace("| 2 |", "| 1 |", 1))
    assert "SECTION_2_V9_COMPARATIVE_DENOMINATOR_TOO_SMALL" in _codes(card)


def test_single_candidate_terminal_shape_is_exact():
    card = _replace(_card(), HEADER + TERMINAL.replace(
        "NO_COMPARATOR_SINGLE_CANDIDATE_SET", COMPARATOR, 1))
    assert "SECTION_2_V9_SINGLE_CANDIDATE_STATE_INVALID" in _codes(card)
    card = _replace(_card(), HEADER + TERMINAL.replace(
        "SINGLE_CANDIDATE_TERMINAL", "RULE_MET", 1))
    assert "SECTION_2_V9_TERMINAL_EVALUATION_MISMATCH" in _codes(card)


def test_receipt_selected_and_comparator_metrics_are_required():
    card = _replace(_card(), HEADER + ROW.replace(SHA, "not-a-hash", 1))
    assert "SECTION_2_V9_CANDIDATE_SET_RECEIPT_INVALID" in _codes(card)
    card = _replace(_card(), HEADER + ROW.replace(
        "observed priority score 8 and exact-roster coverage 10 of 10", "strong candidate", 1))
    assert "SECTION_2_V9_SELECTED_METRICS_UNMEASURED" in _codes(card)
    card = _replace(_card(), HEADER + ROW.replace(
        "observed comparator priority score 5 and exact-roster coverage 8 of 10", "other candidate", 1))
    assert "SECTION_2_V9_COMPARATOR_METRICS_OR_TERMINAL_BASIS_MISSING" in _codes(card)


def test_rule_information_gain_and_next_action_are_substantive():
    card = _replace(_card(), HEADER + ROW.replace(
        "predeclared rule selects the higher priority score when roster coverage is at least 90 percent",
        "we selected this one", 1).replace(
        "this candidate offers bounded information gain only and does not establish biological merit",
        "this is best", 1).replace(
        "compare both exact loci with matched sequence profiles and measure coverage identity and topology results",
        "do more work", 1))
    codes = _codes(card)
    assert {"SECTION_2_V9_SELECTION_RULE_UNSPECIFIC",
            "SECTION_2_V9_INFORMATION_GAIN_UNBOUNDED",
            "SECTION_2_V9_NEXT_ACTION_UNSPECIFIC"}.issubset(codes)


def test_row_count_and_rule_evaluation_are_controlled():
    card = _replace(_card(), HEADER + ROW + "\n" + ROW)
    assert "SECTION_2_V9_ROW_COUNT" in _codes(card)
    card = _replace(_card(), HEADER + ROW.replace("RULE_MET", "PASS", 1))
    assert "SECTION_2_V9_RULE_EVALUATION_INVALID" in _codes(card)


def test_structure_gate_forwards_v9():
    codes = {row["code"] for row in lint_card(
        _card(), check_publication_quality=True, check_selection_process_v9=True)}
    assert "SECTION_2_V9_SELECTION_PROCESS_MISSING" in codes


def test_cli_exposes_separate_v9_switch():
    args = build_parser().parse_args(["verify-modeb", "candidate.md", "--selection-process-v9"])
    assert args.selection_process_v9 is True
    assert args.inventory_reconciliation_v8 is False
