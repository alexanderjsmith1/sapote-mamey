"""test_figures_embeds_svg.py — test for N3 (v9.7.149c).

`compile_report._figures()` previously walked only `*.png`. Now it walks both
PNG and SVG so locus_maps/*.svg from W5 get an `![...](path.svg)` reference
in §6 Figures.

Fixtures use AS-XXX only.
"""
from __future__ import annotations

import json
import pathlib

import pytest


def _bare_pkg(tmp_path: pathlib.Path,
              strain_id: str = "AS-XXX") -> pathlib.Path:
    pkg = tmp_path / strain_id / "package"
    pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": strain_id}))
    (pkg / "manifest_short.json").write_text(json.dumps(
        {"strain_id": strain_id}))
    return pkg


def test_figures_embeds_svg_files(tmp_path):
    """A package containing only SVG files (no PNG) should still get a §6
    Figures section with `![...]` image references — not a 'no figures' note."""
    from mamey.compile_report import _figures
    pkg = _bare_pkg(tmp_path)
    lm_dir = pkg / "locus_maps"
    lm_dir.mkdir()
    (lm_dir / "BGC001_locus_map.svg").write_text(
        '<?xml version="1.0"?>\n<svg xmlns="http://www.w3.org/2000/svg"/>')

    md = _figures(pkg, generate=False)
    assert "# 6. Figures" in md
    assert "![BGC001_locus_map]" in md
    assert "locus_maps/BGC001_locus_map.svg" in md
    assert "no figures in package" not in md


def test_figures_embeds_both_png_and_svg(tmp_path):
    """A mixed package with PNG and SVG should embed both — PNGs first, then
    SVGs (sorted within each group)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mamey.compile_report import _figures

    pkg = _bare_pkg(tmp_path)
    # Real PNG via matplotlib
    fig, ax = plt.subplots(figsize=(2, 2))
    ax.plot([0, 1], [0, 1])
    fig.savefig(pkg / "fig_chart.png", dpi=80)
    plt.close(fig)
    # SVG
    lm_dir = pkg / "locus_maps"
    lm_dir.mkdir()
    (lm_dir / "BGC001_locus_map.svg").write_text(
        '<?xml version="1.0"?>\n<svg xmlns="http://www.w3.org/2000/svg"/>')

    md = _figures(pkg, generate=False)
    assert "![fig_chart]" in md
    assert "![BGC001_locus_map]" in md


def test_figures_still_emits_no_figures_note_when_truly_empty(tmp_path):
    """A package with no PNG and no SVG — the existing 'no figures' note
    must still fire (regression check for N3)."""
    from mamey.compile_report import _figures
    pkg = _bare_pkg(tmp_path)
    md = _figures(pkg, generate=False)
    assert "no figures" in md.lower() or "No figures" in md
