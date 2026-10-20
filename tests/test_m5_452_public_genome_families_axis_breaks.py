"""m5_452_public_genome_families_axis_breaks: B04 (tools/public_genome_families.py) x-axis breaks come from scales::breaks_pretty over
0..max, as tools/bgc_class_groups.py. The sealed tool used fixed breaks 0, 10, 20, 30, 40 (filtered to <= max), so a genus with more than
40 families per genome had no ticks over the rest of the axis. Synthetic names only."""
import csv, importlib.util, shutil
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pgf", ROOT / "tools/public_genome_families.py"); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
spec2 = importlib.util.spec_from_file_location("mtc", ROOT / "tools/_min_text_check.py"); mtc = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(mtc)


def put(path, rows):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t"); w.writeheader(); w.writerows(rows)
    return path


def test_ticks_cover_a_79_family_axis(tmp_path):
    if not shutil.which("Rscript"): pytest.skip("Rscript unavailable")
    g = put(tmp_path / "g.tsv", [dict(strain=f"SYN-{i}", genus="Synthgenusa", block="Synthgenusa") for i in range(3)])
    d = put(tmp_path / "d.tsv", [dict(strain="SYN-0", genus="Synthgenusa", families=79, in_public=31, not_in_public=48),
                                 dict(strain="SYN-1", genus="Synthgenusa", families=57, in_public=54, not_in_public=3),
                                 dict(strain="SYN-2", genus="Synthgenusa", families=44, in_public=7, not_in_public=37)])
    out = tmp_path / "out"
    assert m.main(["--genomes", str(g), "--data", str(d), "--out", str(out), "--layout", "bee", "--dpi", "100",
                   "--min-text-pt", "8", "--print-width", "6.5"]) == 0
    texts = {t.strip() for _, t in mtc.text_sizes(str(out / "public_genome_families.pdf"))}
    assert {"0", "20", "40", "60"} <= texts          # breaks_pretty(0..79) = 0, 20, 40, 60, 80 (80 drawn only if inside the limit)
    assert not {"10", "30"} & texts                   # the old fixed 0-40 ticks are gone
