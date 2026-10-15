"""v9.7.452: tools/collection_map.py --legend-title sets the key title (for a key that also lists a family-level name),
--frame draws a line round the map extent, and the defaults are unchanged. Synthetic sites and isolates (SYN-*) on a synthetic shapefile."""
import importlib.util
import json
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
shapefile = pytest.importorskip("shapefile")
pypdf = pytest.importorskip("pypdf")
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("collection_map_k", ROOT / "tools/collection_map.py")
cm = importlib.util.module_from_spec(spec); spec.loader.exec_module(cm)


def _inputs(tmp):
    w = shapefile.Writer(str(tmp / "land"), shapeType=shapefile.POLYGON)
    w.field("name", "C"); w.poly([[(-80, 35), (-62, 35), (-62, 47), (-80, 47), (-80, 35)]]); w.record("A"); w.close()
    (tmp / "sites.tsv").write_text("site\tlabel\tlat\tlon\nS1\tSite one\t44.0\t-78.0\nS2\tSite two\t41.0\t-66.0\n")
    rows = [("SYN-01", "S1", "Source A", "Genusa"), ("SYN-02", "S1", "Source A", "Familiaceae"),
            ("SYN-03", "S2", "Source A", "Genusa"), ("SYN-04", "S2", "Source A", "Familiaceae")]
    (tmp / "isolates.tsv").write_text("isolate\tsite\tgroup\tgenus\n" + "".join("\t".join(r) + "\n" for r in rows))
    return ["--isolates", str(tmp / "isolates.tsv"), "--sites", str(tmp / "sites.tsv"), "--basemap", str(tmp / "land.shp"),
            "--pool-below", "1", "--dpi", "100"]


def _text(stem):
    return " ".join(pypdf.PdfReader(str(stem.with_suffix(".pdf"))).pages[0].extract_text().split())


def test_legend_title_option(tmp_path):
    base = _inputs(tmp_path)
    out = tmp_path / "m"
    assert cm.main(base + ["--out", str(out), "--legend-title", "Genus (16S rRNA; family where the genus is unresolved)"]) == 0
    assert "family where the genus is unresolved" in _text(out)
    assert json.loads(Path(str(out) + "_RUN_INFO.json").read_text())["legend_title"].startswith("Genus (16S rRNA; family")


@pytest.mark.parametrize("mark,title", [("pie", "Genus (16S rRNA)"), ("circle", "Isolation source")])
def test_default_titles_unchanged(tmp_path, mark, title):
    base = _inputs(tmp_path)
    out = tmp_path / f"d_{mark}"
    assert cm.main(base + ["--out", str(out), "--mark", mark]) == 0
    assert json.loads(Path(str(out) + "_RUN_INFO.json").read_text())["legend_title"] == title
    assert title in _text(out)


def test_frame_option_recorded_and_default_off(tmp_path):
    base = _inputs(tmp_path)
    assert cm.main(base + ["--out", str(tmp_path / "f"), "--frame"]) == 0
    assert json.loads(Path(str(tmp_path / "f") + "_RUN_INFO.json").read_text())["frame"] is True
    assert cm.main(base + ["--out", str(tmp_path / "n")]) == 0
    assert json.loads(Path(str(tmp_path / "n") + "_RUN_INFO.json").read_text())["frame"] is False
