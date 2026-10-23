"""tools/gap_rescue_locus_map.py MAP_HEIGHT_IN and gap_directed_rescue --map-height (owner, 21 Oct, ruling 289, on the
maduropeptin map: "very crowded and the loci could be stretched vertically significantly").

The canvas height for the full y range was a literal 6.2 in, in four places. It is now one constant: the default draws
exactly as before, and a taller value stretches the map vertically at the same width."""
import importlib.util
import sys
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
spec = importlib.util.spec_from_file_location("labels447", ROOT / "tests" / "test_447_gap_rescue_locus_map_anchor_and_labels.py")
fx = importlib.util.module_from_spec(spec); spec.loader.exec_module(fx)
glm = fx.glm
_inspected_figures = fx._inspected_figures


def test_one_constant_replaces_the_literal_height():
    src = (ROOT / "tools" / "gap_rescue_locus_map.py").read_text()
    assert glm.MAP_HEIGHT_IN == 6.2
    assert "figsize=(fig_w, 6.2)" not in src and "6.2 * (y1 - y0)" not in src
    assert src.count("MAP_HEIGHT_IN * (y1 - y0) / 7.3") == 3


def test_a_taller_canvas_keeps_the_width(monkeypatch, tmp_path, _inspected_figures):
    base = fx._draw(monkeypatch, tmp_path, figs=_inspected_figures).get_size_inches()
    monkeypatch.setattr(glm, "MAP_HEIGHT_IN", 9.3)
    tall = fx._draw(monkeypatch, tmp_path, figs=_inspected_figures).get_size_inches()
    assert tall[0] == pytest.approx(base[0])
    # the page is trimmed to the drawn content afterwards, so it grows by less than 9.3 / 6.2 but clearly grows
    assert tall[1] > base[1] * 1.15


def test_cli_bounds_the_height(capsys):
    spec2 = importlib.util.spec_from_file_location("gdr457", ROOT / "tools" / "gap_directed_rescue.py")
    gdr = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(gdr)
    with pytest.raises(SystemExit) as e:
        gdr.main(["--zip", "x.zip", "--label", "S", "--redraw", "run", "--out", "o", "--map-height", "2"])
    assert e.value.code == 2 and "--map-height must be between 4 and 20" in capsys.readouterr().err
