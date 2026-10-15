"""tools/collection_map.py (card 018c0f08_452_collection_map_tool): collection-site map from explicit site and isolate
tables on a shapefile basemap. Synthetic sites, isolates and a synthetic two-square shapefile."""
import csv
import importlib.util
import json
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
shapefile = pytest.importorskip("shapefile")
pypdf = pytest.importorskip("pypdf")
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("collection_map_t", ROOT / "tools/collection_map.py")
cm = importlib.util.module_from_spec(spec); spec.loader.exec_module(cm)


def _basemap(tmp):
    w = shapefile.Writer(str(tmp / "land"), shapeType=shapefile.POLYGON)
    w.field("name", "C")
    w.poly([[(-80, 35), (-70, 35), (-70, 45), (-80, 45), (-80, 35)]]); w.record("A")
    w.poly([[(-70, 40), (-62, 40), (-62, 47), (-70, 47), (-70, 40)]]); w.record("B")
    w.close()
    return tmp / "land.shp"


def _inputs(tmp, extra_site=None):
    sites = [("S1", "Site one", 44.0, -78.0), ("S2", "Site two\\nsecond line", 41.0, -74.0), ("S3", "Site three", 45.0, -64.0)]
    with (tmp / "sites.tsv").open("w") as f:
        f.write("site\tlabel\tlat\tlon\n"); [f.write(f"{a}\t{b}\t{c}\t{d}\n") for a, b, c, d in sites]
    rows = [(f"SYN-{970 + i}", s, g, gen) for i, (s, g, gen) in enumerate(
        [("S1", "Bryophyte", "Streptomyces")] * 6 + [("S1", "Lichen", "")] * 2 + [("S2", "Bryophyte", "Nocardia")] * 3 +
        [("S2", "Bryophyte", "Streptomyces")] * 2 + [("S3", "Mushroom", "Kribbella")])]
    if extra_site:
        rows.append(("SYN-999", extra_site, "Bryophyte", "Streptomyces"))
    with (tmp / "isolates.tsv").open("w") as f:
        f.write("isolate\tsite\tgroup\tgenus\n"); [f.write("\t".join(r) + "\n") for r in rows]
    return tmp / "isolates.tsv", tmp / "sites.tsv"


def _sizes(pdf):
    out = []
    pypdf.PdfReader(str(pdf)).pages[0].extract_text(
        visitor_text=lambda t, c, tm, fd, fs: out.append(abs(fs * tm[0]) if tm[0] else fs) if t.strip() else None)
    return out


@pytest.mark.parametrize("mark", ["pie", "circle"])
def test_map_draws_counts_and_8pt(tmp_path, mark):
    iso, sites = _inputs(tmp_path)
    out = tmp_path / f"map_{mark}"
    assert cm.main(["--isolates", str(iso), "--sites", str(sites), "--basemap", str(_basemap(tmp_path)),
                    "--out", str(out), "--mark", mark, "--pool-below", "1", "--dpi", "100"]) == 0
    pdf = out.with_suffix(".pdf")
    assert min(_sizes(pdf)) >= 8.0 - 1e-6
    assert abs(float(pypdf.PdfReader(str(pdf)).pages[0].mediabox.width) / 72 - 7.2) < 0.01
    nums = list(csv.DictReader(open(str(out) + "_numbers.tsv"), delimiter="\t"))
    total = {r["site"]: int(r["isolates"]) for r in nums if r["group_or_genus"] == "ALL"}
    assert total == {"S1": 8, "S2": 5, "S3": 1}
    for s in total:   # groups and genera each sum to the site total
        assert sum(int(r["isolates"]) for r in nums if r["site"] == s and r["group_or_genus"].startswith("group:")) == total[s]
        assert sum(int(r["isolates"]) for r in nums if r["site"] == s and r["group_or_genus"].startswith("genus:")) == total[s]
    text = pypdf.PdfReader(str(pdf)).pages[0].extract_text()
    assert "second line" in text and "8 isolates" in text and "6 bryophyte, 2 lichen" in text
    info = json.loads(Path(str(out) + "_RUN_INFO.json").read_text())
    assert info["isolates"] == 14 and info["sites"] == 3 and len(info["inputs"]) == 3


def test_refuses_site_without_coordinates(tmp_path):
    iso, sites = _inputs(tmp_path, extra_site="NOWHERE")
    with pytest.raises(SystemExit) as e:
        cm.main(["--isolates", str(iso), "--sites", str(sites), "--basemap", str(_basemap(tmp_path)), "--out", str(tmp_path / "m")])
    assert e.value.code == 2


def test_refuses_site_outside_extent_and_overwrite(tmp_path):
    iso, sites = _inputs(tmp_path)
    base = ["--isolates", str(iso), "--sites", str(sites), "--basemap", str(_basemap(tmp_path))]
    with pytest.raises(SystemExit):
        cm.main(base + ["--out", str(tmp_path / "m1"), "--extent=-80,-70,35,45"])   # S3 lies east of -70
    assert cm.main(base + ["--out", str(tmp_path / "m2"), "--dpi", "100"]) == 0
    with pytest.raises(SystemExit):
        cm.main(base + ["--out", str(tmp_path / "m2"), "--dpi", "100"])


def test_legend_lists_only_present_genera(tmp_path):
    iso, sites = _inputs(tmp_path)
    out = tmp_path / "m"
    assert cm.main(["--isolates", str(iso), "--sites", str(sites), "--basemap", str(_basemap(tmp_path)),
                    "--out", str(out), "--pool-below", "1", "--dpi", "100"]) == 0
    text = " ".join(pypdf.PdfReader(str(out.with_suffix(".pdf"))).pages[0].extract_text().split())
    for g in ("Streptomyces", "Nocardia", "Kribbella", "No 16S genus on record"):
        assert g in text
    assert "Micromonospora" not in text and "Other genera" not in text
