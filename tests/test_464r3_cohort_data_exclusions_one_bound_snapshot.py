"""Governed exclusions come from one strict read, and the binding reports that read."""
from __future__ import annotations

import hashlib
import json
import warnings
from pathlib import Path

import pytest

from mamey import exclusions


def _pack(tmp_path: Path, ids: list[str]) -> Path:
    pack = tmp_path / "OFFICIAL_DATA"
    pack.mkdir()
    (pack / "exclusions.json").write_text(json.dumps({"hard_excluded": ids}), encoding="utf-8")
    return pack


def test_file_changed_after_strict_read_does_not_empty_the_governed_set(tmp_path, monkeypatch):
    pack = _pack(tmp_path, ["DEMO-A"])
    monkeypatch.setenv("MAMEY_OFFICIAL_DATA", str(pack))
    monkeypatch.delenv("MAMEY_DATA_ROOT", raising=False)
    real = json.loads
    state = {"calls": 0}

    def corrupt_after_first(*args, **kwargs):
        result = real(*args, **kwargs)
        state["calls"] += 1
        if state["calls"] == 1:
            (pack / "exclusions.json").write_text("{not json", encoding="utf-8")
        return result

    monkeypatch.setattr(exclusions.json, "loads", corrupt_after_first)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert exclusions.governed_excluded() == {"DEMO-A"}
    assert state["calls"] == 1


def test_binding_names_env_source_path_and_hash_of_bytes_read(tmp_path, monkeypatch):
    pack = _pack(tmp_path, ["DEMO-B", "DEMO-A"])
    monkeypatch.setenv("MAMEY_OFFICIAL_DATA", str(pack))
    monkeypatch.delenv("MAMEY_DATA_ROOT", raising=False)
    binding = exclusions.exclusion_binding()
    target = pack / "exclusions.json"
    assert binding["source_type"] == "MAMEY_OFFICIAL_DATA"
    assert binding["path"] == str(target.absolute())
    assert binding["sha256"] == hashlib.sha256(target.read_bytes()).hexdigest()
    assert binding["hard_excluded"] == ["DEMO-A", "DEMO-B"]


def test_binding_names_data_root_source(tmp_path, monkeypatch):
    _pack(tmp_path, ["DEMO-C"])
    monkeypatch.delenv("MAMEY_OFFICIAL_DATA", raising=False)
    monkeypatch.setenv("MAMEY_DATA_ROOT", str(tmp_path))
    assert exclusions.exclusion_binding()["source_type"] == "MAMEY_DATA_ROOT"


def test_missing_bound_file_raises_instead_of_naming_a_path(tmp_path, monkeypatch):
    monkeypatch.setenv("MAMEY_OFFICIAL_DATA", str(tmp_path / "nowhere"))
    monkeypatch.delenv("MAMEY_DATA_ROOT", raising=False)
    with pytest.raises(ValueError, match="missing"):
        exclusions.exclusion_binding()


def test_default_binding_has_no_path(monkeypatch):
    monkeypatch.delenv("MAMEY_OFFICIAL_DATA", raising=False)
    monkeypatch.delenv("MAMEY_DATA_ROOT", raising=False)
    monkeypatch.setattr(exclusions, "_candidate_json_paths", lambda: [Path("/nonexistent-464r3/OFFICIAL_DATA/exclusions.json")])
    binding = exclusions.exclusion_binding()
    assert binding == {"source_type": "MODULE_DEFAULT", "path": None, "sha256": None, "hard_excluded": []}
