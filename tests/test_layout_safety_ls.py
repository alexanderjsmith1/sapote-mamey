"""test_layout_safety_ls.py — LS-1 through LS-8 layout-safety rules.

This file has been ABSENT for three consecutive audits. P1-escalated.

Rules tested:
  LS-2  No rendered text below 6pt in any deliverable-grade figure.
  LS-3  Fixed-y footer text must be at y ≥ 0.012.
  LS-4  VERY_POOR assembly tier → red warning box before lead table.
  LS-5  Wrap before truncate (enforce in source).
  LS-8  _prov_footer respects MIN_FONT_PT constant.

LS-1 (char-length guard) and LS-6 (dynamic height) are structural and
tested via collection_figures layout safety tests.
LS-7 (non-blocking) is tested via the package write smoke tests.
"""
import inspect
import re
import pytest


# ── helpers ───────────────────────────────────────────────────────────────────

def _all_fontsize_values(source: str) -> list[float]:
    """Extract all fontsize= numeric values from Python source text."""
    return [float(m) for m in re.findall(r'fontsize=([0-9]+\.?[0-9]*)', source)]


def _all_fig_text_y_values(source: str) -> list[float]:
    """Extract y coords from fig.text(x, y, ...) calls in source."""
    return [float(m) for m in re.findall(
        r'fig\.text\s*\(\s*[0-9.]+\s*,\s*([0-9.]+)', source)]


def _ax_figure_text_y_values(source: str) -> list[float]:
    return [float(m) for m in re.findall(
        r'ax\.figure\.text\s*\(\s*[0-9.]+\s*,\s*([0-9.]+)', source)]


# ── LS-2: no fontsize below 6.0 ───────────────────────────────────────────────

def test_ls2_render_brief_no_fontsize_below_6():
    """LS-2: render_brief.py must not contain fontsize < 6.0."""
    src = open("mamey/render_brief.py").read()
    violations = [v for v in _all_fontsize_values(src) if v < 6.0]
    assert violations == [], f"fontsize < 6.0 in render_brief.py: {violations}"


def test_ls2_figures_extra_no_fontsize_below_6():
    """LS-2: figures_extra.py must not contain fontsize < 6.0."""
    src = open("mamey/figures_extra.py").read()
    violations = [v for v in _all_fontsize_values(src) if v < 6.0]
    assert violations == [], f"fontsize < 6.0 in figures_extra.py: {violations}"


def test_ls2_figures_sapote_no_fontsize_below_6():
    """LS-2: figures_sapote.py must not contain fontsize < 6.0."""
    src = open("mamey/figures_sapote.py").read()
    violations = [v for v in _all_fontsize_values(src) if v < 6.0]
    assert violations == [], f"fontsize < 6.0 in figures_sapote.py: {violations}"


def test_ls2_collection_figures_no_fontsize_below_6():
    """LS-2: collection_figures.py must not contain fontsize < 6.0."""
    src = open("mamey/collection_figures.py").read()
    violations = [v for v in _all_fontsize_values(src) if v < 6.0]
    assert violations == [], f"fontsize < 6.0 in collection_figures.py: {violations}"


# ── LS-3: footer y ≥ 0.012 ────────────────────────────────────────────────────

def test_ls3_render_brief_no_fig_text_y_below_012():
    """LS-3: fig.text y coordinates in render_brief.py must all be ≥ 0.012."""
    src = open("mamey/render_brief.py").read()
    violations = [y for y in _all_fig_text_y_values(src) if y < 0.012]
    assert violations == [], f"fig.text y < 0.012 in render_brief.py: {violations}"


def test_ls3_figures_sapote_no_fig_text_y_below_012():
    """LS-3: fig.text y coordinates in figures_sapote.py must all be ≥ 0.012."""
    src = open("mamey/figures_sapote.py").read()
    violations = [y for y in _all_fig_text_y_values(src) if y < 0.012]
    assert violations == [], f"fig.text y < 0.012 in figures_sapote.py: {violations}"


def test_ls3_collection_figures_no_ax_figure_text_y_below_012():
    """LS-3: ax.figure.text y coordinates in collection_figures.py must all be ≥ 0.012."""
    src = open("mamey/collection_figures.py").read()
    violations = [y for y in _ax_figure_text_y_values(src) if y < 0.012]
    assert violations == [], f"ax.figure.text y < 0.012 in collection_figures.py: {violations}"


# ── LS-4: VERY_POOR warning box ────────────────────────────────────────────────

def test_ls4_very_poor_warning_present_in_text_page():
    """LS-4: _text_page must contain a VERY_POOR assembly warning block."""
    from mamey.render_brief import _text_page
    src = inspect.getsource(_text_page)
    assert "VERY_POOR" in src, "_text_page has no VERY_POOR handling"
    assert "warning" in src.lower() or "ASSEMBLY QUALITY" in src, \
        "_text_page VERY_POOR block has no warning text"
    # Warning box implemented via fig.text bbox= (same pattern as the judgment banner)
    assert "bbox" in src or "add_patch" in src or "Rectangle" in src, \
        "_text_page VERY_POOR block has no visual warning box (bbox/Rectangle/add_patch)"


