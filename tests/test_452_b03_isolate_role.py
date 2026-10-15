"""B03 optional role column (card 018c0f08_452_b03_isolate_role): boxes from references only, isolates drawn as
labelled diamonds, italic genus with the reference count; without role the output is as before. Synthetic data."""
import csv, importlib.util, shutil
from pathlib import Path
import pytest
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("b03_role", ROOT / "tools/region_protein_by_genus.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
pytestmark = pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript unavailable")


def data(tmp_path, role=True, bad=False):
    rows = [("SYN-970", "Genusa", 150000, "isolate"), ("SYN-971", "Genusb", 400000, "isolate")]
    rows += [(f"REF{i}", "Genusa", 100000 + 10000 * i, "reference") for i in range(8)]
    rows += [(f"REFB{i}", "Genusb", 300000 + 20000 * i, "reference") for i in range(5)]
    p = tmp_path / "d.tsv"
    with p.open("w") as f:
        f.write("strain\tgenus\tamino_acids\tmissing_CDS_lengths" + ("\trole" if role else "") + "\n")
        for s, g, aa, r in rows:
            f.write(f"{s}\t{g}\t{aa}\t0" + (f"\t{'other' if bad and s == 'SYN-970' else r}" if role else "") + "\n")
    c = tmp_path / "c.md"; c.write_text("Synthetic caption.\n")
    return p, c


def test_role_boxes_from_references_and_labelled_isolates(tmp_path):
    d, c = data(tmp_path); out = tmp_path / "out"
    assert m.main(["--data", str(d), "--caption", str(c), "--out", str(out)]) == 0
    box = list(csv.DictReader((out / "region_protein_by_genus_box_summary.tsv").open(), delimiter="\t"))
    assert float(box[0]["median"]) == pytest.approx(135.0)          # references 100k..170k only, not SYN-970
    text = PdfReader(out / "region_protein_by_genus.pdf").pages[0].extract_text().replace(" ", "")
    assert "SYN-970" in text and "SYN-971" in text and "(n=8)" in text and "(n=5)" in text
    assert "role" in (out / "plot_data.tsv").read_text().splitlines()[0]


def test_without_role_unchanged_columns(tmp_path):
    d, c = data(tmp_path, role=False); out = tmp_path / "out"
    assert m.main(["--data", str(d), "--caption", str(c), "--out", str(out)]) == 0
    assert (out / "plot_data.tsv").read_text().splitlines()[0].split("\t") == m.FIELDS
    assert "(n=9)" in PdfReader(out / "region_protein_by_genus.pdf").pages[0].extract_text().replace(" ", "")


def test_bad_role_refused(tmp_path):
    d, c = data(tmp_path, bad=True)
    with pytest.raises(ValueError):
        m.main(["--data", str(d), "--caption", str(c), "--out", str(tmp_path / "out")])
