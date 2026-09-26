"""nearest_type_strain names the nearest NR_ (type-material) reference, not the nearest reference of any kind."""
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


def _rows(tmp_path, tree=TREE):
    nwk = tmp_path / "g.newick"; nwk.write_text(tree)
    out = tmp_path / "n.tsv"
    pp._grafted_neighborhoods(str(nwk), LABELS, str(out), query_names={"AS_1"})
    return list(csv.DictReader(open(out), delimiter="\t"))


def test_type_column_skips_nontype_neighbour(tmp_path):
    (row,) = _rows(tmp_path)
    assert "ginsengisoli" in row["nearest_type_strain"]
    assert "OP442298" in row["nearest_reference_any"]
    assert float(row["patristic_dist"]) > float(row["nearest_reference_dist"])


def test_blank_type_column_when_panel_has_no_type_reference(tmp_path):
    (row,) = _rows(tmp_path, "(AS_1:0.01,OP442298_1:0.001);\n")
    assert row["nearest_type_strain"] == "" and row["patristic_dist"] == ""
    assert "OP442298" in row["nearest_reference_any"]
