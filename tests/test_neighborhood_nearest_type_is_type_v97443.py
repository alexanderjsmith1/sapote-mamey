"""nearest_type_strain names the nearest explicitly reviewed type-material reference, not the nearest reference of any kind."""
import csv
import importlib.util
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "tools" / "phylo_place.py"
spec = importlib.util.spec_from_file_location("pp_type_col", SRC)
pp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pp)

TREE = "((AS_1:0.01,OP442298_1:0.001):0.01,(NR_112567_1:0.02,NR_026371_1:0.03):0.01);\n"
LABELS = {"OP442298_1": "OP442298.1 Kribbella sp. strain X 16S",
          "NR_112567_1": "NR_112567.1 Kribbella ginsengisoli strain Gsoil 001",
          "NR_026371_1": "NR_026371.1 Kribbella koreensis strain LM 161",
          "AS_1": "AS-1"}


def _rows(tmp_path, tree=TREE, type_evidence=None):
    nwk = tmp_path / "g.newick"; nwk.write_text(tree)
    out = tmp_path / "n.tsv"
    pp._grafted_neighborhoods(str(nwk), LABELS, str(out), query_names={"AS_1"}, type_evidence=type_evidence)
    return list(csv.DictReader(open(out), delimiter="\t"))


def test_type_column_skips_nontype_neighbour(tmp_path):
    from tools._placement_report_metadata import reviewed_type_map
    from .test_m5_placement_metadata_contract import table
    tip = "NR_112567_1"
    path = table(tmp_path/"type.tsv", [dict(tip=tip, accession="NR_112567.1", source_accession="NR_112567.1",
        taxon="Kribbella ginsengisoli", strain="Gsoil 001", role="type_reference", type_strain_of="Kribbella ginsengisoli",
        type_evidence="synthetic explicit reviewed evidence", review_state="REVIEWED", source_url="https://example.org/synthetic/NR_112567.1",
        strain_identity_basis="synthetic exact native-source strain")])
    evidence = reviewed_type_map([path], LABELS, query_tips=["AS_1"])
    (row,) = _rows(tmp_path, type_evidence=evidence)
    assert "ginsengisoli" in row["nearest_type_strain"]
    assert "OP442298" in row["nearest_reference_any"]
    assert float(row["patristic_dist"]) > float(row["nearest_reference_dist"])


def test_blank_type_column_when_panel_has_no_type_reference(tmp_path):
    (row,) = _rows(tmp_path, "(AS_1:0.01,OP442298_1:0.001);\n")
    assert row["nearest_type_strain"] == "" and row["patristic_dist"] == ""
    assert "OP442298" in row["nearest_reference_any"]


def test_nr_prefix_alone_leaves_type_column_unknown(tmp_path):
    (row,) = _rows(tmp_path)
    assert row["nearest_type_strain"] == row["patristic_dist"] == ""
    assert "OP442298" in row["nearest_reference_any"]
