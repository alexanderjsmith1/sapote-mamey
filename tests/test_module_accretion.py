"""test_module_accretion.py — the module-accretion gate.

The gate fails a cut that adds a mamey/ module not in MODULE_MANIFEST.txt and not
justified in the newest CHANGELOG entry. These tests pin PASS on a matching tree,
FAIL on an unjustified addition, and PASS when the addition is justified.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
GATE = ROOT / "tools" / "check_module_accretion.py"


def _load_gate():
    spec = importlib.util.spec_from_file_location("check_module_accretion", GATE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_gate_module_loads():
    g = _load_gate()
    assert hasattr(g, "check")
    assert hasattr(g, "current_modules")
    assert hasattr(g, "manifest_modules")


def test_manifest_exists_and_lists_modules():
    manifest = ROOT / "MODULE_MANIFEST.txt"
    assert manifest.exists(), "MODULE_MANIFEST.txt must ship as the accretion baseline"
    g = _load_gate()
    known = g.manifest_modules()
    assert len(known) > 100, "manifest should list the full module set"
    # the two Cut A modules must be tracked
    assert "mamey/package_map.py" in known
    assert "mamey/manifest_schema.py" in known


def test_gate_passes_on_matching_tree():
    """With the shipped manifest matching the tree, the gate returns 0 (PASS)."""
    g = _load_gate()
    rc = g.check()
    assert rc == 0, "accretion gate should PASS when tree matches MODULE_MANIFEST.txt"


def test_current_matches_manifest_exactly():
    """No drift: every current module is in the manifest and vice versa."""
    g = _load_gate()
    mods, unreadable = g.current_modules()
    assert not unreadable, f"scan of mamey/ hit unreadable director(y/ies): {unreadable}"
    cur = set(mods)
    known = g.manifest_modules()
    added = cur - known
    removed = known - cur
    # G1 (.406): manifest_modules() is the SEALED baseline (SOURCE_CHECKSUMS). On a composing tree,
    # additions are allowed only when justified in the newest CHANGELOG entry.
    justified = g.justified_modules(g.newest_changelog_entry())
    unjustified = {m for m in added if m.split("/")[-1] not in justified}
    assert not unjustified, f"modules present but not justified in CHANGELOG (accretion): {unjustified}"
    assert not removed, f"manifest lists modules not present (stale): {removed}"


def test_justified_modules_parses_changelog_lines():
    g = _load_gate()
    sample = (
        "# v9.7.159 — test\n"
        "- Accretion-justified: package_map.py — new package-discovery map\n"
        "- Consolidates: blastp_followup.py into blastp/\n"
    )
    justified = g.justified_modules(sample)
    assert "package_map.py" in justified
    assert "blastp_followup.py" in justified


def test_gate_fails_on_unjustified_addition(tmp_path, monkeypatch):
    """Simulate an added module absent from both manifest and CHANGELOG justification."""
    g = _load_gate()
    # monkeypatch current_modules to inject a phantom module
    real, unreadable = g.current_modules()
    real["mamey/_phantom_test_module.py"] = "test phantom"
    monkeypatch.setattr(g, "current_modules", lambda: (real, unreadable))
    monkeypatch.setattr(g, "newest_changelog_entry", lambda: "# v9.7.159\n- nothing justified here\n")
    rc = g.check()
    assert rc == 1, "gate must FAIL on an unjustified module addition"


def test_gate_passes_when_addition_is_justified(monkeypatch):
    g = _load_gate()
    real, unreadable = g.current_modules()
    real["mamey/_phantom_test_module.py"] = "test phantom"
    monkeypatch.setattr(g, "current_modules", lambda: (real, unreadable))
    # G1 (.406): keep the tree's own justifications (the baseline is the seal, so a composing tree
    # may already carry justified additions) and add the phantom's line on top.
    entry = g.newest_changelog_entry()
    monkeypatch.setattr(
        g, "newest_changelog_entry",
        lambda: entry + "\n- Accretion-justified: _phantom_test_module.py — reason\n")
    rc = g.check()
    assert rc == 0, "gate must PASS when the addition is justified in the CHANGELOG"
