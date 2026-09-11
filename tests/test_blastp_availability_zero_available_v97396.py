"""Regression test — v97396: blastp_availability.py reports "100% ingested" when literally
zero BLASTp data is available anywhere -- the exact scenario the tool's own docstring calls its
primary use case.

`scan()`'s meta aggregation: `"ingested_fraction": round(tot_matched / tot_avail, 3) if tot_avail
else 1.0`. When `tot_avail == 0` (no channel has any available BLASTp for any strain -- the
"activate at onset" moment, before any BLASTp has run), this defaulted to 1.0 -- a fully-complete
reading for a strain where nothing has even started. This directly contradicts the module's own
"CLAIM CEILING: ... counts are BGC-channel coverage, not a claim" -- reporting 100% implies more
completeness than the data supports.
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import mamey.blastp_availability as ba


def _stub_nothing_available(monkeypatch):
    monkeypatch.setattr(ba._g, "discover_trove_roots", lambda pkg: {})
    monkeypatch.setattr(ba._g, "available", lambda strain, roots: {})
    monkeypatch.setattr(ba._g, "ingested", lambda pkg: {})


def test_zero_available_is_not_reported_as_100_percent_v97396(tmp_path, monkeypatch):
    _stub_nothing_available(monkeypatch)
    runs = tmp_path / "runs" / "AS-001" / "package"
    runs.mkdir(parents=True)
    agg = ba.scan(runs_dir=str(tmp_path / "runs"))
    assert agg["meta"]["ingested_fraction"] is None, (
        "zero available pairs must not be reported as a numeric percentage (100% implies "
        "completeness the data does not support at the tool's own 'onset' use case)"
    )


def test_render_table_shows_na_not_100_percent_v97396(tmp_path, monkeypatch):
    _stub_nothing_available(monkeypatch)
    runs = tmp_path / "runs" / "AS-001" / "package"
    runs.mkdir(parents=True)
    agg = ba.scan(runs_dir=str(tmp_path / "runs"))
    table = ba.render_table(agg)
    assert "100%" not in table
    assert "N/A" in table


def test_genuine_partial_coverage_still_computes_a_real_fraction_no_regression_v97396(tmp_path, monkeypatch):
    monkeypatch.setattr(ba._g, "discover_trove_roots", lambda pkg: {})
    monkeypatch.setattr(ba._g, "available", lambda strain, roots: {"nr": {"BGC001": {}, "BGC002": {}}})
    monkeypatch.setattr(ba._g, "ingested", lambda pkg: {"BGC001": {"nr"}})
    runs = tmp_path / "runs" / "AS-001" / "package"
    runs.mkdir(parents=True)
    agg = ba.scan(runs_dir=str(tmp_path / "runs"))
    assert agg["meta"]["ingested_fraction"] == 0.5
    assert "50%" in ba.render_table(agg)
