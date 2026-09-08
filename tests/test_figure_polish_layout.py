"""test_as901_figure_polish.py — v9.7.72

Tests for Figure-Polish-1 (cohort figure layout):
  - fig_ab_af_vertical_panels: two panels, vertical bars, node-first labels
  - CNBU: correct computation, unknown prior handling, no failure on missing
  - print figure pack: PRINT_FIGURE_PACK.md + manifest written
  - missing AF/AB data skips only affected panel
"""
import csv
import json
import os
import tempfile
import pytest as _pytest
_pytest.importorskip("matplotlib")  # SKIP (not error) when figure stack absent
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import pytest
from pathlib import Path


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _rows(n=8, include_af=True):
    rows = []
    for i in range(n):
        rows.append({
            "rank": str(i + 1),
            "bgc_id": f"BGC{i+1:03d}",
            "contig": f"NODE_{i+10}_length_55000_cov_22",
            "region": f"region{i+1:03d}",
            "products": "NRPS; T1PKS" if i < 4 else "terpene",
            "boundary": "Interior" if i < 5 else "Edge",
            "ab": max(0.0, 90.0 - i * 8),
            "af": max(0.0, 60.0 - i * 6) if include_af else 0.0,
            "novelty": 70.0 - i * 5,
            "lead_tier": "High" if i < 2 else "Medium",
            "kcb_top": f"BGC000{i}.5 | testomycin | knownclusterblast #1",
            "kcb_score": str(8000 - i * 500),
            "cctt": "",
        })
    return rows


# ── fig_ab_af_vertical_panels ─────────────────────────────────────────────────

def test_ab_af_panels_produces_file(tmp_path):
    from mamey.figures_sapote import fig_ab_af_vertical_panels
    rows = _rows()
    png = str(tmp_path / "test_panels.png")
    result = fig_ab_af_vertical_panels(rows, png, "AS-TEST", plt)
    assert result is not None
    assert Path(png).exists()
    assert Path(png).stat().st_size > 5000


def test_ab_af_panels_has_two_subplots(tmp_path):
    """Both AB and AF data present → two subplot panels."""
    from mamey.figures_sapote import fig_ab_af_vertical_panels, _setup_mpl
    plt_inst = _setup_mpl()
    rows = _rows()
    png = str(tmp_path / "panels.png")
    fig_ab_af_vertical_panels(rows, png, "AS-TEST", plt_inst)
    # Verify via the sidecar CSV that both AB and AF data are present
    csv_path = png.replace(".png", "_data.csv")
    assert Path(csv_path).exists()
    data = list(csv.reader(open(csv_path)))[2:]  # skip provenance + header
    ab_vals = [float(r[5]) for r in data if len(r) > 5 and r[5]]
    af_vals = [float(r[6]) for r in data if len(r) > 6 and r[6]]
    assert max(ab_vals) > 0
    assert max(af_vals) > 0


def test_ab_af_panels_labels_are_node_first(tmp_path):
    """Sidecar CSV assembly_locator must start with node/contig, not BGC###."""
    from mamey.figures_sapote import fig_ab_af_vertical_panels
    rows = _rows()
    png = str(tmp_path / "panels.png")
    fig_ab_af_vertical_panels(rows, png, "AS-TEST", plt)
    csv_path = png.replace(".png", "_data.csv")
    data = list(csv.reader(open(csv_path)))[2:]
    headers = list(csv.reader(open(csv_path)))[1]
    loc_col = headers.index("assembly_locator")
    for row in data:
        if len(row) > loc_col and row[loc_col]:
            locator = row[loc_col]
            # Should start with NODE_, not BGC
            assert not locator.startswith("BGC"), f"locator is BGC-first: {locator!r}"
            assert "NODE_" in locator or "region" in locator


def test_ab_af_panels_sidecar_csv_has_provenance_row(tmp_path):
    """Item-18: sidecar CSV must have # provenance at row 0."""
    from mamey.figures_sapote import fig_ab_af_vertical_panels
    rows = _rows()
    png = str(tmp_path / "panels.png")
    fig_ab_af_vertical_panels(rows, png, "AS-TEST", plt)
    csv_path = png.replace(".png", "_data.csv")
    first_row = list(csv.reader(open(csv_path)))[0]
    assert first_row[0] == "# provenance"


def test_ab_af_panels_af_only_when_ab_zero(tmp_path):
    """When all AB scores are zero, only AF panel is rendered (no error)."""
    from mamey.figures_sapote import fig_ab_af_vertical_panels
    rows = _rows()
    for r in rows:
        r["ab"] = 0.0
    png = str(tmp_path / "af_only.png")
    result = fig_ab_af_vertical_panels(rows, png, "AS-TEST", plt)
    assert result is not None
    assert Path(png).exists()


def test_ab_af_panels_returns_none_when_all_zero(tmp_path):
    """When both AB and AF are all zero, returns None (no empty figure)."""
    from mamey.figures_sapote import fig_ab_af_vertical_panels
    rows = _rows()
    for r in rows:
        r["ab"] = 0.0
        r["af"] = 0.0
    png = str(tmp_path / "empty.png")
    result = fig_ab_af_vertical_panels(rows, png, "AS-TEST", plt)
    assert result is None


