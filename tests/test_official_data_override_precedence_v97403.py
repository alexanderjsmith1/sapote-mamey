"""Governed-data override precedence (.403, Black Cherry-4).

An explicit ``MAMEY_OFFICIAL_DATA`` override must be AUTHORITATIVE. Before this fix the
env override, the data root, and the ``__file__`` parent walk all went into one ordered
candidate list, and the caller loop continued past a missing override file — so a tree
living under a workspace that holds its own ``OFFICIAL_DATA/`` silently returned THAT
pack's exclusions and denominators despite the operator naming a different pack.

That is a governed-data provenance risk: the wrong exclusion set or the wrong denominator
can reach a governed conclusion with no signal. It is also why the shipped
``test_official_data_missing_file_warns_v97395`` tests fail when the tree sits inside such
a workspace and pass in a scratch location — the failure was a symptom, this is the cause.

These tests are location-independent by construction: each one builds BOTH an "override"
pack and a decoy "ancestor" pack under tmp_path and asserts which one wins, so they behave
identically wherever the tree is checked out.
"""
from __future__ import annotations

import json

import pytest

from mamey import exclusions

DECOY = {"hard_excluded": ["DECOY-001"], "raw_assembly_void": [],
         "strain_of_record": {}, "qc_hold_audit_only": [], "governed": {}}
OVERRIDE = {"hard_excluded": ["OVERRIDE-001"], "raw_assembly_void": [],
            "strain_of_record": {}, "qc_hold_audit_only": [], "governed": {}}


def _pack(directory, payload, filename="exclusions.json"):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / filename).write_text(json.dumps(payload), encoding="utf-8")
    return directory


# --- the precedence contract ---------------------------------------------------------------

def test_explicit_override_wins_over_any_other_source(tmp_path, monkeypatch):
    override = _pack(tmp_path / "override_pack", OVERRIDE)
    root = tmp_path / "shared_root"
    _pack(root / "OFFICIAL_DATA", DECOY)
    monkeypatch.setenv("MAMEY_OFFICIAL_DATA", str(override))
    monkeypatch.setenv("MAMEY_DATA_ROOT", str(root))
    assert exclusions.load_exclusions()["hard_excluded"] == ["OVERRIDE-001"]


def test_override_probe_list_is_exclusive(tmp_path, monkeypatch):
    """The probe list itself must contain ONLY the override — not the override plus a
    parent walk that a caller loop could fall through to."""
    override = _pack(tmp_path / "override_pack", OVERRIDE)
    monkeypatch.setenv("MAMEY_OFFICIAL_DATA", str(override))
    monkeypatch.delenv("MAMEY_DATA_ROOT", raising=False)
    paths = exclusions._probe_paths("exclusions.json")
    assert paths == [override / "exclusions.json"], (
        "an explicit override must not be followed by fallback candidates: %r" % paths
    )


def test_missing_file_under_override_falls_back_to_default_not_another_pack(tmp_path, monkeypatch):
    """The documented fallback is the EMPTY DEFAULT. It must never be another pack found
    by walking parents — that is the silent-supersession defect this card closes."""
    empty_override = tmp_path / "empty_override"
    empty_override.mkdir()
    root = tmp_path / "shared_root"
    _pack(root / "OFFICIAL_DATA", DECOY)
    monkeypatch.setenv("MAMEY_OFFICIAL_DATA", str(empty_override))
    monkeypatch.setenv("MAMEY_DATA_ROOT", str(root))
    with pytest.warns(RuntimeWarning, match="exclusions.json"):
        result = exclusions.load_exclusions()
    assert result == exclusions._DEFAULT
    assert result["hard_excluded"] != ["DECOY-001"]


def test_data_root_wins_when_no_explicit_override(tmp_path, monkeypatch):
    root = tmp_path / "shared_root"
    _pack(root / "OFFICIAL_DATA", OVERRIDE)
    monkeypatch.delenv("MAMEY_OFFICIAL_DATA", raising=False)
    monkeypatch.setenv("MAMEY_DATA_ROOT", str(root))
    paths = exclusions._probe_paths("exclusions.json")
    assert paths == [root / "OFFICIAL_DATA" / "exclusions.json"]
    assert exclusions.load_exclusions()["hard_excluded"] == ["OVERRIDE-001"]


