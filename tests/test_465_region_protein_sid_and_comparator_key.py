"""tools/region_protein_by_genus.py optional columns: sid marks reference genomes as triangles
with a key; comparators of one name get their own key entry and leave n; tier and hjust place comparator labels."""
import csv
import re
import importlib.util
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("rpg465", ROOT / "tools/region_protein_by_genus.py")
rpg = importlib.util.module_from_spec(spec); spec.loader.exec_module(rpg)
needs_r = pytest.mark.skipif(not shutil.which("Rscript"), reason="Rscript unavailable")
HEAD = "strain\tgenus\tamino_acids\tmissing_CDS_lengths\trole\tname\tstrain_label\topen\tlabel\tsid\n"


def svg_text(path):
    """Drawn text of the SVG, words joined by single spaces (svglite writes one <text> per word)."""
    return " ".join(re.findall(r">([^<>]+)</text>", path.read_text()))


def table(tmp_path, comparators=""):
    refs = "".join(f"r{k}\tExample\t{100000 + 20000 * k}\t0\treference\t\t\t\t\t{'yes' if k < 2 else 'no'}\n" for k in range(6))
    p = tmp_path / "data.tsv"; p.write_text(HEAD + refs + "iso_a\tExample\t180000\t0\tisolate\t\t\t\t\tno\n" + comparators)
    c = tmp_path / "caption.md"; c.write_text("Synthetic totals with two genomes flagged as a named collection.\n")
    return p, c


@needs_r
def test_sid_column_is_kept_and_keyed(tmp_path):
    data, cap = table(tmp_path)
    assert rpg.main(["--data", str(data), "--caption", str(cap), "--out", str(tmp_path / "out")]) == 0
    rows = list(csv.DictReader(open(tmp_path / "out/plot_data.tsv"), delimiter="\t"))
    assert sum(r["sid"] == "yes" for r in rows) == 2
    svg = svg_text(tmp_path / "out/region_protein_by_genus.svg")
    assert "SID genomes (n = 2)" in svg and "Other public genomes (n = 4)" in svg
    assert "Example (n = 6)" in svg                                 # SID genomes still count in the row's n


@needs_r
def test_one_named_comparator_gets_a_key_entry_and_leaves_n(tmp_path):
    cmp = "".join(f"c{k}\tExample\t{150000 + 30000 * k}\t0\tcomparator\tMelissospora conviva\t\tyes\tno\tno\n" for k in range(3))
    data, cap = table(tmp_path, cmp)
    assert rpg.main(["--data", str(data), "--caption", str(cap), "--out", str(tmp_path / "out")]) == 0
    svg = svg_text(tmp_path / "out/region_protein_by_genus.svg")
    assert "Melissospora conviva (n = 3)" in svg and "Example (n = 6)" in svg               # key entry for the comparators; the row counts references only


@needs_r
def test_several_comparator_names_keep_the_old_drawing(tmp_path):
    cmp = ("c1\tExample\t150000\t0\tcomparator\tGenusa alpha\tDSM 1\tyes\tyes\tno\n"
           "c2\tExample\t260000\t0\tcomparator\tGenusb beta\tDSM 2\tyes\tyes\tno\n")
    data, cap = table(tmp_path, cmp)
    assert rpg.main(["--data", str(data), "--caption", str(cap), "--out", str(tmp_path / "out")]) == 0
    svg = svg_text(tmp_path / "out/region_protein_by_genus.svg")
    assert "Example (n = 8)" in svg                                   # no comparator key: comparators count in n, as before
