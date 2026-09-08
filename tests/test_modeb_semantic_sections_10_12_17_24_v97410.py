from mamey.modeb_publication_gate import publication_quality_findings
from tests.test_modeb_publication_quality_v9_7_372 import _card


SHA = "a" * 64
ROSTER = {"ctg1_1"}


def _replace(card: str, section: int, body: str) -> str:
    marker = f"## §{section} Section {section}\n"
    start = card.index(marker) + len(marker)
    next_marker = f"## §{section + 1} Section {section + 1}\n"
    end = card.index(next_marker, start)
    return card[:start] + body.strip() + "\n\n" + card[end:]


def _structured_card() -> str:
    card = _card()
    card = _replace(card, 10, """
#### Boundary and co-capture adjudication
| Observed geometry | Competing boundary or co-capture model | Evidence for | Evidence against | Interpretation consequence | Discriminating closure test |
|---|---|---|---|---|---|
| interior interval around ctg1_1 | adjacent accessory locus is co-captured | antiSMASH interval and sealed coordinates | no read-backed operon boundary | retain one provisional locus without pathway-completion claim | long-read closure plus ctg1_1-dependent metabolomics |
""")
    card = _replace(card, 12, """
#### Ecological hypothesis matrix
| Ecological hypothesis | Locus-specific evidence | Evidence against | Competing explanation | Causality ceiling | Matched discriminating test |
|---|---|---|---|---|---|
| chemical competition | ctg1_1 exact-region biosynthetic role | no phenotype measured | nutrient acquisition | testable hypothesis only | matched wild type knockout and complement competition assay |
| nutrient acquisition | transport context beside ctg1_1 | substrate is unknown | general stress persistence | source context not BGC causality | matched isotope uptake with knockout and complement |
""")
    card = _replace(card, 17, """
#### LC-MS / fermentation decision matrix
| Exact in-roster target | Condition rationale | Perturbation | Control | Measured readout | Decision rule | Claim ceiling |
|---|---|---|---|---|---|---|
| ctg1_1 | predicted biosynthetic core may control one feature | clean ctg1_1 deletion | wild type plus complemented strain and batch blanks | reproducible LC-MS/MS feature with retention-time and MS2 parity | advance only if deletion removes and complementation restores the same feature | locus-linked feature, not named structure or activity |
""")
    card = _replace(card, 24, f"""
#### Novelty evidence ledger
| Reference space | Source receipt SHA-256 | Denominator | Measured result | Counterevidence or limitation | Allowed inference | Resolving next action |
|---|---|---|---|---|---|---|
| MIBiG plus qualified BiG-SCAPE run | {SHA} | 2,400 reference BGCs and 3 cutoffs | no close whole-locus family at strict cutoff | database incompleteness and component recurrence remain | structural distinctiveness candidate only | isolate the ctg1_1-dependent feature and compare structure against references |
""")
    return card


def _codes(card: str):
    return {row["code"] for row in publication_quality_findings(
        card, canonical_loci=ROSTER, check_semantic_sections_v3=True
    )}


def test_structured_sections_clear_new_checks():
    codes = _codes(_structured_card())
    assert not {code for code in codes if code.startswith(("SECTION_10_", "SECTION_12_", "SECTION_17_", "SECTION_24_"))}


def test_padded_generic_sections_fail():
    card = _card()
    for section in (10, 12, 17, 24):
        card = _replace(card, section, (f"Generic section {section} remains uncertain. " * 40))
    codes = _codes(card)
    assert "SECTION_10_BOUNDARY_AND_CO_CAPTURE_ADJUDICATION_MISSING" in codes
    assert "SECTION_12_ECOLOGICAL_HYPOTHESIS_MATRIX_MISSING" in codes
    assert "SECTION_17_LC_MS_FERMENTATION_DECISION_MATRIX_MISSING" in codes
    assert "SECTION_24_NOVELTY_EVIDENCE_LEDGER_MISSING" in codes