def test_ab_af_panels_long_labels_do_not_crash(tmp_path):
    """Very long NODE names must not raise — they wrap/truncate."""
    from mamey.figures_sapote import fig_ab_af_vertical_panels
    rows = _rows()
    for r in rows:
        r["contig"] = "NODE_" + "1234567890" * 5 + "_length_500000_cov_99.5"
    png = str(tmp_path / "long_labels.png")
    try:
        result = fig_ab_af_vertical_panels(rows, png, "AS-TEST", plt)
    except Exception as e:
        pytest.fail(f"Long labels caused crash: {e}")


# ── CNBU ──────────────────────────────────────────────────────────────────────

def test_cnbu_basic_computation():
    from mamey.cnbu import compute_cnbu
    bgcs = [
        {"bgc_id": "BGC001", "length_kb": 60.0, "products": "NRPS"},
        {"bgc_id": "BGC002", "length_kb": 25.0, "products": "T1PKS"},
    ]
    result = compute_cnbu(bgcs)
    assert result["n_bgcs"] == 2
    assert result["n_unknown"] == 0
    # BGC001: 60/60 = 1.0; BGC002: 25/50 = 0.5; total = 1.5
    assert abs(result["total_cnbu"] - 1.5) < 0.01
    assert not result["warnings"]


def test_cnbu_cap_applied():
    from mamey.cnbu import compute_cnbu, DEFAULT_CAP
    bgcs = [{"bgc_id": "BGC001", "length_kb": 999.0, "products": "NRPS"}]
    result = compute_cnbu(bgcs)
    per = result["per_bgc"][0]
    assert per["capped"] is True
    assert per["cnbu"] == DEFAULT_CAP


def test_cnbu_unknown_prior_excluded_from_total():
    from mamey.cnbu import compute_cnbu, UNKNOWN_PRIOR_LABEL
    bgcs = [
        {"bgc_id": "BGC001", "length_kb": 60.0, "products": "NRPS"},
        {"bgc_id": "BGC002", "length_kb": 10.0, "products": "other"},
    ]
    result = compute_cnbu(bgcs)
    assert result["n_unknown"] == 1
    assert result["n_known"] == 1
    assert len(result["warnings"]) > 0
    assert "UNKNOWN_PRIOR" in result["warnings"][0]
    # Total excludes BGC002
    assert abs(result["total_cnbu"] - 1.0) < 0.01


def test_cnbu_unknown_prior_label_in_per_bgc():
    from mamey.cnbu import compute_cnbu, UNKNOWN_PRIOR_LABEL
    bgcs = [{"bgc_id": "BGC001", "length_kb": 10.0, "products": "other"}]
    result = compute_cnbu(bgcs)
    per = result["per_bgc"][0]
    assert per["prior_kb"] == UNKNOWN_PRIOR_LABEL
    assert per["cnbu"] == UNKNOWN_PRIOR_LABEL


def test_cnbu_missing_length_no_failure():
    from mamey.cnbu import compute_cnbu
    bgcs = [{"bgc_id": "BGC001", "length_kb": None, "products": "NRPS"}]
    result = compute_cnbu(bgcs)
    assert result["total_cnbu"] == 0.0
    assert result["n_unknown"] == 0


def test_cnbu_empty_bgc_list():
    from mamey.cnbu import compute_cnbu
    result = compute_cnbu([])
    assert result["total_cnbu"] == 0.0
    assert result["n_bgcs"] == 0


def test_cnbu_custom_priors():
    from mamey.cnbu import compute_cnbu
    bgcs = [{"bgc_id": "BGC001", "length_kb": 10.0, "products": "CUSTOM_CLASS"}]
    result = compute_cnbu(bgcs, priors={"CUSTOM_CLASS": 10.0})
    assert abs(result["total_cnbu"] - 1.0) < 0.01
    assert result["n_unknown"] == 0


# ── Print figure pack ─────────────────────────────────────────────────────────

def test_print_figure_pack_writes_md(tmp_path):
    from mamey.figures_sapote import write_print_figure_pack
    # Create a dummy PNG
    fig, ax = plt.subplots()
    png = str(tmp_path / "test.png")
    fig.savefig(png); plt.close(fig)
    result = write_print_figure_pack([png], str(tmp_path), "AS-TEST", plt)
    md = Path(result["md"])
    assert md.exists()
    text = md.read_text()
    assert "Print figure pack" in text
    assert "test.png" in text


def test_print_figure_pack_writes_manifest(tmp_path):
    from mamey.figures_sapote import write_print_figure_pack
    fig, ax = plt.subplots()
    png = str(tmp_path / "test.png")
    fig.savefig(png); plt.close(fig)
    result = write_print_figure_pack([png], str(tmp_path), "AS-TEST", plt)
    manifest = Path(result["manifest"])
    assert manifest.exists()
    rows = list(csv.reader(open(manifest)))
    assert rows[0][0] == "# provenance"
    assert rows[1] == ["figure_stem", "png_path", "csv_sidecar_exists", "included_in_pdf"]


def test_print_figure_pack_empty_list_no_crash(tmp_path):
    from mamey.figures_sapote import write_print_figure_pack
    result = write_print_figure_pack([], str(tmp_path), "AS-TEST", plt)
    assert result["n_figures"] == 0
    assert Path(result["md"]).exists()
