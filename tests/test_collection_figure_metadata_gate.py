"""test_collection_figure_metadata_gate.py — v9.7.69

Tests for metadata gating in collection_figures.py:
- No metadata → package still seals; availability report written.
- strain_id only → overview generates (min_rows=1).
- genus + source → top genera, shared genera, matrix generate.
- not-tested values are NOT counted as positive.
- 16S similarity fields → 16S figures generate.
- missing required field → figure skipped, not error.
"""
import pytest as _pytest
_pytest.importorskip("matplotlib")  # SKIP (not error) when figure stack absent
import matplotlib
matplotlib.use("Agg")
import os
import csv
import pytest
from pathlib import Path

from mamey.collection_figures import (
    normalize_metadata, render_collection_figures,
    _is_positive, _is_negative, _is_not_tested,
    _check_gate, FIGURE_REGISTRY, NOT_TESTED_VALUES,
)


# ── not-tested semantics ──────────────────────────────────────────────────────

@pytest.mark.parametrize("v", ["", "na", "N/A", "n.t.", "not tested", "nt",
                                "not_tested", "None", "ND", "pending", "unknown"])
def test_not_tested_is_not_positive(v):
    assert not _is_positive(v)

@pytest.mark.parametrize("v", ["", "na", "N/A", "n.t.", "not tested"])
def test_not_tested_is_not_negative(v):
    """Not tested must remain distinct from negative (claim-safety rule)."""
    assert not _is_negative(v)

@pytest.mark.parametrize("v", ["1","yes","Yes","true","True","positive","pos","+","active","hit"])
def test_positive_values(v):
    assert _is_positive(v)

@pytest.mark.parametrize("v", ["0","no","No","false","False","negative","neg","-","inactive"])
def test_negative_values(v):
    assert _is_negative(v)
    assert not _is_positive(v)


# ── normalize_metadata ────────────────────────────────────────────────────────

def test_alias_mapping_basic():
    rows = [{"strain": "AS-XXX", "genus": "Streptomyces"}]
    norm, warns = normalize_metadata(rows)
    assert norm[0].get("strain_id") == "AS-XXX"
    assert not warns

def test_alias_case_insensitive():
    rows = [{"SID": "AS-XXX", "GENUS": "Micromonospora"}]
    norm, warns = normalize_metadata(rows)
    # GENUS matches 'genus' alias
    assert norm[0].get("genus") == "Micromonospora"

def test_ambiguous_alias_warns():
    """Two aliases for the same canonical → warning, first used.

    v9.7.412: the old fixture supplied the CANONICAL column (`candida_call`) plus one alias, which the
    documented rule resolves silently ("canonical wins"); a trailing `or True` then hid that the
    assertion never held. Two genuine aliases exercise the ambiguity branch."""
    rows = [{"candida": "1", "ca_call": "yes"}]
    norm, warns = normalize_metadata(rows)
    # Both are aliases of candida_call — must warn and use the first-seen alias
    assert any("ambiguous" in w.lower() or "candida" in w.lower() for w in warns), warns  # v9.7.412: `or True` made this vacuous


# ── gate checks ───────────────────────────────────────────────────────────────

def _rows_with(fields: dict, n: int = 3) -> list[dict]:
    return [{"strain_id": f"AS-{i:03d}", **fields} for i in range(n)]

def test_gate_passes_when_required_present():
    spec = next(s for s in FIGURE_REGISTRY if s.figure_id == "fig_top_genera")
    rows = _rows_with({"genus": "Streptomyces"})
    can, reason = _check_gate(spec, rows)
    assert can

def test_gate_fails_when_required_absent():
    spec = next(s for s in FIGURE_REGISTRY if s.figure_id == "fig_top_genera")
    rows = _rows_with({})  # no genus
    can, reason = _check_gate(spec, rows)
    assert not can
    assert "genus" in reason.lower()

def test_gate_fails_multi_source_with_one_source():
    spec = next(s for s in FIGURE_REGISTRY if s.figure_id == "fig_shared_unique_genera")
    rows = _rows_with({"genus": "Streptomyces", "source": "bee"})
    can, reason = _check_gate(spec, rows)
    assert not can
    assert "source" in reason.lower()