def test_section12_requires_two_models():
    card = _structured_card().replace(
        "| nutrient acquisition | transport context beside ctg1_1 | substrate is unknown | general stress persistence | source context not BGC causality | matched isotope uptake with knockout and complement |\n",
        "",
    )
    assert "SECTION_12_ECOLOGICAL_HYPOTHESIS_MATRIX_THIN" in _codes(card)


def test_section17_rejects_out_of_roster_target():
    card = _structured_card().replace("| ctg1_1 | predicted biosynthetic", "| ctg9_9 | predicted biosynthetic")
    assert "SECTION_17_TARGET_OUTSIDE_DISPLAYED_ROSTER" in _codes(card)


def test_section24_rejects_unbound_receipt_and_denominator():
    card = _structured_card().replace(SHA, "pending").replace(
        "2,400 reference BGCs and 3 cutoffs", "unknown reference space"
    )
    codes = _codes(card)
    assert "SECTION_24_SOURCE_RECEIPT_INVALID" in codes
    assert "SECTION_24_DENOMINATOR_UNMEASURED" in codes


def test_legacy_behavior_unchanged_when_v2_disabled():
    codes = {row["code"] for row in publication_quality_findings(
        _card(), canonical_loci=ROSTER, check_substantive_quality_v2=True,
        check_semantic_sections_v3=False,
    )}
    assert not {code for code in codes if code.startswith(("SECTION_10_", "SECTION_12_", "SECTION_17_", "SECTION_24_"))}


def test_filled_keyword_table_does_not_bypass_semantics():
    card = _structured_card()
    card = card.replace(
        "| interior interval around ctg1_1 | adjacent accessory locus is co-captured | antiSMASH interval and sealed coordinates | no read-backed operon boundary | retain one provisional locus without pathway-completion claim | long-read closure plus ctg1_1-dependent metabolomics |",
        "| boundary evidence | boundary evidence | same evidence | same evidence | consequence | future work |",
    )
    card = card.replace(
        "| chemical competition | ctg1_1 exact-region biosynthetic role | no phenotype measured | nutrient acquisition | testable hypothesis only | matched wild type knockout and complement competition assay |",
        "| ecology | evidence | evidence | ecology | causal | future work |",
    )
    card = card.replace(
        "| ctg1_1 | predicted biosynthetic core may control one feature | clean ctg1_1 deletion | wild type plus complemented strain and batch blanks | reproducible LC-MS/MS feature with retention-time and MS2 parity | advance only if deletion removes and complementation restores the same feature | locus-linked feature, not named structure or activity |",
        "| ctg1_1 | rationale | future perturbation | controls | readout | decision | conclusion |",
    )
    codes = _codes(card)
    assert "SECTION_10_OBSERVED_GEOMETRY_UNTYPED" in codes
    assert "SECTION_10_EVIDENCE_SIDES_COLLAPSED" in codes
    assert "SECTION_12_LOCUS_EVIDENCE_UNBOUND" in codes
    assert "SECTION_12_COMPETING_EXPLANATION_COLLAPSED" in codes
    assert "SECTION_17_PERTURBATION_TARGET_MISMATCH" in codes
    assert "SECTION_17_CONTROLS_INSUFFICIENT" in codes
    assert "SECTION_17_READOUT_UNMEASURED" in codes
    assert "SECTION_17_DECISION_RULE_MISSING" in codes
    assert "SECTION_17_CLAIM_CEILING_MISSING" in codes


def test_structure_gate_forwards_v3_opt_in():
    from mamey.modeb_structure_gate import lint_card
    codes = {row["code"] for row in lint_card(
        _card(), check_publication_quality=True,
        check_semantic_sections_v3=True, canonical_loci=ROSTER,
    )}
    assert "SECTION_10_BOUNDARY_AND_CO_CAPTURE_ADJUDICATION_MISSING" in codes


def test_cli_parser_exposes_separate_v3_switch():
    from mamey.cli import build_parser
    args = build_parser().parse_args(["verify-modeb", "candidate.md", "--semantic-sections-v3"])
    assert args.semantic_sections_v3 is True
    assert args.substantive_quality_v2 is False
