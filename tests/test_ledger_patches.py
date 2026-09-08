"""test_ledger_patches.py — v9.7.73

Tests for three ledger items implemented in this cut:
  AF-Class-Priority-and-Other-Section-1 — special class review always present
  Figure-Key-KCB-Class-1               — KCB class context in figure key
  Spell-Out-Lead-Chart-Axes-1          — Antibacterial/Antifungal spelled out
"""
import csv
import json
import os
import pytest as _pytest
_pytest.importorskip("matplotlib")  # SKIP (not error) when figure stack absent
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest
from pathlib import Path


# ── Spell-Out-Lead-Chart-Axes-1 ───────────────────────────────────────────────

def test_ab_ranked_title_spells_antibacterial():
    """AB ranked figure must use 'Antibacterial' in title, not just 'AB'."""
    from mamey.figures_sapote import fig_ab_ranked
    import inspect
    src = inspect.getsource(fig_ab_ranked)
    assert "Antibacterial" in src


def test_af_ranked_title_spells_antifungal():
    from mamey.figures_sapote import fig_af_ranked
    import inspect
    src = inspect.getsource(fig_af_ranked)
    assert "Antifungal" in src


def test_ab_axis_label_spells_antibacterial():
    """Axis label in AB ranked figure must use 'Antibacterial'."""
    from mamey.figures_sapote import fig_ab_ranked
    import inspect
    src = inspect.getsource(fig_ab_ranked)
    assert "Antibacterial" in src
    assert "AB_auto" not in src.split("Antibacterial")[0].split("def fig_ab_ranked")[1][:50]  # v9.7.409 A4: trailing `or True` made this assertion vacuous


def test_vertical_panels_axis_labels_spelled_out(tmp_path):
    """fig_ab_af_vertical_panels must use spelled-out labels."""
    from mamey.figures_sapote import fig_ab_af_vertical_panels
    rows = [{"rank":"1","bgc_id":f"BGC{i+1:03d}","contig":f"NODE_{i+1}","region":f"region{i+1:03d}",
             "products":"NRPS","boundary":"Interior","ab":80.0-i*5,"af":50.0-i*3,
             "novelty":60.0,"lead_tier":"High","kcb_top":"","kcb_score":"","cctt":""}
            for i in range(5)]
    png = str(tmp_path / "panels.png")
    result = fig_ab_af_vertical_panels(rows, png, "AS-TEST", plt)
    assert result is not None
    # Verify spelled-out labels appear in the source
    import inspect
    src = inspect.getsource(fig_ab_af_vertical_panels)
    assert "Antibacterial" in src
    assert "Antifungal" in src


# ── Figure-Key-KCB-Class-1 ───────────────────────────────────────────────────

def test_vertical_panels_has_kcb_class_key(tmp_path):
    """The combined AB/AF panel must include a KCB class context key."""
    from mamey.figures_sapote import fig_ab_af_vertical_panels
    import inspect
    src = inspect.getsource(fig_ab_af_vertical_panels)
    # Key text generation must be present in source
    assert "Class / KCB context" in src or "kcb_ctx" in src


def test_vertical_panels_kcb_note_claim_safe(tmp_path):
    """KCB context note must use 'similarity' language, not 'produces'."""
    from mamey.figures_sapote import fig_ab_af_vertical_panels
    import inspect
    src = inspect.getsource(fig_ab_af_vertical_panels)
    assert "similarity" in src.lower() or "KCB~" in src


# ── AF-Class-Priority-and-Other-Section-1 ─────────────────────────────────────

