"""Card attine_452_b03_row_without_references: B03 draws a genus row that has an isolate but no public genomes.

The fixed-jitter step ran over an empty reference set and R stopped ("non-numeric argument to binary operator"). A row
with no public genomes now keeps its isolate diamond, draws no points or box, and is labelled "(no public genomes)";
every other row is drawn exactly as before. Synthetic data only.
"""
import csv
import importlib.util
import shutil
from pathlib import Path

import pytest
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("b03_empty", ROOT / "tools/region_protein_by_genus.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
pytestmark = pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript unavailable")


def render(tmp_path, with_empty_row):
    rows = [("SYN-970", "Genusa", 150000, "isolate"), ("SYN-971", "Genusb", 400000, "isolate")]
    rows += [(f"REF{i}", "Genusa", 100000 + 10000 * i, "reference") for i in range(8)]
    rows += [(f"REFB{i}", "Genusb", 300000 + 20000 * i, "reference") for i in range(5)]
    if with_empty_row:
        rows += [("SYN-972", "Genusc", 250000, "isolate")]
    tmp_path.mkdir(parents=True, exist_ok=True)
    d = tmp_path / "d.tsv"
    d.write_text("strain\tgenus\tamino_acids\tmissing_CDS_lengths\trole\n" + "".join(f"{s}\t{g}\t{a}\t0\t{r}\n" for s, g, a, r in rows))
    c = tmp_path / "c.md"; c.write_text("Synthetic caption.\n")
    out = tmp_path / "out"
    assert m.main(["--data", str(d), "--caption", str(c), "--out", str(out)]) == 0
    return out


def test_a_row_without_public_genomes_draws_its_isolate_only(tmp_path):
    out = render(tmp_path / "with", True)
    text = PdfReader(out / "region_protein_by_genus.pdf").pages[0].extract_text().replace(" ", "")
    assert "SYN-972" in text and "(nopublicgenomes)" in text and "(n=8)" in text and "(n=5)" in text
    plot = list(csv.DictReader((out / "plot_data.tsv").open(), delimiter="\t"))
    assert [r["genus"] for r in plot if r["strain"] == "SYN-972"] == ["Genusc"]
    boxes = list(csv.DictReader((out / "region_protein_by_genus_box_summary.tsv").open(), delimiter="\t"))
    assert len(boxes) == 2   # no box for the row without public genomes


def test_every_other_row_is_drawn_as_before(tmp_path):
    a, b = render(tmp_path / "with", True), render(tmp_path / "without", False)
    box = lambda o: (o / "region_protein_by_genus_box_summary.tsv").read_text()
    assert box(a) == box(b)
    keep = lambda o: [r for r in csv.DictReader((o / "plot_data.tsv").open(), delimiter="\t") if r["genus"] != "Genusc"]
    assert keep(a) == keep(b)
