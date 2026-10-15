"""tools/blastp_identity_figures.py writes CORE_GENES_WITHOUT_HIT.tsv (card .452 blastp_core_genes_without_hit).

The owner, 13 Oct: "if data is sparse so that no box is drawn for a box plot, we can prioritize that blastp right now."
The by-class figure now also lists every core gene of a drawn genome with no bound value, by class, with the class's
gene count with a hit and whether its box is drawn, so the BLASTp to run next is a file, not a guess. Synthetic data.
"""
import csv
import importlib.util
from collections import Counter
from pathlib import Path

spec = importlib.util.spec_from_file_location("todo_fixture", Path(__file__).with_name("test_452_blastp_identity_figures_alex_notes.py"))
fixture = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixture)
world = fixture.world


def _rows(path):
    return list(csv.DictReader(open(path), delimiter="\t"))


def test_todo_list_matches_the_numbers_table(world):
    out = world["tmp"] / "todo"
    assert fixture._run(world, out, "--figure", "by-class") == 0
    todo = _rows(out / "CORE_GENES_WITHOUT_HIT.tsv")
    header = open(out / "CORE_GENES_WITHOUT_HIT.tsv").readline().rstrip("\n").split("\t")
    assert header == ["bgc_class", "strain", "genus", "locus_tag", "class_genes_with_hit", "box_drawn"]
    missing = Counter((r["bgc_class"], r["strain"]) for r in todo)
    for n in _rows(out / "BLASTP_IDENTITY_BY_CLASS_numbers.tsv"):
        assert missing.get((n["bgc_class"], n["strain"]), 0) == int(n["core_genes"]) - int(n["core_genes_with_hit"])
    for r in todo:
        assert r["box_drawn"] == ("yes" if int(r["class_genes_with_hit"]) >= 5 else "no")


def test_omitted_classes_still_listed(world):
    out = world["tmp"] / "todo_omit"
    assert fixture._run(world, out, "--figure", "by-class", "--omit-class", "Other") == 0
    full = world["tmp"] / "todo_full"
    assert fixture._run(world, full, "--figure", "by-class") == 0
    assert (out / "CORE_GENES_WITHOUT_HIT.tsv").read_bytes() == (full / "CORE_GENES_WITHOUT_HIT.tsv").read_bytes()