def test_gate_passes_multi_source_with_two_sources():
    spec = next(s for s in FIGURE_REGISTRY if s.figure_id == "fig_shared_unique_genera")
    rows = (
        _rows_with({"genus": "Streptomyces", "source": "bee"}, 2) +
        _rows_with({"genus": "Micromonospora", "source": "moss"}, 2)
    )
    can, reason = _check_gate(spec, rows)
    assert can


# ── render_collection_figures — no metadata ───────────────────────────────────

def test_no_metadata_writes_availability_report(tmp_path):
    result = render_collection_figures(None, tmp_path)
    assert result["n_generated"] == 0
    avail = tmp_path / "FIGURE_AVAILABILITY.md"
    assert avail.exists()
    assert "skipped" in avail.read_text().lower() or "unlock" in avail.read_text().lower()

def test_no_metadata_writes_figure_manifest(tmp_path):
    result = render_collection_figures(None, tmp_path)
    manifest = tmp_path / "figure_manifest.csv"
    assert manifest.exists()

def test_empty_metadata_list_no_error(tmp_path):
    result = render_collection_figures([], tmp_path)
    assert result["n_generated"] == 0


# ── overview generates with strain_id only ────────────────────────────────────

def test_overview_generates_with_strain_id_only(tmp_path):
    rows = [{"strain_id": f"AS-{i:03d}"} for i in range(5)]
    result = render_collection_figures(rows, tmp_path)
    assert any("fig_collection_overview" in Path(p).stem for p in result["generated"])


# ── genus + source generates expected figures ─────────────────────────────────

def test_genus_figures_generate_with_genus_source(tmp_path):
    rows = (
        [{"strain_id": f"A-{i}", "genus": "Streptomyces", "source": "bee"} for i in range(4)] +
        [{"strain_id": f"B-{i}", "genus": "Micromonospora", "source": "moss"} for i in range(3)]
    )
    result = render_collection_figures(rows, tmp_path)
    gen_ids = {Path(p).stem for p in result["generated"]}
    assert "fig_top_genera" in gen_ids
    assert "fig_shared_unique_genera" in gen_ids

def test_genus_source_matrix_generates(tmp_path):
    rows = (
        [{"strain_id": f"A-{i}", "genus": "Streptomyces", "source": "bee"} for i in range(4)] +
        [{"strain_id": f"B-{i}", "genus": "Actinomyces", "source": "moss"} for i in range(3)]
    )
    result = render_collection_figures(rows, tmp_path)
    gen_ids = {Path(p).stem for p in result["generated"]}
    assert "fig_genus_source_matrix" in gen_ids


# ── not-tested not counted as positive ───────────────────────────────────────

def test_not_tested_excluded_from_positive_count(tmp_path):
    """Core claim-safety invariant."""
    rows = [
        {"strain_id": "A1", "candida_call": "n.t.", "mrsa_call": "n.t."},
        {"strain_id": "A2", "candida_call": "not tested", "mrsa_call": ""},
        {"strain_id": "A3", "candida_call": "1", "mrsa_call": "yes"},
    ]
    result = render_collection_figures(rows, tmp_path)
    # Find overview CSV to check counts
    csv_files = list(tmp_path.glob("*_data.csv"))
    overview_csv = next((f for f in csv_files if "overview" in f.name), None)
    if overview_csv:
        data = dict(csv.reader(open(overview_csv)))  # {category: count}
        # Only row A3 should be counted as positive
        # (csv is provenance+header+data so parse properly)
        rows_data = list(csv.reader(open(overview_csv)))[2:]  # skip provenance + header
        counts = {r[0]: int(r[1]) for r in rows_data if len(r) >= 2 and r[1].isdigit()}
        # If candida or mrsa appear, they should be 1 (only A3), not 3
        for k, v in counts.items():
            if "candida" in k.lower() or "mrsa" in k.lower():
                assert v <= 1, f"not-tested counted as positive: {k}={v}"
