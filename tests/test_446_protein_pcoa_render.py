"""tools/protein_pcoa_render.py: label rules (strain labels and distance), drop/exclude, one stamped spec per panel for R,
banned figure text refused, delivered folders never overwritten. Synthetic strains only (tools/test_synthetic_ids.txt)."""
import csv
import importlib.util
import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("protein_pcoa_render", ROOT / "tools" / "protein_pcoa_render.py")
ppr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ppr)


def pt(x, y, strain, pid):
    return dict(x=x, y=y, strain=strain, pid=pid)


BG = [(i / 10, j / 10) for i in range(5) for j in range(5)]   # a 0.0-0.4 grid; every nearest-neighbour distance is 0.1


def test_strain_labels_put_low_identity_first_then_distance():
    cohort = [pt(0.2, 0.2, "AS-900", 90.0),        # on the grid, high identity
              pt(3.0, 3.0, "AS-901", 95.0),        # far away, high identity
              pt(0.21, 0.2, "AS-902", 40.0),       # low identity: first
              pt(0.25, 0.25, "AS-902", 55.0),      # same strain, same fill, more isolated: carries the label
              pt(1.0, 1.0, "AS-123", 60.0)]        # low identity, but 60 > 40: second
    groups, texts, thr, numbered = ppr.choose_labels(cohort, BG, top_strains=3)
    assert texts == ["AS-902", "AS-123", "AS-901"] and not numbered
    assert groups[0] == [3]
    assert thr == pytest.approx(0.1)


def test_few_points_are_all_labelled():
    cohort = [pt(0.2, 0.2, "AS-900", 90.0), pt(0.3, 0.3, "AS-900", 80.0)]
    groups, texts, _, _ = ppr.choose_labels(cohort, BG, top_strains=30)
    assert groups == [[0], [1]] and texts == ["AS-900", "AS-900"]


def test_distance_rule_groups_same_strain_and_numbers_above_the_cap():
    cohort = [pt(2.0, 2.0, "AS-900", 50.0), pt(2.001, 2.0, "AS-900", 45.0), pt(0.2, 0.2, "AS-901", 99.0)]
    groups, texts, thr, numbered = ppr.choose_labels(cohort, BG)
    assert texts == ["AS-900 x2 (45%)"] and sorted(groups[0]) == [0, 1] and len(groups) == 1   # the on-grid point stays unlabelled
    many = [pt(5 + i, 5 + i, f"AS-90{i % 3}", 50.0) for i in range(5)]
    _, texts, _, numbered = ppr.choose_labels(many, BG, number_above=3)
    assert numbered and texts == ["1", "2", "3", "4", "5"]


@pytest.fixture
def kit(tmp_path):
    out = tmp_path / "kit/out_KS"
    out.mkdir(parents=True)
    rows = [["id", "PC1", "PC2", "PC3", "n_represented", "source", "group", "genus", "strain", "subtype", "region_product",
             "locus_tag", "origin", "length"]]
    for n, (x, y) in enumerate(BG):
        rows.append([f"r{n}", x, y, 0, 2, "reference_held" if n % 4 else "MIBiG", "", "G", f"Ref_{n}", "", "", "", "", 300])
    rows += [["i1", 2.0, 2.0, 0, 1, "isolate", "", "G", "AS-900", "", "", "c1_1", "AS-900__N1.region001.gbk", 300],
             ["i2", 0.2, 0.2, 0, 1, "isolate", "", "G", "AS-901", "", "", "c2_1", "AS-901__N2.region001.gbk", 300],
             ["i3", 1.5, 0.1, 0, 1, "isolate", "", "G", "AS-902", "", "", "c3_1", "AS-902__N3.region001.gbk", 300]]
    with open(out / "PCOA_KS.tsv", "w", newline="") as fh:
        csv.writer(fh, delimiter="\t").writerows(rows)
    with open(out / "NEAREST_KS.tsv", "w", newline="") as fh:
        csv.writer(fh, delimiter="\t").writerows([["id", "nearest_pident"], ["i1", "50"], ["i2", "99"], ["i3", "60"]])
    (out / "RUN_KS.json").write_text(json.dumps({"pct_axes": [30.0, 20.0, 10.0]}))
    (tmp_path / "cohorts.tsv").write_text("strain\tcohort\nAS-900\tgroup_a\nAS-901\tgroup_a\nAS-902\tgroup_b\n")
    (tmp_path / "drop.txt").write_text("AS-901__N2.region001.gbk\n")
    return tmp_path


