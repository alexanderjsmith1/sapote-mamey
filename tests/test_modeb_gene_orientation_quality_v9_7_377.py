from __future__ import annotations

from mamey.modeb_publication_gate import (
    _gene_orientation_findings,
    _repeated_generic_sentence_findings,
    _section27_findings,
    _section45_findings,
)


def _codes(findings: list[dict]) -> set[str]:
    return {item["code"] for item in findings}


def _s27_positive() -> str:
    return """Self-resistance candidates are evaluated gene by gene.

#### Candidate gene orientation

| Gene | Physical membership | Candidate role | Evidence source | Class concordance | Allowed inference |
|---|---|---|---|---|---|
| ctg1_1 | EXACT_REGION | APH-family resistance-like candidate | antiSMASH annotation plus BLASTp | UNRESOLVED | lead-priority context only |
| ctg1_2 | BOUNDARY_CONTEXT | ABC-family transporter candidate | Mamey transporter scan | NOT_APPLICABLE | transport context only |

#### Claim ceiling

Neither ctg1_1 nor ctg1_2 is assigned as producer self-protection without compound-linked evidence.
"""


def _s45_positive() -> str:
    return """#### Cohort comparison denominator

Two exact loci from two strains were compared after exact protein binding.

#### Cohort gene comparison

| Comparator exact locus | Query genes | Comparator genes | Sequence / synteny evidence | Agreement and mismatch | Allowed inference |
|---|---|---|---|---|---|
| AS-2 / NODE_2_length_20000_cov_20.000000 / region001 / BGC002 | ctg1_1; ctg1_2 | ctg2_1; ctg2_2 | count-first protein comparison and ordered-neighbor agreement | two genes agree; release system differs | cohort gene-family navigation only |

#### Cohort-comparison conclusion

The exact gene pair supports a related cohort cassette, not product identity.
"""


def test_section27_family_only_prose_fails_even_when_long():
    body = (
        "Self-resistance is not assigned. The APH-family and metallo-beta-lactamase-fold "
        "proteins are resistance-like candidates with unverified class concordance, and "
        "the ABC systems have unknown substrate and direction. " * 10
    )
    codes = _codes(_section27_findings(body, ["ctg1_1", "ctg1_2"]))
    assert "SECTION_27_GENE_ORIENTATION_MISSING" in codes
    assert "SECTION_27_CLAIM_CEILING_MISSING" in codes


def test_section27_exact_genes_without_orientation_table_fail():
    body = "ctg1_1 is APH-family.\n\n#### Claim ceiling\n\nSelf-resistance is not assigned."
    assert "SECTION_27_GENE_TABLE_MISSING" in _codes(
        _section27_findings(body, ["ctg1_1"])
    )


def test_section27_complete_concise_table_passes_without_word_floor():
    assert _section27_findings(_s27_positive(), ["ctg1_1", "ctg1_2"]) == []


def test_section27_typed_zero_requires_matching_denominator_and_sources():
    valid = (
        "Gene-or-typed-none state: ZERO_EXACT_BOUND_CANDIDATES; denominator=2 exact displayed "
        "proteins; sources=antiSMASH, sealed Mamey, BLASTp.\n\n"
        "#### Claim ceiling\n\nNo self-resistance determinant is assigned."
    )
    assert _section27_findings(valid, ["ctg1_1", "ctg1_2"]) == []
    invalid = valid.replace("denominator=2", "denominator=3")
    assert "SECTION_27_GENE_ORIENTATION_MISSING" in _codes(
        _section27_findings(invalid, ["ctg1_1", "ctg1_2"])
    )


def test_section27_rejects_candidate_gene_outside_external_roster():
    body = _s27_positive().replace("ctg1_2", "ctg9_9")
    assert "SECTION_27_GENE_OUTSIDE_DISPLAYED_ROSTER" in _codes(
        _section27_findings(body, ["ctg1_1", "ctg1_2"])
    )


def test_general_gene_claim_section_requires_gene_or_typed_none():
    findings = _gene_orientation_findings(
        {8: "An APH-family protein and ABC transporter are candidate context."},
        ["ctg1_1"],
    )
    assert "SECTION_GENE_ORIENTATION_MISSING" in _codes(findings)
    assert _gene_orientation_findings(
        {8: "ctg1_1 is an APH-family candidate; class concordance is unresolved."},
        ["ctg1_1"],
    ) == []


def test_section45_predecessor_bookkeeping_is_not_cohort_comparison():
    body = (
        "Historical evidence was preserved and predecessor hashes were registered. "
        "The prior card remains the prose authority."
    )
    codes = _codes(_section45_findings(body, ["ctg1_1"]))
    assert "SECTION_45_COHORT_DENOMINATOR_MISSING" in codes
    assert "SECTION_45_COMPARATOR_TABLE_MISSING" in codes
    assert "SECTION_45_CONCLUSION_MISSING" in codes


def test_section45_complete_gene_comparison_passes():
    assert _section45_findings(_s45_positive(), ["ctg1_1", "ctg1_2"]) == []


def test_section45_typed_unavailable_requires_denominator_source_reason_and_conclusion():
    body = """#### Cohort comparison denominator

COHORT_COMPARISON_NOT_AVAILABLE_TYPED; denominator=42 strains / 1652 exact loci; sources=cohort protein index; reason=no exact protein-neighborhood crosswalk was available.

#### Cohort-comparison conclusion

No cohort similarity result is reported; missing comparison evidence is not biological absence.
"""
    assert _section45_findings(body, ["ctg1_1"]) == []


def test_repeated_generic_sentence_fails_but_evidence_specific_sentences_do_not():
    generic = "This evidence does not change the overall interpretation and remains appropriately bounded."
    findings = _repeated_generic_sentence_findings({1: generic, 2: generic, 3: generic})
    assert "REPEATED_GENERIC_SENTENCE" in _codes(findings)
    assert _repeated_generic_sentence_findings({
        1: "ctg1_1 has antiSMASH domain evidence.",
        2: "ctg1_2 has MIBiG navigation evidence.",
        3: "ctg1_3 has BLAST count-first evidence.",
    }) == []
    assert _repeated_generic_sentence_findings({
        1: "Both external flanks are unavailable.",
        10: "Both external flanks are unavailable.",
        36: "Both external flanks are unavailable.",
        48: "Both external flanks are unavailable.",
    }) == []
