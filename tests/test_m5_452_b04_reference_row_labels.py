"""M5_452_b04_reference_row_labels: B04 (tools/public_genome_families.py) for a reference-only genus. An optional genome-table
'label' column is used verbatim as the row label ('\\n' breaks the line), and --part-labels renames the two legend parts. Without
either, output is unchanged (covered by the existing B04 tests). Synthetic names only."""
import csv, importlib.util, json, shutil
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pgf", ROOT / "tools/public_genome_families.py"); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def put(path, rows):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t"); w.writeheader(); w.writerows(rows)
    return path


@pytest.mark.needs_arial
def test_label_column_and_part_labels(tmp_path):
    if not shutil.which("Rscript"): pytest.skip("Rscript unavailable")
    g = put(tmp_path / "g.tsv", [dict(strain="SYN-991", genus="Synthgenusa", block="Synthgenusa", label="<i>Synthgenusa alpha</i> SYN 1\\n[SYN_000001.1] [Type]"),
                                 dict(strain="SYN-992", genus="Synthgenusa", block="Synthgenusa", label="<i>Synthgenusa</i> sp. SYN 2\\n[SYN_000002.1]")])
    d = put(tmp_path / "d.tsv", [dict(strain="SYN-991", genus="Synthgenusa", families=10, in_public=7, not_in_public=3),
                                 dict(strain="SYN-992", genus="Synthgenusa", families=8, in_public=4, not_in_public=4)])
    out = tmp_path / "out"
    assert m.main(["--genomes", str(g), "--data", str(d), "--out", str(out), "--layout", "bee", "--dpi", "100",
                   "--part-labels", "In 2 or more genomes|In this genome only"]) == 0
    cfg = json.loads((out / "render_config.json").read_text())
    assert cfg["part_labels"] == ["In 2 or more genomes", "In this genome only"]
    rows = list(csv.DictReader((out / "plot_data.tsv").open(), delimiter="\t"))
    assert rows[0]["label"].count("<br>") == 1 and "\\n" not in rows[0]["label"]


def test_bad_part_labels_refused(tmp_path):
    g = put(tmp_path / "g.tsv", [dict(strain="SYN-991", genus="Synthgenusa", block="Synthgenusa")])
    d = put(tmp_path / "d.tsv", [dict(strain="SYN-991", genus="Synthgenusa", families=1, in_public=1, not_in_public=0)])
    with pytest.raises(ValueError):
        m.main(["--genomes", str(g), "--data", str(d), "--out", str(tmp_path / "o"), "--part-labels", "same|same"])
