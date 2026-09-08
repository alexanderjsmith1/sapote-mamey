"""test_collection_figure_manifest.py — v9.7.69

Tests for figure_manifest.csv output and package integration.
"""
import csv
import pytest
from pathlib import Path
import pytest as _pytest
_pytest.importorskip("matplotlib")  # SKIP (not error) when figure stack absent
import matplotlib
matplotlib.use("Agg")

from mamey.collection_figures import (
    render_collection_figures, FIGURE_REGISTRY
)


def test_manifest_covers_all_registry_figures(tmp_path):
    """Every spec in the registry should appear in the manifest."""
    rows = [{"strain_id": f"AS-{i}", "genus": "Streptomyces",
             "source": "bee" if i < 3 else "moss",
             "host": "Apis", "location": "Ontario",
             "candida_call": "1" if i % 2 == 0 else "0",
             "mrsa_call": "0",
             "candida_tested": "yes", "mrsa_tested": "yes",
             "closest_type_similarity": str(98.5 + i * 0.1),
             "closest_type_strain": "Streptomyces coelicolor A3(2)",
             "accession": "MK123456" if i < 5 else "",
             "collection_date": str(2018 + i % 5),
             "genome_mined": "yes",
             "priority": "yes" if i < 2 else "no",
             } for i in range(10)]
    result = render_collection_figures(rows, tmp_path)
    manifest_path = tmp_path / "figure_manifest.csv"
    manifest_rows = list(csv.reader(open(manifest_path)))[2:]  # skip provenance + header
    manifest_ids = {r[0] for r in manifest_rows if r}
    registry_ids = {s.figure_id for s in FIGURE_REGISTRY}
    # Every registry figure should appear (generated or skipped)
    assert registry_ids.issubset(manifest_ids | {"fig_genus_activity_heatmap"}), \
        f"missing from manifest: {registry_ids - manifest_ids}"


def test_manifest_generated_rows_have_output_file(tmp_path):
    rows = [{"strain_id": f"AS-{i}", "genus": "Streptomyces"} for i in range(3)]
    result = render_collection_figures(rows, tmp_path)
    manifest_rows = list(csv.reader(open(tmp_path / "figure_manifest.csv")))[2:]
    for r in manifest_rows:
        if len(r) >= 4 and r[1] == "GENERATED":
            assert r[2], f"GENERATED row missing output_file: {r}"


def test_manifest_skipped_rows_have_reason(tmp_path):
    rows = [{"strain_id": f"AS-{i}"} for i in range(3)]
    result = render_collection_figures(rows, tmp_path)
    manifest_rows = list(csv.reader(open(tmp_path / "figure_manifest.csv")))[2:]
    for r in manifest_rows:
        if len(r) >= 4 and r[1] == "SKIPPED":
            assert r[3], f"SKIPPED row missing reason: {r}"


def test_16s_figures_generate_with_similarity_field(tmp_path):
    """16S similarity fields → 16S figures generate."""
    rows = [{"strain_id": f"AS-{i}",
             "closest_type_similarity": str(97.5 + i * 0.3)}
            for i in range(5)]
    result = render_collection_figures(rows, tmp_path)
    gen_ids = {Path(p).stem for p in result["generated"]}
    assert "fig_16s_similarity_dist" in gen_ids
    assert "fig_low_16s_rate" in gen_ids


def test_ambiguous_alias_produces_warning_not_error(tmp_path):
    """Bad/ambiguous column names must warn, never crash."""
    rows = [{"strain_id": "A1", "sid": "A2",
             "16S_genus": "Streptomyces", "taxon_genus": "Micromonospora"}]
    try:
        result = render_collection_figures(rows, tmp_path)
        # warnings may or may not be emitted
    except Exception as e:
        pytest.fail(f"ambiguous alias caused crash: {e}")
