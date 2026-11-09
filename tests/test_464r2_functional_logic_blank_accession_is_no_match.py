"""A MIBiG hit with a blank accession or subject gene is not a match.

`tools/bgc_functional_logic_workup.py` counted any hit row as an MIBiG match, and a hit with a
blank accession matched a blank dominant accession (`"" == ""`). Real per-gene tables carry no
blank accessions today, so this guards a latent case.
"""
import csv
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("workup", ROOT / "tools" / "bgc_functional_logic_workup.py")
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)

IDENT = "EXAMPLE / CTG_A / region001 / BGC001"


def _write(path, fields, rows, delimiter=","):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter=delimiter)
        w.writeheader()
        w.writerows(rows)


def _fixture(tmp_path, hits, dominant):
    p = tmp_path / "pkg"
    p.mkdir()
    (p / "manifest.json").write_text("{}\n")
    cds_fields = ["strain", "contig", "region", "bgc_id", "locus_tag", "order", "length_aa", "product",
                  "sec_met_domains", "gene_functions"]
    base = {"strain": "EXAMPLE", "contig": "CTG_A", "region": "region001", "bgc_id": "BGC001"}
    _write(p / "EXAMPLE_cds_table.csv", cds_fields, [
        {**base, "locus_tag": "q1", "order": 1, "length_aa": 1100, "product": "NRPS core",
         "sec_met_domains": "AMP-binding; Condensation; PP-binding", "gene_functions": "biosynthetic"},
        {**base, "locus_tag": "q2", "order": 2, "length_aa": 400, "product": "cytochrome P450",
         "sec_met_domains": "p450", "gene_functions": "biosynthetic-additional"},
    ])
    _write(p / "EXAMPLE_3_mibig_per_gene.csv",
           ["bgc_id", "query_gene", "mibig_accession", "subject_gene", "pct_identity",
            "pct_coverage_interpretation", "blast_score"], hits)
    _write(p / "EXAMPLE_2_inventory.csv", ["BGC_ID", "Boundary", "Products"],
           [{"BGC_ID": "BGC001", "Boundary": "Interior", "Products": "NRPS"}])
    rank = tmp_path / "rank.tsv"
    _write(rank, ["complete_identity", "definitive_rank_all_bgcs", "dominant_mibig_accession",
                  "dominant_mibig_product", "matched_gene_pairs"],
           [{"complete_identity": IDENT, "definitive_rank_all_bgcs": 1, "dominant_mibig_accession": dominant,
             "dominant_mibig_product": "", "matched_gene_pairs": 0}], delimiter="\t")
    return p, rank


def _genes(tmp_path):
    rows = MOD.read_rows(tmp_path / "out" / "ALL_GENE_FUNCTIONAL_EVIDENCE.tsv")
    return {r["query_gene"]: r for r in rows}


def test_blank_accession_does_not_match_a_blank_dominant(tmp_path):
    hits = [{"bgc_id": "BGC001", "query_gene": "q2", "mibig_accession": "", "subject_gene": "",
             "pct_identity": 50, "pct_coverage_interpretation": 90, "blast_score": 100}]
    p, rank = _fixture(tmp_path, hits, dominant="")
    MOD.analyze([p], rank, tmp_path / "out")
    q2 = _genes(tmp_path)["q2"]
    assert q2["any_mibig_gene_match"] == "NO"
    assert q2["dominant_reference_gene_match"] == "NO"


def test_a_hit_without_a_subject_gene_is_not_a_match(tmp_path):
    hits = [{"bgc_id": "BGC001", "query_gene": "q2", "mibig_accession": "BGC0000001", "subject_gene": " ",
             "pct_identity": 50, "pct_coverage_interpretation": 90, "blast_score": 100}]
    p, rank = _fixture(tmp_path, hits, dominant="BGC0000001")
    MOD.analyze([p], rank, tmp_path / "out")
    q2 = _genes(tmp_path)["q2"]
    assert q2["any_mibig_gene_match"] == "NO"
    assert q2["dominant_reference_gene_match"] == "NO"


def test_a_complete_hit_still_matches(tmp_path):
    hits = [{"bgc_id": "BGC001", "query_gene": "q2", "mibig_accession": "BGC0000001.2", "subject_gene": "r2",
             "pct_identity": 50, "pct_coverage_interpretation": 90, "blast_score": 100}]
    p, rank = _fixture(tmp_path, hits, dominant="BGC0000001")
    MOD.analyze([p], rank, tmp_path / "out")
    q2 = _genes(tmp_path)["q2"]
    assert q2["any_mibig_gene_match"] == "YES"
    assert q2["dominant_reference_gene_match"] == "YES"
    assert q2["matched_subject_gene"] == "r2"


import pytest


@pytest.mark.parametrize("acc,subj,dom,any_,dom_", [
    ("NA", "r2", "NA", "NO", "NO"),
    ("-", "-", "-", "NO", "NO"),
    ("n/a", "r2", "n/a", "NO", "NO"),
    ("none", "r2", "", "NO", "NO"),
    ("BGC0000001", "nan", "BGC0000001", "NO", "NO"),
    ("BGC0000001", "NA", "BGC0000001", "NO", "NO"),
    ("bgc0000001", "r2", "BGC0000001", "YES", "YES"),
    (" BGC0000001.2 ", "r2", "BGC0000001", "YES", "YES"),
])
def test_placeholders_are_missing_and_accession_case_does_not_matter(tmp_path, acc, subj, dom, any_, dom_):
    hits = [{"bgc_id": "BGC001", "query_gene": "q2", "mibig_accession": acc, "subject_gene": subj,
             "pct_identity": 50, "pct_coverage_interpretation": 90, "blast_score": 100}]
    p, rank = _fixture(tmp_path, hits, dominant=dom)
    MOD.analyze([p], rank, tmp_path / "out")
    q2 = _genes(tmp_path)["q2"]
    assert (q2["any_mibig_gene_match"], q2["dominant_reference_gene_match"]) == (any_, dom_)
