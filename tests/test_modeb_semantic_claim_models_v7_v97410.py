from __future__ import annotations

from mamey.cli import build_parser
from mamey.modeb_publication_gate import publication_quality_findings
from mamey.modeb_structure_gate import lint_card
from tests.test_modeb_publication_quality_v9_7_372 import _card


ROSTER = {"ctg1_1"}
SHA = "b" * 64
SECTIONS = (8, 11, 13, 44)
HEADER = (
    "#### Semantic claim model\n"
    "| Typed state | Exact target or measured object | Evidence for or terminal basis | Evidence against or limitation | Evidence receipt | Narrowest allowed claim | Resolving comparison or assay | Result-dependent claim consequence |\n"
    "|---|---|---|---|---|---|---|---|\n"
)
ROWS = {
    8: f"| COMPARATOR_MEASURED | ctg1_1 MIBiG comparator cluster similarity | measured 63 percent identity and 71 percent coverage across 4 genes | synteny conflict and incomplete comparator boundaries remain important limitations | {SHA} | this supports only a candidate comparator cluster and cannot establish product identity | compare the complete clusters and measure gene-order coverage and sequence identity results | retain the comparator claim only if the result preserves both measures; otherwise reject it |",
    11: f"| FAMILY_MODEL_DEFINED | ctg1_1 biosynthetic product family model | measured 3 conserved catalytic residues among 5 family references | substrate ambiguity and an alternative scaffold family remain important limitations | {SHA} | this is only a candidate biosynthetic family hypothesis and cannot establish a product | profile the protein against curated families and measure residue support and coverage results | retain the family hypothesis if the result supports both measures; otherwise revise it |",
    13: f"| ACTIVITY_HYPOTHESIS_DEFINED | ctg1_1 antibacterial activity assay hypothesis | measured 0 direct activity assays in the bound evidence package | assay background and an alternative non-antibacterial bioactivity remain important limitations | {SHA} | antibacterial activity is only an untested hypothesis and cannot establish bioactivity | culture the locus-bearing strain and assay inhibition with a measured dose-response readout | retain the activity hypothesis only if the result is replicated; otherwise reject it |",
    44: f"| PREVALENCE_MEASURED | ctg1_1 cohort prevalence denominator model | measured prevalence was 3 of 20 genomes in the defined cohort denominator | sampling bias and incomplete assemblies remain important prevalence limitations | {SHA} | this supports only a candidate cohort prevalence and cannot establish population frequency | search the frozen cohort and measure exact-locus hit counts and denominator results | retain the prevalence claim only if the result reproduces 3 of 20; otherwise revise it |",
}


def _replace(card: str, section: int, body: str) -> str:
    marker = f"## §{section} Section {section}\n"
    start = card.index(marker) + len(marker)
    end = card.index(f"## §{section + 1} Section {section + 1}\n", start)
    return card[:start] + body.strip() + "\n\n" + card[end:]


def _structured_card() -> str:
    card = _card()
    for section in SECTIONS:
        card = _replace(card, section, HEADER + ROWS[section])
    return card


def _codes(card: str, enabled: bool = True, roster=ROSTER) -> set[str]:
    return {row["code"] for row in publication_quality_findings(
        card, canonical_loci=roster, check_semantic_claim_models_v7=enabled)}


def _v7(card: str, **kwargs) -> set[str]:
    return {code for code in _codes(card, **kwargs) if "_V7_" in code}


def test_structured_claim_models_clear_v7():
    assert _v7(_structured_card()) == set()


def test_v7_is_separate_opt_in_and_closes_four_section_prose_bypass():
    assert _v7(_card(), enabled=False) == set()
    card = _card()
    for section in SECTIONS:
        card = _replace(card, section, ("ctg1_1 is discussed cautiously with no product identity or activity claim. " * 10))
    codes = _v7(card)
    assert all(f"SECTION_{section}_V7_SEMANTIC_CLAIM_MODEL_MISSING" in codes for section in SECTIONS)


def test_generic_filled_row_fails_shared_primitives():
    row = "| COMPARATOR_MEASURED | ctg1_1 evidence present | evidence present | evidence present | no | evidence present | future work | later |"
    codes = _v7(_replace(_structured_card(), 8, HEADER + row))
    assert {"SECTION_8_V7_OBJECT_UNTYPED", "SECTION_8_V7_EVIDENCE_OR_TERMINAL_BASIS_MISSING",
            "SECTION_8_V7_EVIDENCE_AGAINST_MISSING", "SECTION_8_V7_RECEIPT_INVALID",
            "SECTION_8_V7_CLAIM_UNBOUNDED", "SECTION_8_V7_RESOLVING_ACTION_UNSPECIFIC",
            "SECTION_8_V7_CLAIM_CONSEQUENCE_MISSING"}.issubset(codes)


