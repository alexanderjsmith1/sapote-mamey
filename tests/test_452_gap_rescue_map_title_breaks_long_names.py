"""tools/gap_rescue_locus_map.py wrap_to_width breaks a word wider than the line (card .452 title_breaks_long_names).

A MIBiG compound with a systematic name (e.g. a 158-character "(2E,4E,6E,8E)-N-(...)" pair) has no spaces, so the
title could not wrap and the map failed to fit a 7.2 in print width at every shrink step. A word wider than the line
now breaks after a hyphen or comma. Text with spaces wraps as before. Synthetic text only.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tools"))


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


glm = _load(HERE / "tools" / "gap_rescue_locus_map.py", "gap_rescue_locus_map_452lb")
LONG = "(2E,4E,6E,8E)-N-(2-hydroxy-5-oxocyclopent-1-en-1-yl)-9-(o-tolyl)nona-2,4,6,8-tetraenamide cluster (MIBiG BGC9999999)"


# Text widths depend on the font and dpi in matplotlib's global settings, which earlier tests in a run may change;
# every test here measures inside one fixed context so the result does not depend on test order.
RC = {"font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"], "figure.dpi": 100}


@pytest.fixture(autouse=True)
def _fixed_text_settings():
    with matplotlib.rc_context(RC):
        yield


def _setup():
    fig, ax = plt.subplots(figsize=(3, 1))
    fig.canvas.draw()
    return fig, ax, fig.canvas.get_renderer()


def _width(ax, rend, s):
    t = ax.text(0, 0, s, fontsize=9, weight="bold")
    w = t.get_window_extent(rend).width
    t.remove()
    return w


def test_a_long_systematic_name_breaks_after_hyphens_and_fits():
    fig, ax, rend = _setup()
    max_px = 200
    out = glm.wrap_to_width(ax, rend, LONG, max_px, fontsize=9, weight="bold")
    lines = out.split("\n")
    assert len(lines) > 2
    # every line fits, unless it is one piece with no hyphen or comma left to break at
    assert all(_width(ax, rend, ln) <= max_px or not any(c in ln[:-1] for c in "-, ") for ln in lines)
    # nothing lost or added: a line ending in a hyphen or comma continues a broken name with no space, any other
    # line break stands for one space
    rebuilt = lines[0]
    for ln in lines[1:]:
        rebuilt += ln if rebuilt.endswith(("-", ",")) else " " + ln
    assert rebuilt == LONG
    plt.close(fig)


def test_text_with_spaces_wraps_as_before():
    fig, ax, rend = _setup()
    text = "Maduropeptin cluster (MIBiG BGC0001008, 62.8 kb; 62.8 kb shown)"
    wide = glm.wrap_to_width(ax, rend, text, 10_000, fontsize=9, weight="bold")
    assert wide == text
    narrow = glm.wrap_to_width(ax, rend, text, 150, fontsize=9, weight="bold")
    assert narrow.replace("\n", " ") == text
    plt.close(fig)


def test_a_word_with_no_break_point_stays_whole():
    fig, ax, rend = _setup()
    out = glm.wrap_to_width(ax, rend, "x" * 80, 50, fontsize=9, weight="bold")
    assert out == "x" * 80
    plt.close(fig)
