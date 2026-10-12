"""Guards for the companion-tools registry (AMBER v9.7.331).

The companion tools are DETECTED, NOT BUNDLED. These tests validate that the registry
loads and is well-formed, and that the probe path is offline-safe (never raises, never
requires a tool to be installed). CI does NOT need any companion tool present — probing
just reports everything absent, which is a valid, non-failing state.
"""
import json
import pathlib

import mamey.companion_tools as C


def test_registry_loads_and_ids_unique():
    reg = C.load_registry()
    assert len(reg) >= 15, "expected the full companion-tools set"
    ids = [t.id for t in reg]
    assert len(ids) == len(set(ids)), "duplicate companion tool ids"
    # the tools we never want to silently lose from the transferable layer:
    assert {"antismash", "bigscape", "clinker", "cblaster", "gecco",
            "pygenomeviz", "pycirclize", "prodigal", "muscle", "iqtree",
            "fastani", "gtotree", "ncbi_datasets", "skani", "gtdbtk"} <= set(ids)


def test_every_tool_is_well_formed():
    for t in C.load_registry():
        assert t.category in C.VALID_CATEGORIES, f"{t.id}: bad category {t.category}"
        assert t.requirement in C.VALID_REQUIREMENTS, f"{t.id}: bad requirement {t.requirement}"
        assert t.purpose and t.consumes and t.produces, f"{t.id}: missing prose"
        assert t.detection_command, f"{t.id}: missing detection command"
        assert t.install, f"{t.id}: no install recipe"
        for entry in t.install:
            assert "platform" in entry and "command" in entry, f"{t.id}: malformed install entry"


def test_antismash_marked_required_upstream():
    reg = {t.id: t for t in C.load_registry()}
    assert reg["antismash"].requirement == "REQUIRED-upstream"
    assert reg["antismash"].category == "upstream-input"
    # heavy-DB tools are marked on-request
    assert reg["gtdbtk"].requirement == "on-request"
    assert reg["skani"].requirement == "on-request"


def test_install_hint_never_empty():
    for t in C.load_registry():
        hint = C.install_hint_for(t, plat="linux")
        assert hint and hint != "(no install recipe recorded)", f"{t.id}: empty install hint"


def test_probe_is_offline_safe_without_detection():
    # run_detection=False must not touch subprocess and must report all-absent cleanly.
    probes = C.probe_tools(run_detection=False)
    assert len(probes) == len(C.load_registry())
    assert all(p.present is False and p.detected_version is None for p in probes)
    assert all(p.install_hint for p in probes)


def test_probe_never_raises_with_detection(monkeypatch):
    # Exercise the full registry on a hermetically missing PATH, not live optional software.
    monkeypatch.setattr(C.shutil, "which", lambda name: None)
    def missing(*args, **kwargs):
        raise FileNotFoundError("synthetic missing interpreter/executable")
    monkeypatch.setattr(C.subprocess, "run", missing)
    probes = C.probe_tools(run_detection=True)
    assert len(probes) == len(C.load_registry())
    for p in probes:
        assert isinstance(p.present, bool)


def test_registry_json_matches_declared_categories():
    path = pathlib.Path(C.__file__).resolve().parent / "data" / "companion_tools.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["detected_not_bundled"] is True
    assert data["offline_core_preserved"] is True
    declared = set(data["categories"])
    used = {t["category"] for t in data["tools"]}
    assert used <= declared, f"tool categories not in declared list: {used - declared}"


def test_corason_is_optional_manual_and_not_a_core_or_runtime_claim(monkeypatch):
    tools = {x.id: x for x in C.load_registry()}
    corason = tools['corason']
    assert corason.requirement == 'optional'
    assert corason.category == 'synteny'
    assert corason.network_required is False
    assert corason.reference_db_required is False
    assert 'NOT_PROBED' in corason.detection_command
    assert corason.expected_version == ''
    assert corason.verify_flag is False
    assert 'aa70dddebafb210445794fd24b1c6b2e4177c58c' in str(corason.install)
    assert 'PRIVATE' in corason.produces
    assert 'query-only' in corason.purpose and 'BLAST-order' in corason.purpose
    probes = C.probe_tools([corason], run_detection=False)
    assert len(probes) == 1 and probes[0].present is False

    # A manual entry never executes its marker or infers local installation.
    def forbidden(*args, **kwargs):
        raise AssertionError("manual entry must not launch a child")
    monkeypatch.setattr(C.subprocess, "run", forbidden)
    probes = C.probe_tools([corason], run_detection=True)
    assert len(probes) == 1 and probes[0].present is False
    assert probes[0].detected_version is None
    assert probes[0].probe_status == "MANUAL_NOT_PROBED"
