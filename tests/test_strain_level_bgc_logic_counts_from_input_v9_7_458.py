"""The cross-strain and index intros count strains and loci from the input, not fixed text."""
import csv
import importlib.util
from pathlib import Path

TOOL = Path(__file__).parents[1] / "tools" / "strain_level_bgc_logic.py"
spec = importlib.util.spec_from_file_location("strain_level_bgc_logic_counts", TOOL)
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)


def _row(identity, rank):
    return {
        "complete_identity": identity, "standalone_biological_evidence_score_0_100": "70",
        "functional_reference_relation": "ARCHITECTURE_CORROBORATES_REFERENCE", "boundary": "Interior",
        "evidence_tier": "A_STRONG_PATHWAY_FAMILY_ARCHITECTURE", "genes_matching_dominant_reference": "5",
        "total_cds": "6", "current_antismash_products": "RiPP", "architecture_first_pathway_type": "lanthipeptide RiPP",
        "architecture_first_confidence": "HIGH", "dominant_mibig_product": "example",
        "functional_genes_without_any_mibig_match": "1", "functional_logic_summary": "logic",
        "rggmci_confidence": "", "rggmci_partner_identity": "", "decisive_review_question": "question",
        "definitive_rank_within_strain": str(rank),
    }


def test_intro_counts_come_from_input(tmp_path):
    rows = [_row("SYN-A / NODE_1_length_50000_cov_10 / region001 / BGC001", 1),
            _row("SYN-A / NODE_2_length_40000_cov_10 / region001 / BGC002", 2),
            _row("SYN-B / NODE_1_length_30000_cov_10 / region001 / BGC001", 1)]
    src = tmp_path / "bgc.tsv"
    with src.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t"); w.writeheader(); w.writerows(rows)
    mod.build(src, tmp_path / "out")
    cmp_md = (tmp_path / "out" / "CROSS_STRAIN_BGC_COMPARISON.md").read_text()
    index = (tmp_path / "out" / "INDEX.html").read_text()
    assert "of the 2 package-backed" in cmp_md
    assert "built from 3 complete-identity loci" in index
    assert "42 package-backed" not in cmp_md
    assert "2,409" not in index
