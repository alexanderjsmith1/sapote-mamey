"""test_locus_map_labels_v9791.py — per-arrow ctgN_M locus labels (issue 2.3) + LS-2 coverage.

v9.7.91 adds a per-arrow assembly locus label below each gene in locus maps so every data point
ties to its ctgN_M locus tag. These tests pin that behaviour and extend the LS-2 (>=6pt) source
scan to locus_map.py — which the existing LS-2 suite did not cover (a latent gap caught in the
v9.7.90 audit).
"""
import re
import pathlib

import pytest as _pytest
_pytest.importorskip("matplotlib")  # SKIP (not error) when figure stack absent
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from mamey.locus_map import _draw_panel, _locus_suffix, LABEL_FONT_PT, SPARSE_MAX

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _row(locus_tag, start, end, core=True):
    return {"locus_tag": locus_tag, "start": start, "end": end, "strand": 1,
            "color": "#cccccc", "role": "other", "is_core": core,
            "length_aa": 100, "order": 1, "gene_functions": ""}


def test_locus_suffix_extracts_numeric_tail():
    assert _locus_suffix("ctg162_11") == "11"
    assert _locus_suffix("ctg1_7678") == "7678"
    assert _locus_suffix("nolocus") == "nolocus"


def test_every_arrow_gets_a_locus_label_sparse():
    rows = [_row(f"ctg162_{i}", i * 1000, i * 1000 + 800) for i in range(1, 6)]
    fig, ax = plt.subplots()
    _draw_panel(ax, rows, "BGC008 · NODE_162 · region001")
    texts = [t.get_text() for t in ax.texts]
    for i in range(1, 6):
        assert str(i) in texts, f"locus label {i} missing from sparse panel"
    plt.close(fig)


def test_dense_panel_rotates_labels_and_extends_ylim():
    rows = [_row(f"ctg8_{i}", i * 500, i * 500 + 300) for i in range(1, SPARSE_MAX + 6)]
    fig, ax = plt.subplots()
    _draw_panel(ax, rows, "BGC063 · NODE_8 · region001")
    # rotated 90deg locus labels present
    rotated = [t for t in ax.texts if t.get_rotation() == 90 and t.get_text().isdigit()]
    assert rotated, "dense panel should rotate per-arrow locus labels"
    assert ax.get_ylim()[0] <= -1.7, "dense panel should extend ylim for rotated labels"
    plt.close(fig)


def test_locus_label_font_is_ls2_compliant():
    assert LABEL_FONT_PT >= 6.0, "LS-2: per-arrow locus label font must be >= 6.0pt"


def test_ls2_locus_map_no_fontsize_below_6():
    """LS-2 extension: locus_map.py must not contain fontsize < 6.0 (was not covered before v9.7.91)."""
    src = (ROOT / "mamey" / "locus_map.py").read_text(encoding="utf-8")
    vals = [float(v) for v in re.findall(r"fontsize=([0-9]+\.?[0-9]*)", src)]
    violations = [v for v in vals if v < 6.0]
    assert violations == [], f"fontsize < 6.0 in locus_map.py: {violations}"


# ── LOCUS_MAP_RENDER (v9.7.122) — display-geometry label suppression ───────────
from mamey.locus_map import _label_visible, render_locus_map  # noqa: E402


def test_label_visible_unit():
    # sparse panels always show every label
    assert _label_visible(50, 100000, dense=False) is True
    # dense: a 164 bp gene in a 100 kb span is too narrow for a label
    assert _label_visible(164, 100000, dense=True) is False
    # dense: a megasynthase-width gene (2248 bp) keeps its label
    assert _label_visible(2248, 100000, dense=True) is True
    # degenerate span never crashes
    assert _label_visible(100, 0, dense=True) is False


def test_very_dense_panel_suppresses_narrow_labels():
    # 71 narrow genes packed into ~100 kb — the overlap-wall case (BGC033-class)
    rows = [_row(f"ctg4_{i}", i * 1400, i * 1400 + 164) for i in range(1, 72)]
    fig, ax = plt.subplots()
    _draw_panel(ax, rows, "BGC033 · NODE_4 · region001")
    drawn = [t for t in ax.texts if t.get_text().isdigit()]
    assert len(drawn) < 71, "narrow labels on a very-dense panel must be suppressed"
    # very-dense panels get the widest bottom margin
    assert ax.get_ylim()[0] <= -2.4
    plt.close(fig)


def test_csv_records_every_gene_despite_label_suppression(tmp_path):
    # invariant: suppressed labels still appear in the companion CSV
    rows = [_row(f"ctg4_{i}", i * 1400, i * 1400 + 164) for i in range(1, 72)]
    png = tmp_path / "m.png"
    csvp = tmp_path / "m.csv"
    render_locus_map([("BGC033 · NODE_4", rows)], str(png), str(csvp),
                     suptitle="STRAINX — BGC033 locus", claim_prefix="PRIVATE")
    body = csvp.read_text(encoding="utf-8")
    # every gene's locus suffix should be present in the CSV regardless of label visibility
    for i in range(1, 72):
        assert f"ctg4_{i}" in body, f"ctg4_{i} missing from CSV"
