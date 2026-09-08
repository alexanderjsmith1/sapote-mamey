"""test_collection_figure_layout_safety.py — v9.7.69

Tests for layout-safety rules FB-1 through FB-9.
"""
import os
import csv
import pytest
from pathlib import Path
import pytest as _pytest
_pytest.importorskip("matplotlib")  # SKIP (not error) when figure stack absent
import matplotlib
matplotlib.use("Agg")

from mamey.collection_figures import (
    render_collection_figures, _wrap, _dynamic_height, MAX_BAR_ROWS, MIN_FONT_PT
)


# ── FB-3 long label wrapping ──────────────────────────────────────────────────

def test_wrap_short_label_unchanged():
    assert _wrap("Streptomyces") == "Streptomyces"

def test_wrap_long_label_bounded():
    long = "Verrucosispora gifhornensis subsp. gifhornensis strain NRRL WC-3721"
    result = _wrap(long, width=22)
    for line in result.split("\n"):
        assert len(line) <= 23, f"line too long: {line!r}"

def test_wrap_adds_ellipsis_for_3plus_lines():
    long = "Very Long Genus Name Species Epithet Subsp Var Form Strain"
    result = _wrap(long, width=12, )
    assert result.endswith("…") or len(result.split("\n")) <= 2


# ── FB-1/FB-4 dynamic height ─────────────────────────────────────────────────

def test_dynamic_height_min():
    assert _dynamic_height(1) >= 3.0

def test_dynamic_height_max():
    assert _dynamic_height(200) <= 14.0

def test_dynamic_height_scales_with_rows():
    assert _dynamic_height(10) < _dynamic_height(30)


# ── FB-2 top-N cap ────────────────────────────────────────────────────────────

def test_top_n_cap_on_many_genera(tmp_path):
    """Bar chart must not show more than MAX_BAR_ROWS + 'other' bars."""
    rows = [{"strain_id": f"AS-{i}", "genus": f"Genus_{i:03d}"} for i in range(50)]
    result = render_collection_figures(rows, tmp_path)
    gen_ids = {Path(p).stem for p in result["generated"]}
    assert "fig_top_genera" in gen_ids
    # Read sidecar CSV to verify top-N constraint
    csv_path = tmp_path / "fig_top_genera_data.csv"
    if csv_path.exists():
        data = list(csv.reader(open(csv_path)))[2:]  # skip provenance + header
        # Should be at most MAX_BAR_ROWS + 1 (for "other")
        assert len(data) <= MAX_BAR_ROWS + 1, f"Too many bars: {len(data)}"


# ── FB-8 export pair ──────────────────────────────────────────────────────────

def test_every_generated_figure_has_sidecar_csv(tmp_path):
    """FB-8: each figure must have a _data.csv sidecar."""
    rows = [{"strain_id": f"AS-{i}", "genus": "Streptomyces",
             "source": "bee" if i < 3 else "moss"} for i in range(6)]
    result = render_collection_figures(rows, tmp_path)
    for png in result["generated"]:
        csv_path = png.replace(".png", "_data.csv")
        assert os.path.exists(csv_path), f"missing sidecar for {png}"


# ── FB-9 stable lowercase filenames ──────────────────────────────────────────

def test_output_filenames_are_lowercase(tmp_path):
    rows = [{"strain_id": f"AS-{i}", "genus": "Streptomyces"} for i in range(3)]
    result = render_collection_figures(rows, tmp_path)
    for png in result["generated"]:
        assert Path(png).name == Path(png).name.lower(), f"not lowercase: {png}"


# ── FB-6 provenance footer (structural: file exists and has content) ──────────

def test_generated_figures_exist_and_nonzero(tmp_path):
    rows = [{"strain_id": f"AS-{i}"} for i in range(3)]
    result = render_collection_figures(rows, tmp_path)
    for png in result["generated"]:
        assert Path(png).exists()
        assert Path(png).stat().st_size > 1000


# ── FB-7 non-blocking skip ────────────────────────────────────────────────────

def test_missing_field_never_raises(tmp_path):
    """Missing required fields must produce a skip, not an exception."""
    rows = [{"strain_id": "AS-XXX", "genus": "Streptomyces"}]
    try:
        result = render_collection_figures(rows, tmp_path)
    except Exception as e:
        pytest.fail(f"render_collection_figures raised: {e}")


# ── Sidecar CSV provenance schema (Item-18 compliant) ─────────────────────────

def test_sidecar_csv_has_provenance_row(tmp_path):
    rows = [{"strain_id": f"AS-{i}", "genus": "Streptomyces"} for i in range(3)]
    result = render_collection_figures(rows, tmp_path)
    for png in result["generated"]:
        csv_path = png.replace(".png", "_data.csv")
        if os.path.exists(csv_path):
            rows_c = list(csv.reader(open(csv_path)))
            assert rows_c[0][0] == "# provenance", f"missing provenance: {csv_path}"
            break
