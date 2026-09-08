"""Regression: mamey/exclusions.py must not silently swallow a missing OFFICIAL_DATA/*
file when the OFFICIAL_DATA directory itself is present -- that's the exact live gap
that let TIER/ATTINE_ANT_STRAINS/DEMO_STRAINS/CO_ASSEMBLY go silently empty after the
v9.7.393 externalization moved them out of shipped source without anyone creating the
corresponding OFFICIAL_DATA/*.json files. A genuinely code-only tree (no OFFICIAL_DATA
directory anywhere in the search path) must stay silent -- that's the documented,
intended fail-safe for a public/portable install, and this fix must not break it.
"""
from __future__ import annotations

import warnings

import pytest

from mamey import exclusions


# --- unit-level: the new helper in isolation, no filesystem-walk/env dependency ---

def test_helper_warns_when_a_candidate_parent_dir_exists(tmp_path):
    official_data = tmp_path / "OFFICIAL_DATA"
    official_data.mkdir()
    candidates = [official_data / "exclusions.json"]
    with pytest.warns(RuntimeWarning, match="exclusions.json"):
        exclusions._warn_official_data_present_but_file_missing(candidates, "exclusions.json")


def test_helper_stays_silent_when_no_candidate_parent_dir_exists(tmp_path):
    candidates = [tmp_path / "NO_SUCH_OFFICIAL_DATA" / "exclusions.json"]
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # any warning raised here fails the test
        exclusions._warn_official_data_present_but_file_missing(candidates, "exclusions.json")


# --- integration-level: load_exclusions() / official_data_json() via MAMEY_OFFICIAL_DATA ---

def test_load_exclusions_warns_and_falls_back_when_file_missing_but_dir_present(tmp_path, monkeypatch):
    monkeypatch.setenv("MAMEY_OFFICIAL_DATA", str(tmp_path))  # dir exists, no exclusions.json in it
    monkeypatch.delenv("MAMEY_DATA_ROOT", raising=False)
    with pytest.warns(RuntimeWarning, match="exclusions.json"):
        result = exclusions.load_exclusions()
    assert result == exclusions._DEFAULT


def test_official_data_json_warns_and_falls_back_when_file_missing_but_dir_present(tmp_path, monkeypatch):
    monkeypatch.setenv("MAMEY_OFFICIAL_DATA", str(tmp_path))  # dir exists, no demo_strains.json in it
    monkeypatch.delenv("MAMEY_DATA_ROOT", raising=False)
    with pytest.warns(RuntimeWarning, match="demo_strains.json"):
        result = exclusions.official_data_json("demo_strains.json", default={"strains": []})
    assert result == {"strains": []}


def test_official_data_json_warns_on_malformed_file_too(tmp_path, monkeypatch):
    (tmp_path / "demo_strains.json").write_text("{not valid json", encoding="utf-8")
    monkeypatch.setenv("MAMEY_OFFICIAL_DATA", str(tmp_path))
    monkeypatch.delenv("MAMEY_DATA_ROOT", raising=False)
    with pytest.warns(RuntimeWarning, match="demo_strains.json"):
        result = exclusions.official_data_json("demo_strains.json", default={"strains": []})
    assert result == {"strains": []}


def test_official_data_json_returns_real_data_with_no_warning_when_file_present(tmp_path, monkeypatch):
    (tmp_path / "demo_strains.json").write_text('{"strains": ["SYNTH-1"]}', encoding="utf-8")
    monkeypatch.setenv("MAMEY_OFFICIAL_DATA", str(tmp_path))
    monkeypatch.delenv("MAMEY_DATA_ROOT", raising=False)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        result = exclusions.official_data_json("demo_strains.json", default={"strains": []})
    assert result == {"strains": ["SYNTH-1"]}
