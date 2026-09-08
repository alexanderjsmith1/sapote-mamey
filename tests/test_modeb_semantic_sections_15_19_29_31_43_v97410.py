from __future__ import annotations

from mamey.cli import build_parser
from mamey.modeb_publication_gate import publication_quality_findings
from mamey.modeb_structure_gate import lint_card
from tests.test_modeb_publication_quality_v9_7_372 import _card


SHA = "a" * 64
ROSTER = {"ctg1_1"}
TARGET_PREFIXES = tuple(f"SECTION_{number}_" for number in (15, 19, 29, 31, 43))
ACTION = "delete ctg1_1 with complementation"


def _replace(card: str, section: int, body: str) -> str:
    marker = f"## §{section} Section {section}\n"
    start = card.index(marker) + len(marker)
    next_marker = f"## §{section + 1} Section {section + 1}\n"
    end = card.index(next_marker, start)
    return card[:start] + body.strip() + "\n\n" + card[end:]


def _section15() -> str:
    return f"""
#### Missing-evidence ledger
| Missing evidence object | Source / state receipt SHA-256 | Typed state | Why missing | Affected inference | Resolving acquisition | Decision rule |
|---|---|---|---|---|---|---|
| read-backed boundary coverage for ctg1_1 | {SHA} | NOT_RUN | no long-read library was included in the sealed source package | locus completeness remains unresolved and cannot support a complete-pathway claim | sequence the locus with long reads and measure coverage across both predicted boundaries | retain the complete-boundary model only if spanning reads support both edges |
"""


def _section19(action: str = ACTION) -> str:
    return f"""
#### Final decision record
| Final disposition | Strongest supporting evidence | Strongest conflict or alternative | Boundary / completeness state | Claim ceiling | Linked highest-information action |
|---|---|---|---|---|---|
| HOLD_EVIDENCE | antiSMASH domains and the exact ctg1_1 roster support a biosynthetic candidate | missing BLAST coverage and an alternative primary-metabolism role conflict with assignment | interior interval observed but boundary completeness remains unresolved | candidate interpretation only; product identity and activity remain unknown | {action} |
"""


def _section29() -> str:
    return """
#### Cross-cluster interaction adjudication
| Partner exact locus | Interaction mechanism | Evidence for | Evidence against | Physical-link state | Allowed inference | Discriminating test |
|---|---|---|---|---|---|---|
| AS-2 / NODE_2_length_20000_cov_20.000000 / region001 / BGC002 | trans-acting maturation of the ctg1_1 precursor | complementary maturation domains and a shared precursor-class prediction support functional coupling | different contigs and no matched expression evidence support independent pathways | NO_PHYSICAL_LINK | functional-coupling hypothesis only; pathway interaction remains unresolved | delete the partner maturation gene with complementation and measure the ctg1_1-dependent LC-MS feature readout |
"""


def _section31(displayed: str = "ctg1_1") -> str:
    return f"""
#### Region CDS census reconciliation
| Canonical roster SHA-256 | Exact-region genes | Boundary-context genes | Displayed genes | Missing from displayed roster | Extra beyond canonical roster | Reconciliation state |
|---|---|---|---|---|---|---|
| {SHA} | ctg1_1 | NONE | {displayed} | NONE | NONE | EXACT_MATCH |
"""


def _section43(*, total: int = 0, partner: str = "MEASURED_ZERO_PARTNERS") -> str:
    return f"""
#### RG-GMCI accounting
| RG-GMCI run receipt SHA-256 | Pair denominator | HIGH count | MODERATE count | LOW count | Two-proof rescue rows |
|---|---|---|---|---|---|
| {SHA} | {total} | 0 | 0 | {total} | 0 |

#### Split-pathway adjudication
| Partner exact locus or measured-zero state | Functional-coupling evidence | Physical-link evidence | Distinct alternative | Allowed inference | Resolving action |
|---|---|---|---|---|---|
| {partner} | no complementary domain pair was observed across the measured candidate set | no cross-contig pair passed the physical-link evidence rules in the bound run | an independent single-locus pathway remains the distinct retained model | split-pathway coupling is not supported and remains unresolved | compare a newly sequenced complete assembly and measure whether any pair meets both rescue proofs |
"""


