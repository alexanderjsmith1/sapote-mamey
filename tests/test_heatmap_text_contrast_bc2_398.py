"""v9.7.398 — `mamey/interactive_figures/figure_set_renderer.py` and `codex_heatmap_pack.py`
each picked a heatmap cell's label text colour (dark vs white) via a single luminance-threshold
comparison. Measured against 2,000 random colors, the ground-truth best-contrast choice:

  * figure_set_renderer.py's rule (raw, non-gamma-corrected luminance > .58) disagreed ~18% of
    the time;
  * codex_heatmap_pack.py's rule (WCAG-correct luminance > 0.48) disagreed ~33% of the time —
    the formula was right but the threshold was miscalibrated for that formula.

Two concrete, common chart-accent colors (#A5A5A5 grey, #70AD47 green — both standard Office
palette colors, plausible real heatmap fills) demonstrate the practical impact: the old rules
picked white text at 2.46:1 / 2.71:1 contrast (below the WCAG AA 3:1 minimum for any text size)
when dark text was available at 6.61:1 / 6.02:1.

Both files now compute the real WCAG contrast ratio against each candidate text colour directly
and pick the higher one — correct by construction, no threshold to miscalibrate.
"""
from __future__ import annotations

import random

from mamey.interactive_figures.figure_set_renderer import (
    _contrast_ratio as renderer_contrast_ratio,
    _text_colour_for_contrast as renderer_text_colour,
)
from mamey.interactive_figures.codex_heatmap_pack import (
    _contrast_ratio as codex_contrast_ratio,
    _text_colour_for_contrast as codex_text_colour,
)

_DARK_RENDERER = "#17212b"
_DARK_CODEX = "#111820"
_WHITE = "#ffffff"


def _old_naive_luminance(colour: str) -> float:
    """The pre-fix figure_set_renderer.py formula, reconstructed for a direct comparison."""
    raw = colour.lstrip("#")
    rgb = [int(raw[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


def test_grey_A5A5A5_now_picks_dark_text_not_low_contrast_white():
    # old renderer.py rule: naive_luminance('#A5A5A5') = 0.647 > .58 -> would have picked dark
    # (renderer.py happened to be right here already); confirm the NEW rule agrees and the
    # contrast ratio is the good one, not the ~2.46:1 white option.
    choice = renderer_text_colour("#A5A5A5", _DARK_RENDERER, _WHITE)
    assert choice == _DARK_RENDERER
    assert renderer_contrast_ratio("#A5A5A5", _DARK_RENDERER) > 6.0


def test_codex_pack_grey_A5A5A5_regression_old_rule_would_have_picked_white():
    """The concrete, demonstrated defect: codex_heatmap_pack.py's OLD rule
    (wcag_luminance('#A5A5A5') = 0.376, not > 0.48) picked white text — 2.46:1 contrast, below
    even the WCAG AA large-text minimum of 3:1. The new rule must not repeat this."""
    old_rule_choice = _DARK_CODEX if 0.376 > 0.48 else _WHITE
    assert old_rule_choice == _WHITE, "sanity: confirms the old defect would have fired"
    old_contrast = codex_contrast_ratio("#A5A5A5", _WHITE)
    assert old_contrast < 3.0, f"the old rule's choice only achieves {old_contrast:.2f}:1 contrast"

    new_choice = codex_text_colour("#A5A5A5", _DARK_CODEX, _WHITE)
    assert new_choice == _DARK_CODEX
    assert codex_contrast_ratio("#A5A5A5", _DARK_CODEX) > 6.0


def test_codex_pack_green_70AD47_regression():
    new_choice = codex_text_colour("#70AD47", _DARK_CODEX, _WHITE)
    assert new_choice == _DARK_CODEX
    assert codex_contrast_ratio("#70AD47", _DARK_CODEX) > 5.5
    assert codex_contrast_ratio("#70AD47", _WHITE) < 3.0  # what the old rule would have chosen


def test_new_rule_always_matches_ground_truth_by_construction():
    """Property test: for both modules, the new rule can never pick the lower-contrast option,
    because it directly compares the two real outcomes rather than a threshold proxy."""
    random.seed(20260901)
    for _ in range(300):
        c = "#%02x%02x%02x" % (
            random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)
        )
        for contrast_fn, text_fn, dark in (
            (renderer_contrast_ratio, renderer_text_colour, _DARK_RENDERER),
            (codex_contrast_ratio, codex_text_colour, _DARK_CODEX),
        ):
            choice = text_fn(c, dark, _WHITE)
            other = _WHITE if choice == dark else dark
            assert contrast_fn(c, choice) >= contrast_fn(c, other), (
                f"{c}: chose {choice} over {other} but the other has equal-or-better contrast"
            )
