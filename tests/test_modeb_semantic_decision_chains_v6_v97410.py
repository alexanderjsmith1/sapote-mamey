from __future__ import annotations

from mamey.cli import build_parser
from mamey.modeb_publication_gate import publication_quality_findings
from mamey.modeb_structure_gate import lint_card
from tests.test_modeb_publication_quality_v9_7_372 import _card


ROSTER = {"ctg1_1"}
SHA = "a" * 64
SECTIONS = (14, 16, 21, 22, 23, 25, 30, 41)
HEADER = (
    "#### Semantic decision chain\n"
    "| Typed state | Exact target or measured object | Evidence or terminal basis | Alternative or limitation | Allowed inference | Resolving action and measured result | Decision consequence |\n"
    "|---|---|---|---|---|---|---|\n"
)


def _replace(card: str, section: int, body: str) -> str:
    marker = f"## §{section} Section {section}\n"
    start = card.index(marker) + len(marker)
    next_marker = f"## §{section + 1} Section {section + 1}\n"
    end = card.index(next_marker, start)
    return card[:start] + body.strip() + "\n\n" + card[end:]


ROWS = {
    14: f"| LIMIT_DEFINED | ctg1_1 product identity claim | measured 0 direct structures in the bound receipt sha-256 {SHA} | database similarity is a limitation and an alternative product remains possible | product identity is not established and only a class-level candidate is retained | isolate the ctg1_1-dependent LC-MS feature and measure its structure by NMR | retain the limit unless the result supports a structure; otherwise hold the claim |",
    16: f"| RESULT_MEASURED | ctg1_1 BLASTP protein homology | measured 71% identity and 88% query coverage in receipt sha-256 {SHA} | profile bias and a different domain role remain alternative explanations | homology supports navigation only and cannot establish pathway function | compare ctg1_1 against the profile panel and measure coverage and conserved-residue results | retain the homology model only if the result preserves coverage; otherwise reject it |",
    21: f"| MASS_MEASURED | ctg1_1 precursor mass model | measured m/z 812.4 in 3 replicated LC-MS runs recorded by receipt {SHA} | an adduct or unrelated background feature is an alternative limitation | the mass is a candidate feature only and does not establish structure | delete ctg1_1 with complementation and measure whether the m/z 812.4 feature disappears and returns | retain the precursor model only if the result tracks genotype; otherwise reject it |",
    22: f"| SEARCH_MEASURED | ctg1_1 RiPP database search | measured 0 close hits among 2400 entries in receipt sha-256 {SHA} | database incompleteness and divergent precursors remain limitations | absence of a close hit supports novelty navigation only and cannot establish novelty | search an expanded precursor database and measure hit coverage identity and denominator | retain the no-close-hit model only if the expanded result agrees; otherwise revise it |",
    23: f"| DESIGN_READY | ctg1_1 heterologous expression construct | observed 1 complete transferred interval with both boundaries in receipt {SHA} | host background and construct failure remain alternative explanations | the design supports an experiment only and does not establish production | clone the complete interval into a matched host and measure LC-MS features against empty-vector controls | advance the model only if the result is reproducible and interval-dependent; otherwise hold it |",
    25: f"| NEIGHBOURHOOD_MEASURED | ctg1_1 genomic neighbourhood boundary | measured 12 flanking genes across a 28000 bp interval in receipt {SHA} | assembly truncation and unrelated local genes remain boundary limitations | the interval is a boundary hypothesis only and remains unresolved | sequence both flanks and measure whether read coverage closes the proposed neighbourhood boundary | retain the boundary only if the result spans both edges; otherwise revise it |",
    30: f"| DECISION_BRANCH_DEFINED | ctg1_1 leading pathway model experiment | measured evidence gap 1 is locus attribution in receipt {SHA} | technical failure and an alternative primary-metabolism model remain limitations | the pathway model is only a testable hypothesis and activity remains unknown | delete ctg1_1 with complementation and measure a replicated LC-MS feature readout | retain the leading model if the result disappears and returns; otherwise reject or hold it |",
    41: f"| PHYLOGENY_MEASURED | ctg1_1 protein phylogeny comparator | measured branch support 92% across 50 aligned proteins in receipt {SHA} | taxon sampling bias and a conflicting domain topology remain limitations | the tree supports family navigation only and cannot establish biochemical function | align the expanded comparator panel and measure branch support and topology stability | retain the family placement only if the result is stable; otherwise revise it |",
}


def _structured_card() -> str:
    card = _card()
    for section in SECTIONS:
        card = _replace(card, section, HEADER + ROWS[section])
    return card


def _codes(card: str, *, enabled: bool = True, roster=ROSTER) -> set[str]:
    return {row["code"] for row in publication_quality_findings(
        card, canonical_loci=roster,
        check_semantic_decision_chains_v6=enabled,
    )}


def _v6_codes(card: str, **kwargs) -> set[str]:
    return {code for code in _codes(card, **kwargs) if "_V6_" in code}


def test_structured_decision_chains_clear_v6():
    assert _v6_codes(_structured_card()) == set()


def test_v6_remains_a_separate_opt_in():
    assert _v6_codes(_card(), enabled=False) == set()
    codes = _v6_codes(_card())
    assert all(f"SECTION_{section}_V6_SEMANTIC_DECISION_CHAIN_MISSING" in codes for section in SECTIONS)


