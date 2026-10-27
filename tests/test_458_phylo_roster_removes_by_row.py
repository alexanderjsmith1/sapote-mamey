"""phylo_roster --remove drops the numbered panel row, even when another row shares its label.

The writer kept every row whose candidate_id was still in the kept set, so removing one of two
rows with the same candidate_id removed neither.
"""
import csv
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location("phylo_roster_458", ROOT / "tools" / "phylo_roster.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_duplicate_label_row_is_removed(tmp_path):
    panel = tmp_path / "panel.tsv"
    panel.write_text("candidate_id\trole\tnote\n"
                     "GCF_1\tREFERENCE\tfirst\n"
                     "GCF_1\tREFERENCE\tsecond\n"
                     "GCF_2\tREFERENCE\tthird\n")
    out = tmp_path / "edited.tsv"
    assert _load().main(["--panel", str(panel), "--remove", "2", "--out", str(out)]) == 0
    rows = list(csv.DictReader(open(out), delimiter="\t"))
    assert [r["note"] for r in rows] == ["first", "third"]
