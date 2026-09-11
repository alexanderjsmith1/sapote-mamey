"""v9.7.422 — the rect02 placement figure must not truncate tip labels or the caption.

Premise (live-observed 2026-09-09 on the real attine Pseudonocardiaceae panel, rendered from the
sealed v9.7.421 template through R 4.5.3 / ggtree 4.0.4 / patchwork, 106 tips, SINGLE-page profile):

  1. DEAD KNOB. `tools/placement_display.py` — the only caller of this renderer — exports
     `GG_HEXPAND` (defaulting to "0.6") to control how much horizontal room the tree panel reserves
     for the aligned tip labels. The renderer never read it. Every other GG_* variable the driver
     sets is consumed; this one was not, so the label room could not be raised at all.
  2. TRUNCATED LABELS. The only reserve was the hardcoded estimate
     `max(0.38, max(nchar(disp)) * lsize / 200)`, which under-reserves: reference labels lost the
     end of their accession where the heatmap strip begins — "(NR_18" for NR_180167.1, and so on.
     Recalibrated to /90 against that panel and re-checked on a moss panel.
  3. CLIPPED CAPTION. patchwork aligns the caption strip to the PANEL region, not the whole figure
     width (the legend column sits outside it), so wrapping the caption at `w * 9` characters
     overran and it was cut mid-word. Wrapped to the panel share instead.

Presentation only: topology, rooting, placements, support and the display receipt are untouched.

Text-contract tests in the style of tests/test_410_r_figure_templates.py — parse the sources, do not
require an R runtime.
"""
from __future__ import annotations

import re
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[1] / "tools"
_R = _TOOLS / "ggtree_rect_heatmap.R"
_DRIVER = _TOOLS / "placement_display.py"          # not yet cut into the bundle; guarded below


def _hexpand_expr() -> str:
    src = _R.read_text(encoding="utf-8")
    m = re.search(r"ggtree::hexpand\(([^\n]*)\)", src)
    assert m, "no ggtree::hexpand(...) call found in ggtree_rect_heatmap.R"
    return m.group(1).strip()


def test_renderer_reads_gg_hexpand():
    """FAIL-BEFORE: the driver exported GG_HEXPAND and the renderer ignored it."""
    src = _R.read_text(encoding="utf-8")
    assert 'Sys.getenv("GG_HEXPAND")' in src, (
        "ggtree_rect_heatmap.R must read GG_HEXPAND — placement_display.py exports it to raise the "
        "tip-label room, and a knob the renderer ignores cannot fix a truncated label"
    )


def test_driver_exports_gg_hexpand_if_present():
    """Coupling guard: if the driver is in this bundle, it must still export what the renderer reads."""
    if not _DRIVER.exists():                      # placement_display.py is not cut into .421
        return
    assert "GG_HEXPAND" in _DRIVER.read_text(encoding="utf-8"), (
        "placement_display.py should export GG_HEXPAND; if it stops, revisit the renderer default"
    )


def test_label_room_divisor_is_calibrated():
    """FAIL-BEFORE: /200 under-reserved and truncated the longest reference labels."""
    src = _R.read_text(encoding="utf-8")
    m = re.search(r"nchar\(md\$disp[^)]*\)\)\s*\*\s*lsize\s*/\s*(\d+)", src)
    assert m, "expected a label-room estimate of the form max(nchar(disp)) * lsize / <divisor>"
    divisor = int(m.group(1))
    assert divisor <= 100, (
        f"label-room divisor is {divisor}; a larger divisor reserves LESS room, and /200 was "
        f"measured to truncate reference accessions at the heatmap edge"
    )


def test_hexpand_uses_the_computed_value_not_a_bare_constant():
    expr = _hexpand_expr()
    assert expr and not re.fullmatch(r"[0-9.]+", expr), (
        f"hexpand({expr}) must scale with the labels actually being drawn, not a fixed number"
    )


def test_caption_wraps_to_the_panel_share_not_the_figure_width():
    """FAIL-BEFORE: wrapped at w * 9, which overran the panel and clipped the caption."""
    src = _R.read_text(encoding="utf-8")
    m = re.search(r"floor\(w\s*\*\s*([0-9.]+)\)", src)
    assert m, "expected the caption wrap width to be derived from the figure width w"
    factor = float(m.group(1))
    assert factor < 9.0, (
        f"caption wrap factor is w * {factor}; patchwork aligns the caption to the panel region, "
        f"not the full figure width, so w * 9 overruns and the caption is clipped"
    )


def test_caption_wrap_is_overridable():
    src = _R.read_text(encoding="utf-8")
    assert 'Sys.getenv("GG_CAPTION_WRAP")' in src, (
        "the caption wrap width should be overridable without editing the template"
    )
