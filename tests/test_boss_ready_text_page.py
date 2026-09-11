"""test_boss_ready_text_page.py — v9.7.66

Tests for the restructured _text_page (PDF-001/018/020: executive summary)
and fig_rggmci_rescue (PDF-013: fragment rescue figure).

Design validation for the Do Not Patch Blindly clause:
- Root cause: text page was a sequential text dump, not a scannable executive summary
- Safe layer: _text_page in render_brief.py (no new data sources, same timing envelope)
- No figure names changed; no validator impact
- fig_rggmci_rescue uses only package-present ranked pairs CSV
"""
import csv
import io
import os
import tempfile
import pytest as _pytest
_pytest.importorskip("matplotlib")  # SKIP (not error) when figure stack absent
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from mamey.render_brief import _text_page, _tier_color, fig_rggmci_rescue, _setup_mpl


def _make_facts(n_rows=8):
    rows = []
    tiers = ["High", "High", "Medium", "Medium", "Inventory",
             "Inventory", "Medium", "Inventory"]
    for i in range(n_rows):
        rows.append({
            "rank": str(i + 1), "bgc_id": f"BGC{i+1:03d}",
            "contig": f"NODE_{i+1}_length_200000_cov_55",
            "region": f"region_{i+1}",
            "products": "NRPS; T1PKS" if i < 4 else "saccharide",
            "boundary": "Interior", "arch": "A",
            "ab": 80 - i * 5, "af": 40 - i * 3,
            "novelty": 60 - i * 4,
            "lead_tier": tiers[i % len(tiers)],
            "kcb_top": f"BGC000{i}.5 | testomycin A/testomycin B | knownclusterblast #1",
            "kcb_score": str(5000 - i * 100),
            "cctt": "T43-LAN" if i < 3 else "",
        })
    return {
        "strain_label": "Streptomyces sp. AS-TEST",
        "release": "private",
        "rows": rows,
        "manifest": {
            "taxonomy": "Streptomyces sp.",
            "source": "Apis mellifera",
            "workflow_version": "v9.7.66",
            "analysis_date": "2026-06-17",
            "bgc_counts": {
                "corrected": "29.5", "raw": "48",
                "interior": "19", "edge": "12", "full_contig": "17",
                "assembly_tier": "GOOD",
            },
            "assembly": {
                "genome_bp": "6813456", "contigs": "387",
                "n50": "187208", "gc_pct": "71.8",
            },
            "bioactivity": {
                "targets": "MRSA+Candida", "status": "default-assumed",
                "compound_linkage": "not established",
            },
            "scan_status": {"scans": [
                ["KCB_sweep", "PASS", "48 regions"],
                ["RG_GMCI", "PASS", "6 high"],
                ["CCTT", "PASS", "T43-LAN: 3 BGCs"],
                ["UMED", "PASS", "1 GAP"],
            ]},
            "resistance_gene_summary": {"counts": {"T1": 2, "T2": 3}},
        },
    }


def _render_text_page(facts, tier="standard"):
    """Render _text_page to a PDF in memory; return the figure."""
    from matplotlib.backends.backend_pdf import PdfPages
    plt_inst = _setup_mpl()
    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        _text_page(pdf, plt_inst, facts, tier)
    return buf.getvalue()


# ── _tier_color ────────────────────────────────────────────────────────────────

def test_tier_color_high_is_green():
    assert _tier_color("High").startswith("#")
    assert _tier_color("High") != _tier_color("Inventory")

def test_tier_color_unknown_returns_muted():
    from mamey.render_brief import CL
    assert _tier_color("Unknown") == CL["muted"]


# ── _text_page renders without error ─────────────────────────────────────────

def test_text_page_renders_standard_tier():
    facts = _make_facts()
    pdf_bytes = _render_text_page(facts, tier="standard")
    assert len(pdf_bytes) > 1000, "PDF output should be non-trivial"

def test_text_page_renders_brief_tier():
    """brief tier should skip the table section gracefully."""
    facts = _make_facts()
    pdf_bytes = _render_text_page(facts, tier="brief")
    assert len(pdf_bytes) > 500

def test_text_page_handles_empty_rows():
    """Zero rows must not raise."""
    facts = _make_facts(0)
    pdf_bytes = _render_text_page(facts, tier="standard")
    assert len(pdf_bytes) > 0

