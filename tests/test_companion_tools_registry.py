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


def test_probe_never_raises_with_detection():
    # Real detection may find nothing in CI; it must still return a clean list, never raise.
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
