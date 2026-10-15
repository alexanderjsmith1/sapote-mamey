"""M5_452_k01_references_only: tools/chitin_isolate_vs_references.py --references-only draws one row per reference genus (range,
middle half, median per family) with no isolates; without the flag, --genomes and --isolates stay required. Synthetic data only."""
import csv, importlib.util, json
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("k01", ROOT / "tools/chitin_isolate_vs_references.py"); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
FAM = ["Glyco_hydro_18", "Glyco_hydro_19", "LPMO_10", "CBM_5_12"]


def refs(tmp_path):
    rows = []
    for g, base in (("Synthgenusa", 6), ("Synthgenusb", 1)):
        for i in range(4):
            r = dict(genus=g, strain_id=f"SYN-{g[-1]}{i}", cds_searched=5000)
            r.update({f: base + i for f in FAM}); rows.append(r)
    p = tmp_path / "refs.tsv"
    with p.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t"); w.writeheader(); w.writerows(rows)
    return p


def test_references_only_draws_genus_rows(tmp_path):
    out = tmp_path / "out"
    assert m.main(["--references-only", "--references", str(refs(tmp_path)), "--out", str(out), "--dpi", "100"]) == 0
    info = json.loads((out / "RUN_INFO.json").read_text())
    assert info["mode"] == "references_only" and info["genera"] == ["Synthgenusa", "Synthgenusb"]   # higher median chitinases first
    nums = list(csv.DictReader((out / "K01_chitin_references_by_genus_numbers.tsv").open(), delimiter="\t"))
    row = next(r for r in nums if r["genus"] == "Synthgenusa" and r["family"] == "Glyco_hydro_18")
    assert (row["n_references"], row["ref_min"], row["ref_max"], float(row["ref_median"])) == ("4", "6", "9", 7.5)
    assert (out / "K01_chitin_references_by_genus.png").stat().st_size > 0


def test_isolate_mode_still_requires_inputs(tmp_path):
    with pytest.raises(SystemExit):
        m.main(["--references", str(refs(tmp_path)), "--out", str(tmp_path / "o")])
