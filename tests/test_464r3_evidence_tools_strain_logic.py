"""Strain-level reports: a blank homology subject is not a no-match, the gene cap is stated,
and a rerun never mixes with an old folder."""
import csv
import importlib.util
from pathlib import Path
import pytest

TOOL = Path(__file__).parents[1] / "tools" / "strain_level_bgc_logic.py"
spec = importlib.util.spec_from_file_location("strain_level_bgc_logic_464r3", TOOL)
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
IDENTITY = "EXAMPLE / CTG_A / region001 / BGC001"
ROW = {"complete_identity": IDENTITY, "standalone_biological_evidence_score_0_100": "70",
       "functional_reference_relation": "ARCHITECTURE_CORROBORATES_REFERENCE", "boundary": "Interior",
       "evidence_tier": "A", "genes_matching_dominant_reference": "5", "total_cds": "30",
       "current_antismash_products": "RiPP", "architecture_first_pathway_type": "lanthipeptide RiPP",
       "architecture_first_confidence": "HIGH", "dominant_mibig_product": "example",
       "functional_genes_without_any_mibig_match": "25", "functional_logic_summary": "logic",
       "rggmci_confidence": "", "rggmci_partner_identity": "", "decisive_review_question": "q",
       "definitive_rank_within_strain": "1"}


def _write(path, rows):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t"); w.writeheader(); w.writerows(rows)


def _gene(i, **kw):
    g = {"complete_identity": IDENTITY, "strain": "EXAMPLE", "bgc_alias": "BGC001", "gene_order": str(i),
         "query_gene": f"g{i}", "aa_length": "300", "primary_functional_role": "tailoring",
         "product_annotation": "enzyme", "functional_logic_without_dominant_match": "YES",
         "any_mibig_gene_match": "NO", "dominant_reference_gene_match": "", "matched_subject_gene": "",
         "matched_pct_identity": "", "matched_pct_coverage": ""}
    g.update(kw); return g


def test_blank_subject_is_not_shown_as_no_match():
    assert "no dominant-reference match" not in mod.protein_table_md([_gene(1)])
    assert "homology state not recorded" in mod.protein_table_md([_gene(1)])
    html = mod.protein_table_html([_gene(1, dominant_reference_gene_match="NO")])
    assert "no dominant-reference match<" not in html
    assert "not a completed no-hit search" in html
    md = mod.protein_table_md([_gene(1, matched_subject_gene="refA", matched_pct_identity="55")])
    assert "refA; ID 55%; coverage not recorded" in md


def test_unmatched_gene_cap_is_stated(tmp_path):
    src = tmp_path / "bgc.tsv"; _write(src, [ROW])
    genes = tmp_path / "genes.tsv"; _write(genes, [_gene(i) for i in range(1, 26)])
    mod.build(src, tmp_path / "out", genes)
    report = (tmp_path / "out" / "PER_STRAIN" / "EXAMPLE" / "REPORT.html").read_text()
    assert "showing 20 of 25" in report
    assert "Showing the first 20 of 25 genes" in report


def test_existing_output_folder_is_refused_and_failure_is_labelled(tmp_path):
    src = tmp_path / "bgc.tsv"; _write(src, [ROW])
    out = tmp_path / "out"; out.mkdir(); (out / "RECEIPT.json").write_text("old\n")
    with pytest.raises(FileExistsError):
        mod.build(src, out)
    assert (out / "RECEIPT.json").read_text() == "old\n"
    empty = tmp_path / "empty.tsv"; empty.write_text("complete_identity\n")
    with pytest.raises(Exception):
        mod.build(empty, tmp_path / "fresh")
    assert (tmp_path / "fresh" / "RUN_FAILED.json").is_file()
    assert not (tmp_path / "fresh" / "RECEIPT.json").exists()