def _structured_card() -> str:
    card = _card()
    for section, body in (
        (15, _section15()), (19, _section19()), (29, _section29()),
        (31, _section31()), (43, _section43()),
    ):
        card = _replace(card, section, body)
    return card


def _codes(card: str, *, enabled: bool = True, roster=ROSTER) -> set[str]:
    return {finding["code"] for finding in publication_quality_findings(
        card, canonical_loci=roster, check_semantic_sections_v5=enabled,
    )}


def _target_codes(card: str, **kwargs) -> set[str]:
    return {code for code in _codes(card, **kwargs) if code.startswith(TARGET_PREFIXES)}


def test_structured_sections_clear_v5_checks():
    assert _target_codes(_structured_card()) == set()


def test_v5_is_separate_opt_in():
    assert _target_codes(_card(), enabled=False) == set()
    codes = _target_codes(_card())
    assert "SECTION_15_MISSING_EVIDENCE_LEDGER_MISSING" in codes
    assert "SECTION_19_FINAL_DECISION_RECORD_MISSING" in codes
    assert "SECTION_29_CROSS_CLUSTER_INTERACTION_ADJUDICATION_MISSING" in codes
    assert "SECTION_31_REGION_CDS_CENSUS_RECONCILIATION_MISSING" in codes
    assert "SECTION_43_RG_GMCI_ACCOUNTING_MISSING" in codes


def test_long_cautious_semantic_displacement_bypass_is_closed():
    card = _card()
    wrong = "The evidence remains uncertain and no product identity or activity is claimed. " * 30
    for section in (15, 19, 29, 31, 43):
        card = _replace(card, section, wrong)
    assert _target_codes(card, enabled=False) == set()
    assert len(_target_codes(card)) >= 5


def test_filled_keyword_tables_do_not_bypass_v5():
    card = _structured_card()
    card = card.replace("read-backed boundary coverage for ctg1_1", "evidence present")
    card = card.replace("antiSMASH domains and the exact ctg1_1 roster support a biosynthetic candidate", "evidence present")
    card = card.replace("trans-acting maturation of the ctg1_1 precursor", "interaction present")
    card = card.replace("no complementary domain pair was observed across the measured candidate set", "evidence present")
    codes = _target_codes(card)
    assert "SECTION_15_MISSING_OBJECT_UNTYPED" in codes
    assert "SECTION_19_SUPPORT_UNSUBSTANTIVE" in codes
    assert "SECTION_29_INTERACTION_MECHANISM_UNTYPED" in codes
    assert "SECTION_43_LINK_EVIDENCE_UNSUBSTANTIVE" in codes


def test_section15_requires_receipt_typed_state_and_decision_bearing_acquisition():
    card = _structured_card().replace(SHA, "pending", 1).replace(
        "NOT_RUN", "UNKNOWN", 1).replace(
        "sequence the locus with long reads and measure coverage across both predicted boundaries",
        "do more work",
    )
    codes = _target_codes(card)
    assert "SECTION_15_SOURCE_STATE_RECEIPT_INVALID" in codes
    assert "SECTION_15_STATE_UNTYPED" in codes
    assert "SECTION_15_RESOLVING_ACQUISITION_UNSPECIFIC" in codes


def test_section19_requires_opposed_sources_and_exact_section20_link():
    support = "antiSMASH domains and the exact ctg1_1 roster support a biosynthetic candidate"
    bad_section = _section19("sequence the locus again").replace(
        "missing BLAST coverage and an alternative primary-metabolism role conflict with assignment",
        support,
    )
    card = _replace(_structured_card(), 19, bad_section)
    codes = _target_codes(card)
    assert "SECTION_19_SUPPORT_CONFLICT_COLLAPSED" in codes
    assert "SECTION_19_ACTION_NOT_LINKED_TO_SECTION_20" in codes


