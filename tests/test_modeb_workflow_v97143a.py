"""v9.7.143a Mode B workflow regression tests.

These tests encode the AS-705 lessons:
- AA lengths are mandatory.
- Huge SDR-labelled proteins need a large-protein override.
- NODE_24/NODE_30 triggers NPDC041969 comparator workflow.
- NODE_58 must not collapse into the NPDC041969 model.
"""
from __future__ import annotations

import pytest
pd = pytest.importorskip('pandas')

from mamey.mode_b.schema import normalize_modeb_gene_table, validate_modeb_gene_table
from mamey.mode_b.guards import large_protein_misannotation_warning
from mamey.mode_b.comparator_workflow import detect_comparator_workflows, render_comparator_workflow_card
from mamey.mode_b.claim_safety import classify_split_composite_status, claim_safety_note


def _as705_rows():
    return [
        {"node":"NODE_24","locus":"ctg24_2","query_length":4548,"hit_accession":"WP_469452610","hit_title":"SDR family NAD(P)-dependent oxidoreductase","hit_species":"Streptomyces sp. NPDC041969","percent_identity":74.4,"percent_similarity":80.2,"query_coverage_pct":100.0,"functional_call":"very large SDR-labelled PKS/transAT-like module","modeb_role":"core"},
        {"node":"NODE_24","locus":"ctg24_3","query_length":275,"hit_accession":"WP_469452608","hit_title":"ACP S-malonyltransferase","hit_species":"Streptomyces sp. NPDC041969","percent_identity":82.1,"percent_similarity":89.7,"query_coverage_pct":99.3,"functional_call":"AT-like PKS component","modeb_role":"auxiliary"},
        {"node":"NODE_30","locus":"ctg30_12","query_length":267,"hit_accession":"WP_469452626","hit_title":"ABC transporter permease subunit","hit_species":"Streptomyces sp. NPDC041969","percent_identity":80.9,"percent_similarity":91.8,"query_coverage_pct":100.0,"functional_call":"export context","modeb_role":"export"},
        {"node":"NODE_30","locus":"ctg30_19","query_length":4840,"hit_accession":"WP_469452616","hit_title":"SDR family NAD(P)-dependent oxidoreductase","hit_species":"Streptomyces sp. NPDC041969","percent_identity":72.5,"percent_similarity":78.7,"query_coverage_pct":82.7,"functional_call":"large SDR-labelled module","modeb_role":"large module"},
        {"node":"NODE_58","locus":"ctg58_2","query_length":3619,"hit_accession":"NA","hit_title":"SDR family NAD(P)-dependent oxidoreductase","hit_species":"Streptomyces cinnamoneus","percent_identity":75.3,"percent_similarity":82.3,"query_coverage_pct":99.8,"functional_call":"reductive modular PKS-like protein","modeb_role":"core modular PKS"},
    ]


def test_modeb_schema_normalizes_query_length_to_protein_length():
    df = normalize_modeb_gene_table(pd.DataFrame(_as705_rows()))
    assert "protein_length_aa" in df.columns
    assert int(df.loc[df["locus"] == "ctg24_2", "protein_length_aa"].iloc[0]) == 4548
    assert int(df.loc[df["locus"] == "ctg30_19", "protein_length_aa"].iloc[0]) == 4840
    validate_modeb_gene_table(df)


def test_modeb_schema_fails_without_any_length_column():
    df = pd.DataFrame([{"node":"NODE_X","locus":"x1"}])
    with pytest.raises(ValueError, match="protein length"):
        normalize_modeb_gene_table(df)


def test_npdc041969_comparator_workflow_triggers():
    df = normalize_modeb_gene_table(pd.DataFrame(_as705_rows()))
    workflows = detect_comparator_workflows(df)
    comparators = {w["comparator"] for w in workflows}
    assert "Streptomyces sp. NPDC041969" in comparators
    workflow = next(w for w in workflows if w["comparator"] == "Streptomyces sp. NPDC041969")
    assert "NODE_24" in workflow["nodes"]
    assert "NODE_30" in workflow["nodes"]
    assert workflow["external_antismash_needed"] is True
    assert "antiSMASH" in workflow["user_action"]
    card = render_comparator_workflow_card(workflow)
    assert "Comparator next step detected" in card
    assert "antiSMASH" in card


def test_large_protein_misannotation_guard_triggers():
    df = normalize_modeb_gene_table(pd.DataFrame(_as705_rows()))
    by_locus = {r["locus"]: r for r in df.to_dict("records")}
    for locus in ["ctg24_2", "ctg30_19", "ctg58_2"]:
        warning = large_protein_misannotation_warning(by_locus[locus])
        assert "Large-protein override" in warning


def test_node58_do_not_merge_with_npdc041969_axis():
    label = classify_split_composite_status({"different_comparator_axis": True})
    assert label == "do_not_merge"
    assert "keep as separate" in claim_safety_note(label)


def test_candidate_split_claim_safety_label():
    label = classify_split_composite_status({"shared_comparator": True, "multiple_contigs": True})
    assert label == "candidate_split_BGC"
    assert "do not claim confirmed contiguity" in claim_safety_note(label)
