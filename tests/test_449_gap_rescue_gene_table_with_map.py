"""tools/gap_rescue_gene_table.py: each gap-rescue run writes a per-gene table and pairs it with its locus map.

The table says where every reference gene's best strain protein lies (core region, the core contig outside the region,
another contig, or not found), when one protein is the best match for several reference genes, and when a gene was
called split across contig ends, so the table never disagrees with the map silently.
"""
import csv
import importlib.util
import sys
from pathlib import Path

import pytest

pytest.importorskip("Bio")
pytest.importorskip("matplotlib")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import gap_rescue_gene_table as gt  # noqa: E402

_spec = importlib.util.spec_from_file_location("t444", ROOT / "tests/test_444_gap_directed_rescue.py")
t444 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(t444)


def test_long_reference_notes_are_shortened():
    assert gt.tidy_annotation("COG function: Cell wall. KEGG: x. COG: COG1898 dTDP-4-dehydrorhamnose 3,5-epimerase and "
                              "related enzymes.") == "dTDP-4-dehydrorhamnose 3,5-epimerase and related enzymes"
    assert gt.tidy_annotation("SC6A5.08, probable phytoene synthase, len: 303aa; similar to many") == "probable phytoene synthase"
    long = "word " * 40
    assert len(gt.tidy_annotation(long)) <= 90 and gt.tidy_annotation(long).endswith("...")


def test_location_column_names_contig_shared_protein_and_split():
    core = "T / NODE_1_length_9 / region001 / BGC007"
    rows = [
        {"reference_gene": "1", "name": "r1", "status": "PRESENT_IN_CORE", "best_locus": "c1_1", "best_protein": "q1",
         "best_len_aa": "300", "best_contig": "NODE_1_length_9", "best_identity_pct": "80"},
        {"reference_gene": "2", "name": "r2", "status": "PRESENT_IN_CORE", "best_locus": "c1_1", "best_protein": "q1",
         "best_len_aa": "300", "best_contig": "NODE_1_length_9", "best_identity_pct": "55"},
        {"reference_gene": "3", "name": "r3", "status": "MISSING_FOUND_CLEAR", "best_locus": "c1_9", "best_protein": "q9",
         "best_len_aa": "200", "best_contig": "NODE_1_length_9", "best_region_identity": "T / NODE_1_length_9 (no antiSMASH region)",
         "partner_verdict": "SINGLE_GENE", "best_identity_pct": "60"},
        {"reference_gene": "4", "name": "r4", "status": "MISSING_FOUND_CLEAR", "best_locus": "c5_2", "best_protein": "q12",
         "best_len_aa": "250", "best_contig": "NODE_5_length_3", "best_region_identity": "T / NODE_5_length_3 (no antiSMASH region)",
         "partner_verdict": "PARALOG_FAMILY", "best_identity_pct": "70"},
        {"reference_gene": "5", "name": "r5", "status": "MISSING_NOT_FOUND", "best_locus": "", "best_protein": ""},
    ]
    splits = [{"name": "r5", "status": "SPLIT_ACROSS_CONTIG_ENDS", "split_call": "CLEAR",
               "piece1_region_identity": "T / NODE_8_length_2 (no antiSMASH region)",
               "piece2_region_identity": "T / NODE_9_length_2 / region001 / BGC002",
               "piece1_locus": "c8_1", "piece2_locus": "c9_1", "piece1_identity_pct": "63.7", "piece2_identity_pct": "52.7"}]
    t = gt.table_rows(rows, splits, core, {"q1": "Beta-ketoacyl synthase"}, {"r1": "ketosynthase"})
    loc = [r["Location"] for r in t]
    assert loc[0] == "BGC007, NODE_1 (core)"
    assert loc[1] == "BGC007, NODE_1 (core); same protein as r1"
    assert loc[2] == "NODE_1, same contig, outside the region; single gene"
    assert loc[3] == "NODE_5, no antiSMASH region, other contig; paralog family"
    assert loc[4] == "split across NODE_8 + BGC002, NODE_9"   # a CLEAR split row names its two pieces, as the map does
    assert t[4]["CDS"] == "c8_1 + c9_1" and t[4]["Identity (%)"] == "63.7 / 52.7"
    assert t[0]["Protein family (antiSMASH)"] == "Beta-ketoacyl synthase" and t[0]["Reference annotation"] == "ketosynthase"