def test_section29_requires_complete_partner_identity_and_measured_test():
    card = _structured_card().replace(
        "AS-2 / NODE_2_length_20000_cov_20.000000 / region001 / BGC002",
        "AS-2 / BGC002",
    ).replace(
        "delete the partner maturation gene with complementation and measure the ctg1_1-dependent LC-MS feature readout",
        "future work",
    )
    codes = _target_codes(card)
    assert "SECTION_29_PARTNER_IDENTITY_INCOMPLETE" in codes
    assert "SECTION_29_DISCRIMINATING_TEST_UNSPECIFIC" in codes


def test_section31_requires_hash_bound_exact_external_roster_equality():
    card = _structured_card().replace(SHA, "unbound", 1)
    codes = _target_codes(card)
    assert "SECTION_31_ROSTER_RECEIPT_INVALID" not in codes  # first SHA belongs to section 15
    card = _replace(card, 31, _section31("ctg1_1, ctg1_2").replace(SHA, "unbound"))
    codes = _target_codes(card)
    assert "SECTION_31_ROSTER_RECEIPT_INVALID" in codes
    assert "SECTION_31_INTERNAL_CENSUS_MISMATCH" in codes
    assert "SECTION_31_DISPLAYED_ROSTER_MISMATCH" in codes


def test_section31_refuses_certification_without_external_roster():
    assert "SECTION_31_CANONICAL_ROSTER_UNBOUND" in _target_codes(
        _structured_card(), roster=None)


def test_section43_requires_valid_arithmetic_identity_and_receipt():
    section = _section43(
        total=2,
        partner="AS-2 / NODE_2_length_20000_cov_20.000000 / region001 / BGC002",
    ).replace("| 2 | 0 | 0 | 2 | 0 |", "| 2 | 1 | 1 | 1 | 3 |").replace(SHA, "pending")
    codes = _target_codes(_replace(_structured_card(), 43, section))
    assert "SECTION_43_RUN_RECEIPT_INVALID" in codes
    assert "SECTION_43_CONFIDENCE_COUNTS_MISMATCH" in codes
    assert "SECTION_43_RESCUE_COUNT_EXCEEDS_PAIRS" in codes


def test_section43_nonzero_partner_requires_complete_identity():
    card = _replace(_structured_card(), 43, _section43(total=1, partner="BGC002"))
    assert "SECTION_43_PARTNER_IDENTITY_INCOMPLETE" in _target_codes(card)


def test_reasoned_section29_terminal_and_measured_zero_section43_pass():
    terminal = (
        "CROSS_CLUSTER_INTERACTION_NOT_EVALUABLE_TYPED; denominator=0 candidate partners; "
        "sources=sealed package and bound analysis receipt; reason=no complete partner identity "
        "with functional evidence was admitted; resolving_test=sequence the complete assembly "
        "and measure whether a partner shares synteny and a matched LC-MS feature readout"
    )
    card = _replace(_structured_card(), 29, terminal)
    assert _target_codes(card) == set()


def test_structure_gate_forwards_v5_opt_in():
    codes = {finding["code"] for finding in lint_card(
        _card(), check_publication_quality=True,
        check_semantic_sections_v5=True, canonical_loci=ROSTER,
    )}
    assert "SECTION_31_REGION_CDS_CENSUS_RECONCILIATION_MISSING" in codes


def test_cli_parser_exposes_separate_v5_switch():
    args = build_parser().parse_args(["verify-modeb", "candidate.md", "--semantic-sections-v5"])
    assert args.semantic_sections_v5 is True
    assert args.semantic_sections_v3 is False
    assert args.semantic_comparators_v4 is False