def test_parent_walk_still_used_when_no_env_is_set(monkeypatch):
    """The bundled-tree path is preserved: with no override, the walk is the probe list."""
    monkeypatch.delenv("MAMEY_OFFICIAL_DATA", raising=False)
    monkeypatch.delenv("MAMEY_DATA_ROOT", raising=False)
    paths = exclusions._probe_paths("exclusions.json")
    assert len(paths) > 1
    assert all(p.name == "exclusions.json" and p.parent.name == "OFFICIAL_DATA" for p in paths)


# --- the same contract for official_data_json() --------------------------------------------

def test_official_data_json_override_is_exclusive(tmp_path, monkeypatch):
    override = _pack(tmp_path / "override_pack", {"tier": "OVERRIDE"}, "cohort_assembly_tiers.json")
    root = tmp_path / "shared_root"
    _pack(root / "OFFICIAL_DATA", {"tier": "DECOY"}, "cohort_assembly_tiers.json")
    monkeypatch.setenv("MAMEY_OFFICIAL_DATA", str(override))
    monkeypatch.setenv("MAMEY_DATA_ROOT", str(root))
    assert exclusions.official_data_json("cohort_assembly_tiers.json") == {"tier": "OVERRIDE"}


def test_official_data_json_missing_under_override_returns_caller_default(tmp_path, monkeypatch):
    empty_override = tmp_path / "empty_override"
    empty_override.mkdir()
    root = tmp_path / "shared_root"
    _pack(root / "OFFICIAL_DATA", {"tier": "DECOY"}, "cohort_assembly_tiers.json")
    monkeypatch.setenv("MAMEY_OFFICIAL_DATA", str(empty_override))
    monkeypatch.setenv("MAMEY_DATA_ROOT", str(root))
    with pytest.warns(RuntimeWarning, match="cohort_assembly_tiers.json"):
        result = exclusions.official_data_json("cohort_assembly_tiers.json", {"tier": "CALLER"})
    assert result == {"tier": "CALLER"}


# --- malformed explicit source (added at .403 after an independent QA pass asked for it) ------

def test_malformed_file_under_override_warns_and_uses_default_not_another_pack(tmp_path, monkeypatch):
    """A corrupt file under an explicit override must NOT silently hand the run a different
    pack's governed data. The contract is: warn, then fall back to the documented default.

    This is the nastier sibling of the missing-file case. A missing file is at least an obvious
    operator error; a truncated or half-written JSON looks like a real binding right up until it
    is parsed, and before the exclusive-probe fix the parse failure simply advanced the loop into
    the ancestor walk — swapping in a different cohort's exclusions with only a warning that
    named the wrong problem."""
    override = tmp_path / "override_pack"
    override.mkdir(parents=True, exist_ok=True)
    (override / "exclusions.json").write_text('{"hard_excluded": ["OVERRIDE-001",', encoding="utf-8")
    root = tmp_path / "shared_root"
    _pack(root / "OFFICIAL_DATA", DECOY)
    monkeypatch.setenv("MAMEY_OFFICIAL_DATA", str(override))
    monkeypatch.setenv("MAMEY_DATA_ROOT", str(root))
    with pytest.warns(RuntimeWarning, match="could not read"):
        loaded = exclusions.load_exclusions()
    assert "DECOY-001" not in loaded["hard_excluded"], \
        "a malformed explicit override must never fall through to another pack"


def test_official_data_json_malformed_under_override_returns_caller_default(tmp_path, monkeypatch):
    override = tmp_path / "override_pack"
    override.mkdir(parents=True, exist_ok=True)
    (override / "demo.json").write_text("{not json at all", encoding="utf-8")
    root = tmp_path / "shared_root"
    _pack(root / "OFFICIAL_DATA", {"sentinel": "DECOY"}, filename="demo.json")
    monkeypatch.setenv("MAMEY_OFFICIAL_DATA", str(override))
    monkeypatch.setenv("MAMEY_DATA_ROOT", str(root))
    with pytest.warns(RuntimeWarning, match="could not read"):
        got = exclusions.official_data_json("demo.json", {"sentinel": "CALLER_DEFAULT"})
    assert got == {"sentinel": "CALLER_DEFAULT"}
