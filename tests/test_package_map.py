"""test_package_map.py — PACKAGE_MAP generator + seal-path auto-emit gate.

Covers the Cut A package-discovery map: the generator resolves spec artifacts
against a real package, the read-completeness verdict distinguishes real gaps
from mode-gated absences, and the seal path auto-emits PACKAGE_MAP.json.

The gene-context / cds-table / deep-data reads for §4 (the pasted-failure
section) must resolve as required-present on a gold package — this is the
regression guard for "files there but not found".
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from mamey.package_map import (
    build_package_map,
    write_package_map,
    default_spec_path,
    _resolve_artifact,
)


def _mk_pkg(tmp_path: Path, files: dict[str, str]) -> Path:
    pkg = tmp_path / "package"
    pkg.mkdir()
    for rel, content in files.items():
        p = pkg / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return pkg


def _minimal_gold_pkg(tmp_path: Path) -> Path:
    """A package carrying the §4 required reads + a manifest with source_scans."""
    return _mk_pkg(tmp_path, {
        "manifest.json": json.dumps({
            "strain_id": "TEST",
            "source_scans": {"chitinase": {}, "umed": {}, "resistance": {}},
            "assembly": {"n50": 1000, "contigs": 1},
            "files": [],
        }),
        "TEST_1_intake.json": json.dumps({"strain_id": "TEST"}),
        "TEST_4_triage_board.csv": "BGC_ID,Contig,Node_ID,antiSMASH_Region\nBGC001,NODE_1,NODE_1,region001\n",
        "TEST_2_inventory.csv": "bgc_id\nBGC001\n",
        "TEST_2b_bgc_crosswalk.csv": "bgc_id,node\nBGC001,NODE_1\n",
        "TEST_gene_context.jsonl": '{"schema_version":"gene_context/1.0"}\n{"bgc_id":"BGC001","cds":[]}\n',
        "TEST_cds_table.csv": "bgc_id,contig,locus_tag\nBGC001,NODE_1,x\n",
        "deep_data.json": json.dumps({"domain_hits": [{"domain": "p450"}], "bgc_profile": []}),
    })


def test_spec_loads_and_is_consistent():
    """The bundled spec parses and every section read maps to a defined artifact."""
    spec = json.loads(default_spec_path().read_text(encoding="utf-8"))
    arts = set(spec["artifacts"])
    for num, sec in spec["sections"].items():
        for r in sec.get("required_reads", []) + sec.get("optional_reads", []):
            assert r in arts, f"§{num} reads undefined artifact {r!r}"


def test_resolve_strain_prefixed_file(tmp_path):
    pkg = _minimal_gold_pkg(tmp_path)
    st = _resolve_artifact("{strain}_gene_context.jsonl", pkg, "TEST")
    assert st["present"] is True
    assert st["resolved_path"] == "TEST_gene_context.jsonl"


def test_resolve_manifest_hash_key(tmp_path):
    """manifest.json#source_scans resolves by json key, not a standalone file."""
    pkg = _minimal_gold_pkg(tmp_path)
    st = _resolve_artifact("manifest.json#source_scans", pkg, "TEST")
    assert st["present"] is True
    assert "source_scans" in st["resolved_path"]


def test_resolve_absent_is_honest(tmp_path):
    pkg = _minimal_gold_pkg(tmp_path)
    st = _resolve_artifact("domain_rows_long.csv", pkg, "TEST")
    assert st["present"] is False
    assert st["resolved_path"] is None


def test_section_4_required_reads_present_on_gold(tmp_path):
    """PASTED-FAILURE REGRESSION: §4's deep reads resolve present on a gold-shape package."""
    pkg = _minimal_gold_pkg(tmp_path)
    m = build_package_map(pkg)  # bundled default spec
    s4 = m["sections"]["4"]
    present = set(s4["required_reads_present"])
    assert "{strain}_gene_context.jsonl" in present
    assert "deep_data.json" in present
    assert s4["read_completeness"] == "COMPLETE"


