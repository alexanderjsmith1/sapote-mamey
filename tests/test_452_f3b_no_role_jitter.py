"""F3b without a role column: points take the same ID-hash jitter as the role path, so a genus is not drawn as a
diagonal line ordered by value (the "worms" seen in the v9.7.451 render). Synthetic data."""
import csv, importlib.util, shutil
from pathlib import Path
import pytest
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("b03_jitter", ROOT / "tools/region_protein_by_genus.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
pytestmark = pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript unavailable")


def run(tmp_path, role):
    rows = [(f"REF{i}", "Genusa", 100000 + 10000 * i) for i in range(12)]
    p = tmp_path / "d.tsv"
    with p.open("w") as f:
        f.write("strain\tgenus\tamino_acids\tmissing_CDS_lengths" + ("\trole" if role else "") + "\n")
        for s, g, aa in rows:
            f.write(f"{s}\t{g}\t{aa}\t0" + ("\treference" if role else "") + "\n")
    c = tmp_path / "c.md"; c.write_text("Synthetic caption.\n")
    out = tmp_path / ("role" if role else "norole")
    assert m.main(["--data", str(p), "--caption", str(c), "--out", str(out)]) == 0
    pts = list(csv.DictReader((out / "region_protein_by_genus_point_positions.tsv").open(), delimiter="\t"))
    return out, {r["strain"]: float(r["position"]) for r in pts}, {r["strain"]: float(r["value"]) for r in pts}


def test_no_role_positions_not_ordered_by_value(tmp_path):
    _, pos, val = run(tmp_path, role=False)
    order = sorted(pos, key=lambda s: val[s])
    ys = [pos[s] for s in order]
    assert ys != sorted(ys) and ys != sorted(ys, reverse=True)   # no monotone slope
    assert all(0.8 <= y <= 1.2 for y in ys)


def test_no_role_matches_role_path_positions(tmp_path):
    _, a, _ = run(tmp_path, role=False)
    _, b, _ = run(tmp_path, role=True)
    assert a == pytest.approx(b)


def test_no_role_keeps_genus_count_label(tmp_path):
    out, _, _ = run(tmp_path, role=False)
    assert "(n=12)" in PdfReader(out / "region_protein_by_genus.pdf").pages[0].extract_text().replace(" ", "")