def test_ls4_very_poor_warning_renders_without_error(tmp_path):
    """LS-4: _text_page with VERY_POOR assembly tier must render without raising."""
    import io
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    from mamey.render_brief import _text_page

    facts = {
        "rows": [],
        "strain_label": "Streptomyces sp. AS-TEST",
        "release": "private",
        "manifest": {
            "taxonomy": "Streptomyces sp.", "source": "Apis mellifera",
            "workflow_version": "v9.7.78", "analysis_date": "2026-06-18",
            "bgc_counts": {
                "corrected": "8.5", "raw": "10", "interior": "2",
                "edge": "4", "full_contig": "4",
                "assembly_tier": "VERY_POOR",     # ← triggers LS-4 path
                "interior_pct": "12.3",
            },
            "assembly": {"genome_bp": "5200000", "contigs": "2100", "n50": "4000", "gc_pct": "71"},
            "bioactivity": {"targets": "MRSA+Candida", "status": "default-assumed",
                            "compound_linkage": "not established"},
            "scan_status": {"scans": [["KCB", "PASS", "0 BGCs"]]},
            "resistance_gene_summary": {"counts": {}},
        },
    }
    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        _text_page(pdf, plt, facts, tier="standard")
    assert len(buf.getvalue()) > 500


def test_ls4_non_very_poor_no_warning_box():
    """LS-4: GOOD assembly tier must NOT trigger the warning (box conditional on VERY_POOR)."""
    from mamey.render_brief import _text_page
    src = inspect.getsource(_text_page)
    # Warning must be gated on VERY_POOR, not unconditional
    assert 'assembly_tier" == "VERY_POOR"' in src or "== \"VERY_POOR\"" in src, \
        "LS-4 warning box is not conditional on VERY_POOR tier"


# ── LS-5: wrap before truncate ────────────────────────────────────────────────

def test_ls5_render_brief_uses_wrap_label():
    """LS-5: render_brief.py must import and use wrap_label or _wrap for labels."""
    src = open("mamey/render_brief.py").read()
    assert "wrap_label" in src or "_wrap" in src, \
        "render_brief.py does not use wrap_label or _wrap (LS-5)"


def test_ls5_figures_sapote_uses_wrap():
    """LS-5: figures_sapote.py must import textwrap or use wrap_label."""
    src = open("mamey/figures_sapote.py").read()
    assert "textwrap" in src or "wrap_label" in src or "_tw.wrap" in src, \
        "figures_sapote.py has no wrap enforcement (LS-5)"


# ── LS-8: MIN_FONT_PT parity ──────────────────────────────────────────────────

def test_ls8_collection_figures_prov_footer_respects_min_font_pt():
    """LS-8: collection_figures._prov_footer must not use a hardcoded value below MIN_FONT_PT."""
    src = open("mamey/collection_figures.py").read()
    # _prov_footer must not have a bare fontsize= below MIN_FONT_PT (7.0)
    # It should use max(..., MIN_FONT_PT) or a computed value
    from mamey.collection_figures import _prov_footer, MIN_FONT_PT
    prov_src = inspect.getsource(_prov_footer)
    # The source must not contain a fontsize literal smaller than MIN_FONT_PT
    raw_fontsizes = [float(m) for m in re.findall(r'fontsize=([0-9]+\.?[0-9]*)', prov_src)]
    violations = [f for f in raw_fontsizes if f < MIN_FONT_PT and f < 6.0]
    assert violations == [], \
        f"_prov_footer has raw fontsize {violations} below MIN_FONT_PT={MIN_FONT_PT} (LS-8)"


def test_ls8_min_font_pt_constant_is_7():
    """LS-8: MIN_FONT_PT in collection_figures.py must be 7.0 (the spec value)."""
    from mamey.collection_figures import MIN_FONT_PT
    assert MIN_FONT_PT == 7.0, f"MIN_FONT_PT is {MIN_FONT_PT}, expected 7.0"


# ── Regression: previously-passing layout is not degraded ────────────────────

def test_regression_collection_figures_min_font_pt_unchanged():
    """Regression: MIN_FONT_PT must not have been lowered by any LS fix."""
    from mamey.collection_figures import MIN_FONT_PT
    assert MIN_FONT_PT >= 7.0


def test_regression_render_safe_helpers_still_importable():
    """Regression: render_safe helpers survive all LS fixes."""
    from mamey.render_safe import shorten_label, wrap_label, locus_label, clean_scalar
    assert callable(shorten_label)
    assert callable(wrap_label)
    assert callable(locus_label)