def test_retained_long_claim_safe_decision_empty_bypass_is_closed():
    card = _card()
    for section in SECTIONS:
        body = (
            f"The exact ctg1_1 query provides cautious context for section {section}. "
            f"Evidence remains provisional and product identity activity expression and function are not established. "
            f"General analysis may be useful after further review of section-specific information. "
        ) * 6
        card = _replace(card, section, body)
    codes = _v6_codes(card)
    assert all(f"SECTION_{section}_V6_SEMANTIC_DECISION_CHAIN_MISSING" in codes for section in SECTIONS)


def test_filled_generic_rows_fail_shared_primitives():
    card = _structured_card()
    card = _replace(card, 16, HEADER + "| RESULT_MEASURED | ctg1_1 evidence present | evidence present | evidence present | evidence present | future work | decision present |")
    codes = _v6_codes(card)
    assert "SECTION_16_V6_OBJECT_UNTYPED" in codes
    assert "SECTION_16_V6_EVIDENCE_OR_TERMINAL_BASIS_MISSING" in codes
    assert "SECTION_16_V6_ALTERNATIVE_OR_LIMITATION_MISSING" in codes
    assert "SECTION_16_V6_ALLOWED_INFERENCE_UNBOUNDED" in codes
    assert "SECTION_16_V6_RESOLVING_ACTION_UNSPECIFIC" in codes
    assert "SECTION_16_V6_DECISION_CONSEQUENCE_MISSING" in codes


def test_wrong_section_semantic_displacement_fails_profiles():
    card = _structured_card()
    card = _replace(card, 16, HEADER + ROWS[21])
    card = _replace(card, 21, HEADER + ROWS[16])
    codes = _v6_codes(card)
    assert "SECTION_16_V6_STATE_UNTYPED" in codes
    assert "SECTION_16_V6_OBJECT_UNTYPED" in codes
    assert "SECTION_21_V6_STATE_UNTYPED" in codes
    assert "SECTION_21_V6_OBJECT_UNTYPED" in codes


def test_reasoned_terminal_states_clear_v6():
    terminal_states = {
        14: ("EVIDENCE_UNAVAILABLE_TYPED", "ctg1_1 product identity claim"),
        16: ("ANALYSIS_NOT_RUN_TYPED", "ctg1_1 BLASTP protein profile"),
        21: ("PRECURSOR_NOT_ASSIGNABLE_TYPED", "ctg1_1 precursor mass model"),
        22: ("SEARCH_NOT_RUN_TYPED", "ctg1_1 RiPP database search"),
        23: ("EXPRESSION_NOT_READY_TYPED", "ctg1_1 heterologous expression construct"),
        25: ("BOUNDARY_UNRESOLVED_TYPED", "ctg1_1 genomic neighbourhood boundary"),
        30: ("EXPERIMENT_NOT_READY_TYPED", "ctg1_1 pathway model experiment"),
        41: ("PHYLOGENY_NOT_RUN_TYPED", "ctg1_1 protein phylogeny comparator"),
    }
    card = _card()
    for section, (state, obj) in terminal_states.items():
        row = (
            f"| {state} | {obj} | analysis not run because the sealed source package has no exact result; denominator 0 and receipt missing | "
            "source incompleteness and an alternative model remain important limitations | "
            "the interpretation remains unresolved and cannot support a stronger claim | "
            "sequence the complete locus and measure the specified result against matched controls | "
            "retain the hold only if the result remains unavailable; otherwise revise the model |"
        )
        card = _replace(card, section, HEADER + row)
    assert _v6_codes(card) == set()


def test_targets_must_be_in_external_roster():
    card = _structured_card().replace("ctg1_1 BLASTP protein homology", "ctg9_9 BLASTP protein homology")
    assert "SECTION_16_V6_TARGET_OUTSIDE_ROSTER" in _v6_codes(card)


def test_measured_state_requires_quantified_or_receipt_bound_basis():
    card = _structured_card().replace(
        f"measured 71% identity and 88% query coverage in receipt sha-256 {SHA}",
        "homology evidence is available from previous work",
    )
    assert "SECTION_16_V6_EVIDENCE_OR_TERMINAL_BASIS_MISSING" in _v6_codes(card)


def test_evidence_and_alternative_must_not_collapse():
    evidence = f"measured 71% identity and 88% query coverage in receipt sha-256 {SHA}"
    card = _structured_card().replace(
        "profile bias and a different domain role remain alternative explanations", evidence
    )
    assert "SECTION_16_V6_EVIDENCE_ALTERNATIVE_COLLAPSED" in _v6_codes(card)


def test_action_and_decision_consequence_are_both_required():
    card = _structured_card().replace(
        "compare ctg1_1 against the profile panel and measure coverage and conserved-residue results",
        "do more work",
    ).replace(
        "retain the homology model only if the result preserves coverage; otherwise reject it",
        "review later",
    )
    codes = _v6_codes(card)
    assert "SECTION_16_V6_RESOLVING_ACTION_UNSPECIFIC" in codes
    assert "SECTION_16_V6_DECISION_CONSEQUENCE_MISSING" in codes


def test_structure_gate_forwards_v6_opt_in():
    codes = {row["code"] for row in lint_card(
        _card(), check_publication_quality=True,
        check_semantic_decision_chains_v6=True, canonical_loci=ROSTER,
    )}
    assert "SECTION_30_V6_SEMANTIC_DECISION_CHAIN_MISSING" in codes


def test_cli_parser_exposes_separate_v6_switch():
    args = build_parser().parse_args(["verify-modeb", "candidate.md", "--semantic-decision-chains-v6"])
    assert args.semantic_decision_chains_v6 is True
    assert args.semantic_sections_v5 is False
