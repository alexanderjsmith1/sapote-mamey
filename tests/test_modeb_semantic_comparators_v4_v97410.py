from __future__ import annotations

import importlib.util
from pathlib import Path

from mamey.cli import build_parser
from mamey.modeb_publication_gate import publication_quality_findings
from mamey.modeb_structure_gate import lint_card


ROSTER = ["ctg1_1"]
HERE = Path(__file__).resolve().parent


def _base_card() -> str:
    path = HERE / "test_modeb_publication_quality_v9_7_372.py"
    spec = importlib.util.spec_from_file_location("modeb_v4_base_fixture", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._card()


def _replace(card: str, section: int, body: str) -> str:
    marker = f"## §{section} Section {section}\n"
    next_marker = f"## §{section + 1} Section {section + 1}\n"
    start = card.index(marker) + len(marker)
    end = card.index(next_marker, start)
    return card[:start] + body.rstrip() + "\n\n" + card[end:]


def _section6() -> str:
    anchors = (
        "Direct tailoring candidates", "Broad metabolic context", "Conditional pathway order",
        "Non-diagnostic enzyme families", "Comparator conflicts", "Coupling evidence",
        "Discriminating tests",
    )
    text = []
    for anchor in anchors:
        text.extend([f"#### {anchor}", "The exact ctg1_1 evidence is adjudicated below."])
    text.extend([
        "#### Tailoring and maturation adjudication",
        "| Exact in-roster gene | Candidate reaction | Evidence for | Evidence against | Pathway-order or coupling evidence | Distinct alternative role | Allowed inference | Discriminating test |",
        "|---|---|---|---|---|---|---|---|",
        "| ctg1_1 | candidate O-methyl transfer after precursor cleavage | antiSMASH domain and BLAST 72% identity support a methyltransferase-family protein | the catalytic motif differs at two conserved residues and product evidence is absent | ctg1_1 is adjacent within 800 bp and preserves candidate pathway order | primary-metabolism methyltransferase acting on a housekeeping metabolite | supports only a tailoring candidate and does not establish product identity or activity | delete ctg1_1 with a complemented control and compare the LC-MS feature readout |",
    ])
    return "\n".join(text)


def _section45() -> str:
    return "\n".join([
        "#### Cohort comparison denominator",
        "Two exact loci from two strains were compared.",
        "#### Cohort gene comparison",
        "| Comparator exact locus | Query genes | Comparator genes | Sequence / synteny evidence | Agreement and mismatch | Allowed inference |",
        "|---|---|---|---|---|---|",
        "| AS-2 / NODE_2_length_20000_cov_20.000000 / region001 / BGC002 | ctg1_1 | ctg2_1 | 82% identity over 205/240 aa with shared three-gene order | shared core order agrees but two accessory genes differ | supports only cohort navigation and does not establish product identity |",
        "#### Cohort-comparison conclusion",
        "The measured match supports only cohort navigation and does not establish production or activity.",
        "#### Discriminating next comparison",
        "Align both complete canonical rosters and measure whether bidirectional ortholog order supports or rejects whole-locus conservation.",
    ])


def _section46() -> str:
    return "\n".join([
        "#### Type/reference comparison denominator",
        "One profile-compatible exact reference locus was compared.",
        "#### Type/reference gene comparison",
        "| Comparator exact locus | Query genes | Comparator genes | Profile compatibility | Divergence | Allowed inference |",
        "|---|---|---|---|---|---|",
        "| Reference strain / REF_CONTIG_1 / region001 / BGC002 | ctg1_1 | ref_0001 | 3/4 core domains match the antiSMASH profile at the reference locus | two accessory genes differ and the release enzyme is absent | supports only profile-level navigation and does not establish product identity |",
        "#### Type/reference comparison conclusion",
        "The measured profile supports only a comparator hypothesis and does not establish activity or structure.",
        "#### Discriminating next comparison",
        "Compare the complete domain order and measure bidirectional sequence coverage before retaining the reference model.",
    ])


def _section47() -> str:
    return "\n".join([
        "#### Host-matched comparison denominator",
        "One unrelated host-matched reference locus was compared.",
        "#### Host-matched gene comparison",
        "| Comparator exact locus | Verified host metadata | Query genes | Comparator genes | Comparator rationale | Sequence / synteny evidence | Transfer limits | Allowed inference |",
        "|---|---|---|---|---|---|---|---|",
        "| Unrelated strain / REF_CONTIG_2 / region001 / BGC003 | receipt sha-256 ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff | ctg1_1 | hostref_0001 | verified shared host niche but unrelated taxonomic lineage | 68% identity over 170/250 aa with a three-gene order mismatch | shared host does not transfer gene function or ecological activity | supports only host-context navigation and does not establish product or activity |",
        "#### Host-matched comparison conclusion",
        "The host match supports only contextual comparison and does not establish ecological function.",
        "#### Discriminating next comparison",
        "Compare matched non-host controls and measure whether whole-roster synteny distinguishes host association from lineage effects.",
    ])


def _structured_card() -> str:
    card = _base_card()
    for section, body in ((6, _section6()), (45, _section45()), (46, _section46()), (47, _section47())):
        card = _replace(card, section, body)
    return card


def _codes(card: str, *, enabled: bool = True, roster=ROSTER) -> set[str]:
    return {finding["code"] for finding in publication_quality_findings(
        card,
        canonical_loci=roster,
        check_substantive_quality_v2=True,
        check_semantic_comparators_v4=enabled,
    )}


def test_structured_semantic_comparators_v4_pass():
    assert _codes(_structured_card()) == set()


def test_v4_is_separate_opt_in_and_does_not_change_v2():
    assert _codes(_base_card(), enabled=False) == set()
    codes = _codes(_base_card(), enabled=True)
    assert "SECTION_6_TAILORING_AND_MATURATION_ADJUDICATION_MISSING" in codes
    assert "SECTION_45_DISCRIMINATING_NEXT_COMPARISON_MISSING" in codes
    assert "SECTION_46_DISCRIMINATING_NEXT_COMPARISON_MISSING" in codes
    assert "SECTION_47_DISCRIMINATING_NEXT_COMPARISON_MISSING" in codes


def test_filled_present_cells_reproduce_and_then_close_bypass():
    card = _base_card()
    section6 = _section6().replace(
        "| ctg1_1 | candidate O-methyl transfer after precursor cleavage | antiSMASH domain and BLAST 72% identity support a methyltransferase-family protein | the catalytic motif differs at two conserved residues and product evidence is absent | ctg1_1 is adjacent within 800 bp and preserves candidate pathway order | primary-metabolism methyltransferase acting on a housekeeping metabolite | supports only a tailoring candidate and does not establish product identity or activity | delete ctg1_1 with a complemented control and compare the LC-MS feature readout |",
        "| ctg1_1 | present | present | present | present | present | present | present |",
    )
    section45 = _section45().replace(
        "| AS-2 / NODE_2_length_20000_cov_20.000000 / region001 / BGC002 | ctg1_1 | ctg2_1 | 82% identity over 205/240 aa with shared three-gene order | shared core order agrees but two accessory genes differ | supports only cohort navigation and does not establish product identity |",
        "| AS-2 / NODE_2_length_20000_cov_20.000000 / region001 / BGC002 | ctg1_1 | ctg2_1 | present | present | present |",
    )
    section46 = _section46().replace(
        "| Reference strain / REF_CONTIG_1 / region001 / BGC002 | ctg1_1 | ref_0001 | 3/4 core domains match the antiSMASH profile at the reference locus | two accessory genes differ and the release enzyme is absent | supports only profile-level navigation and does not establish product identity |",
        "| Reference strain / REF_CONTIG_1 / region001 / BGC002 | ctg1_1 | ref_0001 | present | present | present |",
    )
    section47 = _section47().replace(
        "| Unrelated strain / REF_CONTIG_2 / region001 / BGC003 | receipt sha-256 ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff | ctg1_1 | hostref_0001 | verified shared host niche but unrelated taxonomic lineage | 68% identity over 170/250 aa with a three-gene order mismatch | shared host does not transfer gene function or ecological activity | supports only host-context navigation and does not establish product or activity |",
        "| Unrelated strain / REF_CONTIG_2 / region001 / BGC003 | receipt present | ctg1_1 | hostref_0001 | present | present | present | present |",
    )
    for section, body in ((6, section6), (45, section45), (46, section46), (47, section47)):
        card = _replace(card, section, body)
    assert _codes(card, enabled=False) == set()
    codes = _codes(card, enabled=True)
    assert "SECTION_6_CANDIDATE_REACTION_UNTYPED" in codes
    assert "SECTION_45_SEQUENCE_SYNTENY_UNMEASURED" in codes
    assert "SECTION_46_PROFILE_COMPATIBILITY_UNMEASURED" in codes
    assert "SECTION_47_HOST_METADATA_RECEIPT_INVALID" in codes


def test_section6_target_must_be_in_external_roster():
    card = _structured_card().replace("| ctg1_1 | candidate O-methyl", "| ctg1_99 | candidate O-methyl")
    assert "SECTION_6_TARGET_OUTSIDE_DISPLAYED_ROSTER" in _codes(card)


def test_section6_evidence_for_and_against_must_differ():
    card = _structured_card()
    evidence = "antiSMASH domain and BLAST 72% identity support a methyltransferase-family protein"
    card = card.replace("the catalytic motif differs at two conserved residues and product evidence is absent", evidence)
    assert "SECTION_6_EVIDENCE_SIDES_COLLAPSED" in _codes(card)


def test_section45_requires_measured_comparison_and_opposed_result():
    card = _structured_card().replace(
        "82% identity over 205/240 aa with shared three-gene order", "sequence evidence is available"
    ).replace(
        "shared core order agrees but two accessory genes differ", "the core order agrees across both loci"
    )
    codes = _codes(card)
    assert "SECTION_45_SEQUENCE_SYNTENY_UNMEASURED" in codes
    assert "SECTION_45_AGREEMENT_MISMATCH_NOT_OPPOSED" in codes


def test_section46_requires_concrete_divergence():
    card = _structured_card().replace(
        "two accessory genes differ and the release enzyme is absent", "divergence evidence is present"
    )
    assert "SECTION_46_DIVERGENCE_UNTYPED" in _codes(card)


def test_section47_requires_hash_bound_host_metadata():
    card = _structured_card().replace(
        "receipt sha-256 ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff", "receipt present"
    )
    assert "SECTION_47_HOST_METADATA_RECEIPT_INVALID" in _codes(card)


def test_reasoned_terminal_shapes_pass_v4():
    card = _structured_card()
    section6 = "\n".join([
        "#### Direct tailoring candidates", "No exact tailoring role is assigned.",
        "#### Broad metabolic context", "Broad metabolism remains an alternative.",
        "#### Conditional pathway order", "Pathway order is unresolved.",
        "#### Non-diagnostic enzyme families", "The enzyme family is non-diagnostic.",
        "#### Comparator conflicts", "Comparator evidence conflicts.",
        "#### Coupling evidence", "Physical coupling is not established.",
        "#### Discriminating tests", "A matched perturbation is required.",
        "ZERO_EXACT_BOUND_CANDIDATES; denominator=1 exact displayed protein; sources=sealed package and channel receipt",
        "TAILORING_NOT_ASSIGNABLE_TYPED; denominator=1 displayed protein; sources=sealed package and channel receipt; reason=no candidate reaction has opposed locus-specific evidence in the bound sources; resolving_test=sequence the complete locus and measure a matched LC-MS perturbation readout",
    ])
    section45 = "\n".join([
        "#### Cohort comparison denominator", "No exact cohort comparator is admitted.",
        "ZERO_EXACT_BOUND_CANDIDATES; denominator=1 exact displayed protein; sources=bound cohort receipt",
        "COHORT_COMPARISON_NOT_AVAILABLE_TYPED; denominator=0 exact loci; sources=bound cohort receipt; reason=no comparator has complete identity and sequence evidence",
        "#### Cohort-comparison conclusion", "The unavailable comparator evidence does not support a cohort inference.",
        "#### Discriminating next comparison", "Bind one exact cohort comparator and measure sequence coverage before retaining or rejecting cohort recurrence.",
    ])
    section46 = "\n".join([
        "ZERO_EXACT_BOUND_CANDIDATES; denominator=1 exact displayed protein; sources=bound reference receipt",
        "TYPE_REFERENCE_COMPARISON_NOT_AVAILABLE_TYPED; denominator=0 exact loci; sources=bound reference receipt; reason=no profile-compatible exact reference is admitted",
        "#### Type/reference comparison conclusion", "The unavailable comparator evidence does not support a reference inference.",
        "#### Discriminating next comparison", "Bind one exact reference roster and compare domain order before retaining or rejecting profile compatibility.",
    ])
    section47 = "\n".join([
        "HOST_MATCHED_COMPARISON_NOT_AVAILABLE_TYPED; denominator=0 exact loci; sources=bound host metadata receipt; reason=no unrelated comparator has verified matching host metadata",
        "#### Host-matched comparison conclusion", "The unavailable comparator evidence does not support a host-context inference.",
        "#### Discriminating next comparison", "Bind one exact unrelated host comparator and measure whole-roster synteny against matched non-host controls.",
    ])
    for section, body in ((6, section6), (45, section45), (46, section46), (47, section47)):
        card = _replace(card, section, body)
    assert _codes(card) == set()


def test_cli_exposes_separate_v4_switch():
    args = build_parser().parse_args(["verify-modeb", "candidate.md", "--semantic-comparators-v4"])
    assert args.semantic_comparators_v4 is True


def test_lint_card_propagates_v4_to_publication_gate():
    codes = {finding["code"] for finding in lint_card(
        _base_card(),
        check_publication_quality=True,
        check_substantive_quality_v2=True,
        check_semantic_comparators_v4=True,
        canonical_loci=ROSTER,
    )}
    assert "SECTION_6_TAILORING_AND_MATURATION_ADJUDICATION_MISSING" in codes
    assert "SECTION_45_DISCRIMINATING_NEXT_COMPARISON_MISSING" in codes