def run(kit, *extra):
    return ppr.main(["--kit", str(kit / "kit"), "--out", str(kit / "out"), "--cohort-table", str(kit / "cohorts.tsv"),
                     "--panel", "group_a=group_a", "--panel-label", "group_a=group_a isolates", "--top-strains", "5", *extra])


def test_matplotlib_render_and_receipts(kit):
    assert run(kit, "--renderer", "matplotlib", "--drop-origins", str(kit / "drop.txt")) == 0
    for ext in ("pdf", "svg", "png"):
        assert (kit / f"out/PCOA_KS_group_a.{ext}").stat().st_size > 0
    labels = list(csv.DictReader(open(kit / "out/LABELS_KS_group_a.tsv"), delimiter="\t"))
    assert [r["strain"] for r in labels] == ["AS-900"]          # AS-901 dropped by origin, AS-902 is another cohort
    receipt = json.loads((kit / "out/panel_KS_group_a.json").read_text())
    assert receipt["n_cohort_points"] == 1 and receipt["n_low"] == 1 and receipt["label_rule"] == "top_strains"
    assert not list((kit / "out").glob(".render_*"))


def test_banned_wording_is_refused(kit):
    (kit / "names.tsv").write_text("set\ttitle\ttag\nKS\tKS domains\tKS domains, claim-safe view\n")
    assert run(kit, "--renderer", "matplotlib", "--set-names", str(kit / "names.tsv")) == 2


def test_refuses_to_overwrite_a_delivered_folder(kit):
    (kit / "out").mkdir()
    (kit / "out/PCOA_KS_group_a.png").write_bytes(b"delivered")
    assert run(kit, "--renderer", "matplotlib") == 2
    assert (kit / "out/PCOA_KS_group_a.png").read_bytes() == b"delivered"


@pytest.mark.skipif(not ppr.r_available(), reason="Rscript with ggplot2, ggrepel, jsonlite and svglite not available")
def test_r_render_and_stamp_guard(kit, tmp_path):
    assert run(kit, "--renderer", "r") == 0
    assert (kit / "out/PCOA_KS_group_a.svg").stat().st_size > 0 and not list((kit / "out").glob("*.stamp"))
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps({"stamp": "aaa", "points": [], "labels": [], "legend": {}, "tag": "", "colour": "#000000"}))
    r = subprocess.run(["Rscript", str(ROOT / "tools/protein_pcoa_render.R"), str(spec_file), str(tmp_path / "x"), "bbb"],
                       capture_output=True, text=True)
    assert r.returncode != 0 and "stamp mismatch" in r.stderr
    assert not (tmp_path / "x.pdf").exists()


def test_tool_names_no_strain():
    for f in ("tools/protein_pcoa_render.py", "tools/protein_pcoa_render.R"):
        assert not re.search(r"\bA[JS]S?-\d", (ROOT / f).read_text()), f


# ---- Review: F5 grouping span from every kit point, F6 base-pdf fallback ---------------------------------------
def test_grouping_span_comes_from_the_whole_kit():
    # two points of one strain 0.02 apart; panel + background span 1.0 (1.5% = 0.015: two labels),
    # whole kit span 2.0 because of an other-cohort point (1.5% = 0.03: one shared label, as in v5)
    cohort = [dict(x=0.0, y=0.0, strain="AS-900", pid=50.0), dict(x=0.02, y=0.0, strain="AS-900", pid=50.0)]
    background = [(1.0, 0.0), (1.0, 0.01)]
    g_panel, _, _, _ = ppr.choose_labels(cohort, background, number_above=99)
    g_kit, texts, _, _ = ppr.choose_labels(cohort, background, number_above=99, span=2.0)
    assert len(g_panel) == 2 and len(g_kit) == 1 and texts[0].startswith("AS-900 x2")


def test_build_panel_passes_the_kit_span():
    src = (ROOT / "tools/protein_pcoa_render.py").read_text()
    assert "span=kit_span" in src and 'kx, ky = [float(r["PC1"]) for r in rows]' in src


def test_r_pdf_falls_back_to_base_pdf():
    src = (ROOT / "tools/protein_pcoa_render.R").read_text()
    assert "pdf_ok <- tryCatch(" in src and "device = grDevices::pdf)" in src