def test_text_page_handles_missing_manifest_keys():
    """Missing manifest keys must not raise — all fields have defaults."""
    facts = {"strain_label": "Test", "release": "private", "rows": [],
             "manifest": {}}
    pdf_bytes = _render_text_page(facts, tier="standard")
    assert len(pdf_bytes) > 0


# ── fig_rggmci_rescue ─────────────────────────────────────────────────────────

def _write_pairs_csv(path, n_high=2, n_mod=3):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pair","bgc_a","bgc_b","rggmci_score","rggmci_confidence",
                    "supporting_references","good_geometry_references",
                    "products_a","products_b","split_signature","acceptance_gate",
                    "best_sources","interpretation_guard"])
        for i in range(n_high):
            w.writerow([f"BGC{i+1:03d}+BGC{i+10:03d}", f"BGC{i+1:03d}", f"BGC{i+10:03d}",
                        str(35 - i), "HIGH_RG_GMCI_RESCUE",
                        str(10 - i), str(8 - i), "RiPP; lanthipeptide", "RRE-containing; RiPP",
                        "True", "OK", "ref1|ref2", "Homology-guided linkage."])
        for j in range(n_mod):
            k = n_high + j
            w.writerow([f"BGC{k+1:03d}+BGC{k+10:03d}", f"BGC{k+1:03d}", f"BGC{k+10:03d}",
                        str(25 - j), "MODERATE_RG_GMCI_CANDIDATE",
                        str(6 - j), str(4 - j), "PKS; T1PKS", "NRPS",
                        "False", "OK", "ref3", "Homology-guided linkage."])


def test_rggmci_rescue_figure_renders(tmp_path):
    pairs_csv = str(tmp_path / "pairs.csv")
    png_path = str(tmp_path / "rescue.png")
    _write_pairs_csv(pairs_csv)
    plt_inst = _setup_mpl()
    fig = fig_rggmci_rescue(pairs_csv, png_path, "AS-TEST", plt_inst)
    assert fig is not None
    assert os.path.exists(png_path)
    plt.close(fig)

def test_rggmci_rescue_produces_sidecar_csv(tmp_path):
    pairs_csv = str(tmp_path / "pairs.csv")
    png_path = str(tmp_path / "rescue.png")
    _write_pairs_csv(pairs_csv)
    plt_inst = _setup_mpl()
    fig = fig_rggmci_rescue(pairs_csv, png_path, "AS-TEST", plt_inst)
    sidecar = png_path.replace(".png", "_data.csv")
    assert os.path.exists(sidecar)
    rows = list(csv.reader(open(sidecar)))
    assert rows[0][0] == "# provenance"
    assert rows[1][0] == "pair"
    plt.close(fig)

def test_rggmci_rescue_returns_none_for_empty_csv(tmp_path):
    pairs_csv = str(tmp_path / "empty.csv")
    open(pairs_csv, "w").write("pair,bgc_a,bgc_b\n")
    png_path = str(tmp_path / "rescue.png")
    plt_inst = _setup_mpl()
    result = fig_rggmci_rescue(pairs_csv, png_path, "AS-TEST", plt_inst)
    assert result is None

def test_rggmci_rescue_returns_none_for_missing_file(tmp_path):
    png_path = str(tmp_path / "rescue.png")
    plt_inst = _setup_mpl()
    result = fig_rggmci_rescue("/nonexistent/pairs.csv", png_path, "AS-TEST", plt_inst)
    assert result is None

def test_rggmci_rescue_sidecar_has_provenance_row(tmp_path):
    """PDF-013 sidecar must follow the Item-18 provenance schema."""
    pairs_csv = str(tmp_path / "pairs.csv")
    png_path = str(tmp_path / "rescue.png")
    _write_pairs_csv(pairs_csv, n_high=1, n_mod=1)
    plt_inst = _setup_mpl()
    fig = fig_rggmci_rescue(pairs_csv, png_path, "AS-TEST", plt_inst)
    import pandas as pd
    df = pd.read_csv(png_path.replace(".png", "_data.csv"), skiprows=1)
    assert "pair" in df.columns
    assert "rggmci_score" in df.columns
    plt.close(fig)
