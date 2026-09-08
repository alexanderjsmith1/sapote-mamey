"""test_collection_figure_availability_report.py — v9.7.69

Tests for FIGURE_AVAILABILITY.md and figure_manifest.csv output.
"""
import csv
import pytest
from pathlib import Path
import pytest as _pytest
_pytest.importorskip("matplotlib")  # SKIP (not error) when figure stack absent
import matplotlib
matplotlib.use("Agg")

from mamey.collection_figures import render_collection_figures


def test_availability_report_lists_skipped_with_reason(tmp_path):
    """Skipped figures must explain why and list missing fields."""
    rows = [{"strain_id": "AS-XXX", "genus": "Streptomyces"}]  # no source/host/etc.
    result = render_collection_figures(rows, tmp_path)
    report = (tmp_path / "FIGURE_AVAILABILITY.md").read_text()
    assert "Skipped" in report or "skipped" in report
    assert "missing" in report.lower() or "required" in report.lower()


def test_availability_report_lists_generated(tmp_path):
    rows = [{"strain_id": f"AS-{i}", "genus": "Streptomyces"} for i in range(3)]
    result = render_collection_figures(rows, tmp_path)
    report = (tmp_path / "FIGURE_AVAILABILITY.md").read_text()
    assert "Generated" in report or "generated" in report


def test_availability_report_includes_unlock_hint(tmp_path):
    result = render_collection_figures(None, tmp_path)
    report = (tmp_path / "FIGURE_AVAILABILITY.md").read_text()
    assert "strain_id" in report
    assert "unlock" in report.lower() or "provide" in report.lower()


def test_availability_report_shows_aliases(tmp_path):
    """Missing field section should list acceptable aliases."""
    rows = [{"strain_id": "AS-XXX"}]  # missing genus etc.
    result = render_collection_figures(rows, tmp_path)
    report = (tmp_path / "FIGURE_AVAILABILITY.md").read_text()
    # Should mention alias possibilities
    assert "alias" in report.lower() or "genus" in report.lower()


def test_figure_manifest_has_provenance_row(tmp_path):
    """figure_manifest.csv must follow Item-18 provenance schema."""
    rows = [{"strain_id": f"AS-{i}"} for i in range(3)]
    result = render_collection_figures(rows, tmp_path)
    manifest_path = tmp_path / "figure_manifest.csv"
    rows_m = list(csv.reader(open(manifest_path)))
    assert rows_m[0][0] == "# provenance"
    assert rows_m[1] == ["figure_id", "status", "output_file", "skip_reason"]


def test_figure_manifest_records_generated_and_skipped(tmp_path):
    rows = [{"strain_id": f"AS-{i}", "genus": "Streptomyces"} for i in range(3)]
    result = render_collection_figures(rows, tmp_path)
    manifest_path = tmp_path / "figure_manifest.csv"
    data = list(csv.DictReader(open(manifest_path), fieldnames=None))[1:]  # skip provenance
    # re-read properly
    rows_m = list(csv.reader(open(manifest_path)))[2:]  # skip provenance + header
    statuses = {r[0]: r[1] for r in rows_m if len(r) >= 2}
    assert "GENERATED" in statuses.values()
    assert "SKIPPED" in statuses.values()


def test_no_metadata_manifest_all_skipped(tmp_path):
    result = render_collection_figures(None, tmp_path)
    # All figures should appear as SKIPPED or manifest just shows empty generated
    manifest_path = tmp_path / "figure_manifest.csv"
    rows_m = list(csv.reader(open(manifest_path)))[2:]
    statuses = [r[1] for r in rows_m if len(r) >= 2]
    # Either all SKIPPED or empty
    assert all(s == "SKIPPED" for s in statuses) or not statuses