def test_wrong_section_displacement_fails_state_and_object():
    card = _replace(_structured_card(), 8, HEADER + ROWS[13])
    codes = _v7(card)
    assert "SECTION_8_V7_STATE_UNTYPED" in codes
    assert "SECTION_8_V7_OBJECT_UNTYPED" in codes


def test_reasoned_terminal_states_clear_v7():
    states = {8: ("COMPARATOR_UNAVAILABLE_TYPED", "comparator cluster"),
              11: ("FAMILY_UNRESOLVED_TYPED", "biosynthetic family"),
              13: ("ACTIVITY_EVIDENCE_UNAVAILABLE_TYPED", "activity assay"),
              44: ("COHORT_UNAVAILABLE_TYPED", "cohort prevalence denominator")}
    card = _card()
    for section, (state, obj) in states.items():
        row = (f"| {state} | ctg1_1 exact {obj} | analysis not run because the source package receipt is unavailable and denominator reason is recorded | "
               f"source incompleteness and an alternative model remain important limitations | {SHA} | "
               f"the {obj} remains an unresolved hypothesis only and cannot establish a stronger claim | "
               "compare the exact target against controls and measure the specified result and support readout | "
               "retain the hold if the result remains unavailable; otherwise revise the claim |")
        card = _replace(card, section, HEADER + row)
    assert _v7(card) == set()


def test_external_roster_and_measured_basis_are_required():
    card = _structured_card().replace("ctg1_1 MIBiG", "ctg9_9 MIBiG", 1)
    assert "SECTION_8_V7_TARGET_OUTSIDE_ROSTER" in _v7(card)
    card = _structured_card().replace("measured 63 percent identity and 71 percent coverage across 4 genes",
                                      "comparison evidence appears generally supportive")
    assert "SECTION_8_V7_EVIDENCE_OR_TERMINAL_BASIS_MISSING" in _v7(card)


def test_prevalence_needs_numerator_denominator_expression():
    card = _structured_card().replace("measured prevalence was 3 of 20 genomes in the defined cohort denominator",
                                      "measured prevalence was 3 genomes in the defined cohort")
    assert "SECTION_44_V7_EVIDENCE_OR_TERMINAL_BASIS_MISSING" in _v7(card)


def test_receipt_must_be_exactly_one_hash():
    card = _structured_card().replace(f"| {SHA} |", f"| {SHA} {SHA} |", 1)
    assert "SECTION_8_V7_RECEIPT_INVALID" in _v7(card)


def test_evidence_claim_action_and_consequence_cannot_collapse():
    card = _structured_card().replace(
        "synteny conflict and incomplete comparator boundaries remain important limitations",
        "measured 63 percent identity and 71 percent coverage across 4 genes", 1
    ).replace("this supports only a candidate comparator cluster and cannot establish product identity",
              "the comparator is correct", 1
    ).replace("compare the complete clusters and measure gene-order coverage and sequence identity results",
              "do more work", 1
    ).replace("retain the comparator claim only if the result preserves both measures; otherwise reject it",
              "review later", 1)
    codes = _v7(card)
    assert {"SECTION_8_V7_EVIDENCE_COLLAPSED", "SECTION_8_V7_CLAIM_UNBOUNDED",
            "SECTION_8_V7_RESOLVING_ACTION_UNSPECIFIC", "SECTION_8_V7_CLAIM_CONSEQUENCE_MISSING"}.issubset(codes)


def test_structure_gate_forwards_v7():
    codes = {row["code"] for row in lint_card(
        _card(), check_publication_quality=True,
        check_semantic_claim_models_v7=True, canonical_loci=ROSTER)}
    assert "SECTION_44_V7_SEMANTIC_CLAIM_MODEL_MISSING" in codes


def test_cli_exposes_separate_v7_switch():
    args = build_parser().parse_args(["verify-modeb", "candidate.md", "--semantic-claim-models-v7"])
    assert args.semantic_claim_models_v7 is True
    assert args.semantic_decision_chains_v6 is False