def test_a_run_writes_the_table_and_pairs_it_with_the_map(tmp_path):
    rows, receipt, out = t444._run(tmp_path)
    table = list(csv.DictReader(open(out / "gene_table.tsv"), delimiter="\t"))
    assert [r["Reference gene"] for r in table] == [f"r{i}" for i in range(1, 7)]
    assert all("(core)" in r["Location"] for r in table[:3])
    assert all("other contig" in r["Location"] and "ctgB" in r["Location"] for r in table[3:])
    assert (out / "gene_table.png").stat().st_size > 5_000 and (out / "gene_table.pdf").exists()
    pytest.importorskip("PIL")
    pypdf = pytest.importorskip("pypdf")
    assert (out / "map_and_table.png").exists()
    assert len(pypdf.PdfReader(str(out / "map_and_table.pdf")).pages) == 2


def test_no_gene_table_flag_skips_it(tmp_path):
    z, ref, hits = t444._setup(tmp_path)
    out = tmp_path / "out"
    assert t444.gdr.main(["--zip", str(z), "--label", "T", "--core", "ctgA.region001", "--reference", str(ref),
                          "--out", str(out), "--hits", str(hits), "--no-gene-table"]) == 0
    assert (out / "gap_rescue.tsv").exists() and not (out / "gene_table.tsv").exists()


def test_only_clear_splits_read_split_across():
    base = {"status": "SPLIT_ACROSS_CONTIG_ENDS", "piece1_region_identity": "T / NODE_8_length_2 (no antiSMASH region)",
            "piece2_region_identity": "T / NODE_9_length_2 (no antiSMASH region)"}
    notes = gt.split_notes([dict(base, name="a", split_call="CLEAR"), dict(base, name="b", split_call="WEAK"),
                            dict(base, name="c", split_call="RIVAL_STRONGER"),
                            dict(base, name="d", split_call="MODULAR_UNRESOLVED")])
    assert notes == {"a": "; split across NODE_8 + NODE_9", "b": "; weak split candidate on NODE_8 + NODE_9",
                     "c": "; weaker split candidate on NODE_8 + NODE_9", "d": "; modular gene, split not resolved"}


def test_shared_protein_primary_is_the_reciprocal_best_row():
    # the map draws only the reciprocal-best row of a shared protein, so the note goes on the other row
    rows = [{"reference_gene": "1", "name": "narC", "status": "PRESENT_IN_CORE", "best_locus": "c94_18", "best_protein": "q",
             "best_len_aa": "3050", "best_contig": "NODE_94_length_9", "best_identity_pct": "46.9", "reciprocal_best": "False"},
            {"reference_gene": "2", "name": "narA", "status": "PRESENT_IN_CORE", "best_locus": "c94_18", "best_protein": "q",
             "best_len_aa": "3050", "best_contig": "NODE_94_length_9", "best_identity_pct": "75.1", "reciprocal_best": "True"}]
    t = gt.table_rows(rows, [], "T / NODE_94_length_9 / region001 / BGC050", {}, {})
    assert [r["Location"] for r in t] == ["BGC050, NODE_94 (core); same protein as narA", "BGC050, NODE_94 (core)"]


def test_a_core_gene_that_crosses_the_region_edge_says_so():
    # region membership is coordinate overlap, so a gene straddling the region end is "in the core"; the table says how much
    core = {"contig": "ctg10", "start": 67310, "end": 101080}
    prots = {"q1": {"contig": "ctg10", "start": 100185, "end": 102450, "tag": "ctg10_75"},
             "q2": {"contig": "ctg10", "start": 90000, "end": 91000, "tag": "ctg10_70"}}
    rows = [{"reference_gene": "1", "name": "r1", "status": "PRESENT_IN_CORE", "best_locus": "ctg10_75", "best_protein": "q1",
             "best_contig": "NODE_10_length_9", "best_identity_pct": "73"},
            {"reference_gene": "2", "name": "r2", "status": "PRESENT_IN_CORE", "best_locus": "ctg10_70", "best_protein": "q2",
             "best_contig": "NODE_10_length_9", "best_identity_pct": "80"}]
    edge = gt.edge_shares(rows, prots, core)
    assert edge == {"ctg10_75": 40}
    t = gt.table_rows(rows, [], "T / NODE_10_length_9 / region002 / BGC002", {}, {}, edge)
    assert t[0]["Location"] == "BGC002, NODE_10 (core); crosses the region edge (40% of the gene inside)"
    assert t[1]["Location"] == "BGC002, NODE_10 (core)"

