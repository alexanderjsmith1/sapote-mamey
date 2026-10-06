"""tools/protein_pcoa_render.py --mid-below: a third identity tier (light fill) between --label-below and --mid-below.
Without the flag the figure keeps its two tiers. Synthetic strains only (tools/test_synthetic_ids.txt)."""
import csv
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("protein_pcoa_render", ROOT / "tools" / "protein_pcoa_render.py")
ppr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ppr)

BG = [(i / 10, j / 10) for i in range(5) for j in range(5)]


@pytest.fixture
def kit(tmp_path):
    out = tmp_path / "kit/out_KS"
    out.mkdir(parents=True)
    rows = [["id", "PC1", "PC2", "PC3", "n_represented", "source", "group", "genus", "strain", "subtype", "region_product",
             "locus_tag", "origin", "length"]]
    for n, (x, y) in enumerate(BG):
        rows.append([f"r{n}", x, y, 0, 2, "reference_held" if n % 4 else "MIBiG", "", "G", f"Ref_{n}", "", "", "", "", 300])
    for k, (x, y) in enumerate([(2.0, 2.0), (0.2, 0.2), (1.5, 0.1)]):
        rows.append([f"i{k}", x, y, 0, 1, "isolate", "", "G", f"AS-90{k}", "", "", f"c{k}_1", f"AS-90{k}__N{k}.region001.gbk", 300])
    with open(out / "PCOA_KS.tsv", "w", newline="") as fh:
        csv.writer(fh, delimiter="\t").writerows(rows)
    with open(out / "NEAREST_KS.tsv", "w", newline="") as fh:
        csv.writer(fh, delimiter="\t").writerows([["id", "nearest_pident"], ["i0", "50"], ["i1", "78"], ["i2", "92"]])
    (out / "RUN_KS.json").write_text(json.dumps({"pct_axes": [30.0, 20.0, 10.0]}))
    (tmp_path / "cohorts.tsv").write_text("strain\tcohort\nAS-900\tg\nAS-901\tg\nAS-902\tg\n")
    return tmp_path


def run(kit, *extra):
    return ppr.main(["--kit", str(kit / "kit"), "--out", str(kit / "out"), "--cohort-table", str(kit / "cohorts.tsv"),
                     "--panel", "g=g", "--panel-label", "g=g isolates", "--top-strains", "5", "--renderer", "matplotlib", *extra])


def test_three_tiers_split_the_open_points(kit):
    assert run(kit, "--mid-below", "85") == 0
    receipt = json.loads((kit / "out/panel_KS_g.json").read_text())
    assert (receipt["n_low"], receipt["n_mid"], receipt["n_cohort_points"]) == (1, 1, 3) and receipt["mid_below"] == 85
    fills = {r["strain"]: r["fill"] for r in csv.DictReader(open(kit / "out/LABELS_KS_g.tsv"), delimiter="\t")}
    assert fills == {"AS-900": "solid", "AS-901": "light", "AS-902": "open"}
    svg = (kit / "out/PCOA_KS_g.svg").read_text()
    assert "70–85% identity" in svg and "&gt;= 85% identity" in svg


def test_default_keeps_two_tiers(kit):
    assert run(kit) == 0
    receipt = json.loads((kit / "out/panel_KS_g.json").read_text())
    assert receipt["n_mid"] == 0 and receipt["mid_below"] is None
    fills = {r["fill"] for r in csv.DictReader(open(kit / "out/LABELS_KS_g.tsv"), delimiter="\t")}
    assert fills == {"solid", "open"}
    assert "&gt;= 70% identity" in (kit / "out/PCOA_KS_g.svg").read_text()


def test_mid_tier_must_lie_above_the_low_tier(kit):
    with pytest.raises(SystemExit):
        run(kit, "--mid-below", "60")


def test_tint_mixes_the_panel_colour_with_white():
    assert ppr.tint("#000000") == "#8c8c8c" and ppr.tint("#ffffff") == "#ffffff"
