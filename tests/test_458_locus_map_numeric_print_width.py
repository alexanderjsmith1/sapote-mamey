"""The locus map takes a print width in inches, so it can match the width it is placed at, and the
"gap" mark meets the 8 pt floor in every layout.

Before: only named widths (3.5, 6.0, 6.5, 7.2, 9.0 in) were accepted, so a map placed at 7.99 or 5.85 in
was drawn at another width and scaled on the page; and the gap mark was 7 pt in the screen layout.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
spec = importlib.util.spec_from_file_location("gap_rescue_locus_map_458w", ROOT / "tools" / "gap_rescue_locus_map.py")
glm = importlib.util.module_from_spec(spec); spec.loader.exec_module(glm)

REF = [{"i": i + 1, "name": f"madA{i}", "product": "biosynthetic enzyme", "kind": "biosynthetic",
        "s": i * 1.6, "e": i * 1.6 + 1.4, "strand": 1} for i in range(10)]


def _draw(monkeypatch, tmp_path, print_width):
    monkeypatch.setattr(glm, "reference_genes", lambda _p: (REF, REF[-1]["e"] + 0.5))
    prots, rows = {}, []
    for k, g in enumerate(REF):
        start = 5000 + int(g["s"] * 1000)
        prots[f"p{k}"] = {"tag": f"core_{k}", "contig": "core", "start": start,
                          "end": start + int((g["e"] - g["s"]) * 1000), "strand": 1, "contig_len": 90000}
        rows.append({"status": "PRESENT_IN_CORE", "best_protein": f"p{k}", "best_identity_pct": 80.0,
                     "reciprocal_best": True, "partner_verdict": ""})
    core = {"contig": "core", "start": 4000, "end": 24000, "identity": "AS-0 / core / region001 / BGC001"}
    out = tmp_path / f"m_{print_width}.png"
    return glm.draw_locus_map(tmp_path / "BGC0000000.gbk", rows, [], prots, [core], core, "AS-0", "test", out,
                              print_width=print_width), out


def test_named_and_numeric_widths():
    assert glm.print_width_inches("double") == 7.2
    assert glm.print_width_inches("7.99") == 7.99
    assert glm.print_width_inches(5.85) == 5.85
    assert glm.print_width_inches(None) is None
    for bad in ("wide", "2.0", "12", float("nan")):
        with pytest.raises(ValueError):
            glm.print_width_inches(bad)


@pytest.mark.parametrize("width", ["7.99", "5.85"])
def test_a_map_drawn_at_its_placed_width_keeps_8_pt_text(monkeypatch, tmp_path, width):
    from PIL import Image
    res, out = _draw(monkeypatch, tmp_path, width)
    assert res["print_width_in"] == float(width)
    assert res["min_font_pt"] >= 8.0
    with Image.open(out) as im:
        assert im.size[0] / 300.0 <= float(width) + 0.02


def test_gap_mark_is_set_at_the_floor():
    src = (ROOT / "tools" / "gap_rescue_locus_map.py").read_text()
    assert 'ha="center", va="bottom", fontsize=fs(8), color="#B91C1C")' in src
