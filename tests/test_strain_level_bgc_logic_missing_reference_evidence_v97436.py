"""Missing dominant-reference evidence must not be scored as a tested negative.

score_row() derives two penalties from genes_matching_dominant_reference and
total_cds. When either field is absent the numeric coercion produced 0, so a BGC
whose reference comparison never ran was penalised exactly like one that ran and
found almost nothing. A missing denominator separately inflated the hit fraction
above 1.0 and suppressed the low-fraction control.
"""
import csv
import importlib.util
from pathlib import Path

TOOL = Path(__file__).parents[1] / "tools" / "strain_level_bgc_logic.py"
spec = importlib.util.spec_from_file_location("strain_level_bgc_logic", TOOL)
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

BASE = {
    "standalone_biological_evidence_score_0_100": "62",
    "functional_reference_relation": "ARCHITECTURE_SUPPORT_PRESENT",
    "boundary": "Full-contig",
    "evidence_tier": "B_SUPPORTED_PARTIAL",
    "current_antismash_products": "NRPS;T1PKS",
    "architecture_first_pathway_type": "NRPS",
}


def test_absent_reference_evidence_is_not_scored_as_a_tested_negative():
    tested = mod.score_row(dict(BASE, genes_matching_dominant_reference="0", total_cds="40"))
    missing = mod.score_row(dict(BASE))
    assert "SPARSE_REFERENCE_GENE_SUPPORT" in tested[2]
    assert "LOW_REFERENCE_HIT_FRACTION" in tested[2]
    # The row that was never evaluated must not inherit either penalty.
    assert "SPARSE_REFERENCE_GENE_SUPPORT" not in missing[2]
    assert "LOW_REFERENCE_HIT_FRACTION" not in missing[2]
    assert missing[0] > tested[0]


def test_empty_reference_cells_behave_like_absent_not_like_zero():
    empty = mod.score_row(dict(BASE, genes_matching_dominant_reference="", total_cds=""))
    assert "SPARSE_REFERENCE_GENE_SUPPORT" not in empty[2]
    assert "REFERENCE_NOT_EVALUATED" in empty[2]


def test_unevaluated_row_is_labelled_rather_than_silently_passed():
    flag = mod.score_row(dict(BASE))[2]
    assert "REFERENCE_NOT_EVALUATED" in flag


def test_missing_denominator_does_not_inflate_the_hit_fraction():
    real = mod.score_row(dict(BASE, genes_matching_dominant_reference="5", total_cds="60"))
    lost = mod.score_row(dict(BASE, genes_matching_dominant_reference="5"))
    assert abs(real[3] - 5 / 60) < 1e-9
    assert "LOW_REFERENCE_HIT_FRACTION" in real[2]
    # Without a denominator there is no fraction to report, and none may be invented.
    assert lost[3] is None
    assert "REFERENCE_DENOMINATOR_MISSING" in lost[2]


def test_evidence_state_helper_separates_the_four_situations():
    assert mod.reference_evidence_state({"genes_matching_dominant_reference": "3", "total_cds": "9"}) == "REFERENCE_EVALUATED"
    assert mod.reference_evidence_state({"genes_matching_dominant_reference": "3"}) == "REFERENCE_DENOMINATOR_MISSING"
    assert mod.reference_evidence_state({"total_cds": "9"}) == "REFERENCE_SUPPORT_NOT_EVALUATED"
    assert mod.reference_evidence_state({}) == "REFERENCE_NOT_EVALUATED"


def test_build_emits_the_state_column_without_crashing_on_a_missing_denominator(tmp_path):
    identity = "AS-X / NODE_1_length_50000_cov_10 / region001 / BGC001"
    row = {
        "complete_identity": identity, "standalone_biological_evidence_score_0_100": "70",
        "functional_reference_relation": "ARCHITECTURE_SUPPORT_PRESENT", "boundary": "Full-contig",
        "evidence_tier": "B_SUPPORTED_PARTIAL", "genes_matching_dominant_reference": "5",
        "total_cds": "", "current_antismash_products": "NRPS;T1PKS",
        "architecture_first_pathway_type": "NRPS", "architecture_first_confidence": "HIGH",
        "dominant_mibig_product": "example", "functional_genes_without_any_mibig_match": "1",
        "functional_logic_summary": "logic", "rggmci_confidence": "", "rggmci_partner_identity": "",
        "decisive_review_question": "question", "definitive_rank_within_strain": "1",
    }
    src = tmp_path / "bgc.tsv"
    with src.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row), delimiter="\t"); w.writeheader(); w.writerow(row)
    mod.build(src, tmp_path / "out")
    text = (tmp_path / "out" / "ALL_BGC_STRAIN_PRODUCT_LOGIC.tsv").read_text()
    assert "strain_logic_reference_evidence_state" in text
    assert "REFERENCE_DENOMINATOR_MISSING" in text


def test_no_reference_selected_is_not_charged_for_sparse_reference_support():
    """The live path: the workup emits these relations with a necessarily-zero
    match count because no dominant reference was selected at all."""
    compared = mod.score_row(dict(BASE, functional_reference_relation="ARCHITECTURE_SUPPORT_PRESENT",
                                  genes_matching_dominant_reference="0", total_cds="40"))
    none_sel = mod.score_row(dict(BASE, functional_reference_relation="ARCHITECTURE_ONLY_NO_REFERENCE_MATCH",
                                  genes_matching_dominant_reference="0", total_cds="40"))
    assert "SPARSE_REFERENCE_GENE_SUPPORT" in compared[2]
    assert "SPARSE_REFERENCE_GENE_SUPPORT" not in none_sel[2]
    assert "LOW_REFERENCE_HIT_FRACTION" not in none_sel[2]
    assert "NO_REFERENCE_SELECTED" in none_sel[2]


def test_both_channels_unresolved_is_not_double_charged():
    row = dict(BASE, functional_reference_relation="BOTH_CHANNELS_UNRESOLVED",
               genes_matching_dominant_reference="0", total_cds="40")
    flag = mod.score_row(row)[2]
    # RELATION_MODIFIERS already prices this state at -15; the fragment controls
    # must not charge a second time for the same absence.
    assert "SPARSE_REFERENCE_GENE_SUPPORT" not in flag
    assert "NO_REFERENCE_SELECTED" in flag