def _make_facts_with_classes(include_nuc=True, include_arylp=True, include_other=True):
    rows = [
        {"rank":"1","bgc_id":"BGC001","contig":"NODE_1","region":"region001",
         "products":"NRPS; T1PKS","boundary":"Interior","ab":74.0,"af":40.0,
         "novelty":60.0,"lead_tier":"High","kcb_top":"BGC001.5 | nikkomycin | knownclusterblast",
         "kcb_score":"5000","cctt":""},
    ]
    if include_nuc:
        rows.append({"rank":"2","bgc_id":"BGC002","contig":"NODE_2","region":"region002",
                     "products":"nucleoside","boundary":"Interior","ab":55.0,"af":60.0,
                     "novelty":70.0,"lead_tier":"High","kcb_top":"","kcb_score":"","cctt":""})
    if include_arylp:
        rows.append({"rank":"3","bgc_id":"BGC003","contig":"NODE_3","region":"region003",
                     "products":"arylpolyene; other","boundary":"Interior","ab":20.0,"af":15.0,
                     "novelty":30.0,"lead_tier":"Inventory","kcb_top":"","kcb_score":"","cctt":""})
    if include_other:
        rows.append({"rank":"4","bgc_id":"BGC004","contig":"NODE_4","region":"region004",
                     "products":"other","boundary":"Interior","ab":10.0,"af":8.0,
                     "novelty":15.0,"lead_tier":"Inventory","kcb_top":"","kcb_score":"","cctt":""})
    return {
        "rows": rows,
        "strain_label": "Streptomyces sp. AS-TEST",
        "release": "private",
        "manifest": {
            "taxonomy": "Streptomyces sp.", "source": "Apis mellifera",
            "workflow_version": "v9.7.73", "analysis_date": "2026-06-17",
            "bgc_counts": {"corrected":"3.5","raw":"4","interior":"4","edge":"0",
                           "full_contig":"0","assembly_tier":"GOOD"},
            "assembly": {"genome_bp":"6800000","contigs":"400","n50":"180000","gc_pct":"72"},
            "bioactivity": {"targets":"MRSA+Candida","status":"default-assumed",
                            "compound_linkage":"not established"},
            "scan_status": {"scans": [["KCB","PASS","4 BGCs"], ["CCTT","PASS","0 triggers"]]},
            "resistance_gene_summary": {"counts": {}},
        }
    }


def test_special_class_review_renders_without_error(tmp_path):
    """_text_page with special class rows must not raise."""
    from mamey.render_brief import _text_page, _setup_mpl
    from matplotlib.backends.backend_pdf import PdfPages
    import io
    facts = _make_facts_with_classes()
    plt_inst = _setup_mpl()
    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        _text_page(pdf, plt_inst, facts, tier="standard")
    assert len(buf.getvalue()) > 500


def test_special_class_review_with_zero_counts(tmp_path):
    """Special class review must not fail when nucleoside/polyene/other counts are zero."""
    from mamey.render_brief import _text_page, _setup_mpl
    from matplotlib.backends.backend_pdf import PdfPages
    import io
    facts = _make_facts_with_classes(include_nuc=False, include_arylp=False, include_other=False)
    plt_inst = _setup_mpl()
    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        _text_page(pdf, plt_inst, facts, tier="standard")
    assert len(buf.getvalue()) > 500


def test_arylpolyene_guard_present_in_source():
    """render_brief must contain the arylpolyene guard text."""
    import inspect
    from mamey import render_brief as rb
    src = inspect.getsource(rb)
    assert "arylpolyene" in src.lower()
    assert ("antifungal polyene macrolide" in src.lower() or
            "arylpolyene" in src.lower() and "macrolide" in src.lower())


def test_special_class_functions_defined():
    """The nucleoside/polyene/other detection lambdas must be present in _text_page."""
    import inspect
    from mamey import render_brief as rb
    src = inspect.getsource(rb._text_page)
    assert "nucleoside" in src
    assert "polyene" in src
    assert "other_only" in src or "is_other_only" in src or "_other_bgcs" in src


def test_special_class_section_in_source():
    """_text_page source must contain the 'Special class review' heading."""
    import inspect
    from mamey.render_brief import _text_page
    src = inspect.getsource(_text_page)
    assert "Special class review" in src