def test_mode_gated_not_reported_as_gap(tmp_path):
    """A gold-only artifact absent from a lean package is MODE_GATED, never a GAP."""
    pkg = _minimal_gold_pkg(tmp_path)
    m = build_package_map(pkg)
    # no section should report a GAP purely because a non-'always' artifact is absent
    for num, s in m["sections"].items():
        if s["read_completeness"] == "GAP":
            # a GAP is only legitimate if an 'always' artifact is truly missing
            assert s["required_reads_hard_missing"], (
                f"§{num} flagged GAP with no hard-missing always-artifact")


def test_write_package_map_creates_file(tmp_path):
    pkg = _minimal_gold_pkg(tmp_path)
    out = write_package_map(pkg)
    assert out.exists()
    d = json.loads(out.read_text(encoding="utf-8"))
    assert d["package_map_version"] == "1.2"
    assert d["strain_id"] == "TEST"
    assert d["summary"]["artifacts_total"] > 0


def test_never_raises_on_malformed_package(tmp_path):
    """Fail-soft: a package missing manifest still produces a map, no exception."""
    pkg = _mk_pkg(tmp_path, {"stray.txt": "x"})
    m = build_package_map(pkg)  # must not raise
    assert m["summary"]["artifacts_present"] == 0 or isinstance(m["summary"]["artifacts_present"], int)


def test_generator_output_is_deterministic(tmp_path):
    pkg = _minimal_gold_pkg(tmp_path)
    a = json.dumps(build_package_map(pkg), sort_keys=True)
    b = json.dumps(build_package_map(pkg), sort_keys=True)
    assert a == b


# ---------------- version-aware LEGACY_ABSENT (spec v0.5+) ----------------

def test_legacy_absent_vs_gap(tmp_path):
    """An always-artifact absent from a package that PREDATES it is LEGACY_ABSENT, not GAP."""
    from mamey.package_map import _predates, _parse_engine_version
    # a v1.9.3 package predates a post-1.9.3 artifact
    assert _predates((1, 9, 3), "post-1.9.3") is True
    # a modern package does not
    assert _predates((1, 9, 104), "post-1.9.3") is False
    # explicit version comparison
    assert _predates((1, 9, 2), "1.9.3") is True
    assert _predates((1, 9, 3), "1.9.3") is False
    # unknown package version is conservative (treat as real gap, not excused)
    assert _predates(None, "post-1.9.3") is False


def test_parse_engine_version(tmp_path):
    from mamey.package_map import _parse_engine_version
    pkg = _mk_pkg(tmp_path, {"manifest.json": json.dumps({"workflow_version": "Mamey v1.9.104"})})
    assert _parse_engine_version(pkg) == (1, 9, 104)
    (tmp_path / "b").mkdir()
    pkg2 = _mk_pkg(tmp_path / "b", {"manifest.json": json.dumps({})})
    assert _parse_engine_version(pkg2) is None


# ---------------- v9.7.160: smoke = not analyzable ----------------

def test_smoke_package_not_analyzable(tmp_path):
    """A smoke package must be flagged analyzable=false (empty triage board -> no Mode B/comparison)."""
    pkg = _mk_pkg(tmp_path, {"manifest.json": json.dumps({"strain_id": "T", "mode": "smoke", "files": []})})
    m = build_package_map(pkg)
    assert m["analyzable"] is False
    assert "NOT ANALYZABLE" in m["analyzable_note"]
    assert m["package_mode"] == "smoke"


def test_gold_package_analyzable(tmp_path):
    pkg = _mk_pkg(tmp_path, {"manifest.json": json.dumps({"strain_id": "T", "mode": "gold", "files": []})})
    m = build_package_map(pkg)
    assert m["analyzable"] is True
    assert m["package_mode"] == "gold"
