"""An explicitly bound but unavailable cohort-governance source holds governed output.

The raw/non-strict loader keeps its documented warning fallback. The governed accessor,
and the exclusion gate built on it, must refuse instead of silently using the empty
default. A tree with no pack bound still gets the empty generic default.
"""
import json

import pytest

from mamey import exclusion_gate, exclusions


def test_missing_bound_file_holds_governed_accessor(tmp_path, monkeypatch):
    monkeypatch.setenv("MAMEY_OFFICIAL_DATA", str(tmp_path))  # bound dir, no exclusions.json
    monkeypatch.delenv("MAMEY_DATA_ROOT", raising=False)
    with pytest.raises(ValueError, match="bound exclusion source is missing"):
        exclusions.governed_excluded()


def test_malformed_bound_file_holds_governed_accessor(tmp_path, monkeypatch):
    (tmp_path / "exclusions.json").write_text("{not json", encoding="utf-8")
    monkeypatch.setenv("MAMEY_OFFICIAL_DATA", str(tmp_path))
    monkeypatch.delenv("MAMEY_DATA_ROOT", raising=False)
    with pytest.raises(ValueError, match="unreadable or malformed"):
        exclusions.governed_excluded()


def test_gate_and_ingest_guard_hold_on_failed_binding(tmp_path, monkeypatch):
    monkeypatch.setenv("MAMEY_OFFICIAL_DATA", str(tmp_path))
    monkeypatch.delenv("MAMEY_DATA_ROOT", raising=False)
    table = tmp_path / "governed.csv"
    table.write_text("strain\nSYN-001\n", encoding="utf-8")
    with pytest.raises(ValueError):
        exclusion_gate.gate_governed_outputs([table])
    with pytest.raises(ValueError):
        exclusion_gate.assert_strain_governable("SYN-001")


def test_bound_readable_pack_is_used(tmp_path, monkeypatch):
    (tmp_path / "exclusions.json").write_text(json.dumps({"hard_excluded": ["SYN-001"]}), encoding="utf-8")
    monkeypatch.setenv("MAMEY_OFFICIAL_DATA", str(tmp_path))
    monkeypatch.delenv("MAMEY_DATA_ROOT", raising=False)
    assert exclusions.governed_excluded() == {"SYN-001"}


def test_unbound_generic_tree_keeps_empty_default(monkeypatch):
    monkeypatch.delenv("MAMEY_OFFICIAL_DATA", raising=False)
    monkeypatch.delenv("MAMEY_DATA_ROOT", raising=False)
    monkeypatch.setattr(exclusions, "_candidate_json_paths", lambda: [])
    assert exclusions.governed_excluded() == set()


def test_raw_loader_keeps_warning_fallback(tmp_path, monkeypatch):
    monkeypatch.setenv("MAMEY_OFFICIAL_DATA", str(tmp_path))
    monkeypatch.delenv("MAMEY_DATA_ROOT", raising=False)
    with pytest.warns(RuntimeWarning):
        assert exclusions.load_exclusions() == exclusions._DEFAULT
