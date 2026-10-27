"""Card 462_panel_key_fits_page_width: the shared gene-class key of gap_rescue_panel_figure.py stays inside a
6.5 in page (it ran off the right edge with long labels such as "biosynthetic core" and "class unclear"), and a single
map can be drawn as a figure of its own without a panel letter (--no-letter). Synthetic blank maps; no DIAMOND."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
HERE = Path(__file__).resolve().parents[1]
TOOLS = HERE / "tools"
sys.path.insert(0, str(TOOLS))


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pf = _load(TOOLS / "gap_rescue_panel_figure.py", "gap_rescue_panel_figure_462")
ALL = ["biosynthetic core", "tailoring", "regulator", "transport", "housekeeping", "other", "hypothetical"]


def _maps(tmp_path, n, classes, unclear=True):
    from PIL import Image
    out = []
    for i in range(n):
        d = tmp_path / f"m{i}"; d.mkdir()
        Image.new("RGB", (1950, 900), "white").save(d / "gap_rescue.png", dpi=(300, 300))
        (d / "gap_rescue_key.json").write_text(json.dumps({"classes": classes, "class_unclear": unclear,
                                                            "key": False, "gecco": True}))
        out.append(d)
    return out


def _legend_right_in(fig):
    fig.canvas.draw()
    return max(leg.get_window_extent().x1 for leg in fig.legends) / fig.dpi


def test_full_key_stays_inside_a_6p5_in_page(tmp_path):
    import matplotlib.pyplot as plt
    maps = pf.read_maps(_maps(tmp_path, 1, ALL))
    fig, H = pf.draw_page(maps, [0], "a", 6.5, True, ALL, True, True)
    assert _legend_right_in(fig) <= 6.5
    assert H == pytest.approx(3.0 + pf.key_height(len(ALL) + 1, 3) + pf.GECCO_KEY_H, abs=0.01)
    plt.close(fig)


def test_short_key_keeps_four_columns(tmp_path):
    import matplotlib.pyplot as plt
    maps = pf.read_maps(_maps(tmp_path, 1, ["tailoring"], unclear=False))
    fig, H = pf.draw_page(maps, [0], "a", 7.2, True, ["tailoring"], False, True)
    assert H == pytest.approx(3.0 + pf.key_height(1) + pf.GECCO_KEY_H, abs=0.01)
    plt.close(fig)


def test_no_letter_for_a_single_map_only(tmp_path):
    one = _maps(tmp_path, 1, ["tailoring"])
    info = pf.compose(one, tmp_path / "solo", letters="a", width_in=6.5, show_letters=False)
    assert len(info["pages"]) == 1
    import matplotlib.pyplot as plt
    fig, _ = pf.draw_page(pf.read_maps(one), [0], "a", 6.5, True, ["tailoring"], True, True, show_letters=False)
    assert "a" not in [t.get_text() for t in fig.texts]
    plt.close(fig)
    two_dir = tmp_path / "two"; two_dir.mkdir()
    two = _maps(two_dir, 2, ["tailoring"])
    with pytest.raises(pf.PanelFigureError):
        pf.compose(two, tmp_path / "duo", letters="ab", width_in=6.5, show_letters=False)
