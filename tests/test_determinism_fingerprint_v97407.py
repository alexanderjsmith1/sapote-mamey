import hashlib
import json
from pathlib import Path

import tools.determinism_fingerprint as determinism
from tools.determinism_fingerprint import compare_reports, fingerprint_pair, main, report_ok, validate_inventory


def _package(root, score):
    root.mkdir()
    (root / "manifest.json").write_text('{"strain_id":"PUBLIC-FIX"}')
    (root / "PUBLIC-FIX_2_inventory.csv").write_text(
        "BGC_ID,Node_ID,antiSMASH_Region,Score\nBGC001,contig_001,region001," + score + "\n"
    )
    return root


def test_pair_reports_full_identity_column_and_value(tmp_path):
    left = _package(tmp_path / "left", "1")
    right = _package(tmp_path / "right", "2")
    result = fingerprint_pair("case", left, right, ["manifest.json"])
    assert result["typed_bgc_cell_differences"] == [{
        "file": "PUBLIC-FIX_2_inventory.csv",
        "identity": "PUBLIC-FIX / contig_001 / region001 / BGC001",
        "column": "Score", "left": "1", "right": "2",
    }]


def test_compare_reports_keeps_typed_identity(tmp_path):
    left = _package(tmp_path / "left", "1")
    right = _package(tmp_path / "right", "2")
    a = {"inputs": {"case": fingerprint_pair("case", left, left, ["manifest.json"])}}
    b = {"inputs": {"case": fingerprint_pair("case", right, right, ["manifest.json"])}}
    changes = compare_reports(b, a)["changes"]
    assert any(row["identity"] == "PUBLIC-FIX / contig_001 / region001 / BGC001" and row["column"] == "Score" for row in changes)


def test_shipped_inventory_covers_discovered_materials():
    spec = json.loads((__import__("pathlib").Path(__file__).parents[1] / "mamey/data/determinism_inventory.json").read_text())
    assert validate_inventory(spec)["complete"] is True
    assert validate_inventory(spec)["missing_hash_bindings"] == []
    assert validate_inventory(spec)["hash_mismatches"] == []


def test_inventory_coverage_fails_closed_on_unreadable_directory(monkeypatch):
    spec = json.loads((Path(__file__).parents[1] / "mamey/data/determinism_inventory.json").read_text())
    monkeypatch.setattr(determinism, "safe_walk_files", lambda *args, **kwargs: ([], ["locked-fixture-dir"]))
    coverage = validate_inventory(spec)
    assert coverage["complete"] is False
    assert coverage["unreadable_directories"] == ["locked-fixture-dir", "locked-fixture-dir"]


def test_typed_csv_identity_rejects_short_node_token(tmp_path):
    left = _package(tmp_path / "left", "1")
    right = _package(tmp_path / "right", "1")
    for package in (left, right):
        (package / "PUBLIC-FIX_2_inventory.csv").write_text(
            "BGC_ID,Node_ID,antiSMASH_Region,Score\nBGC001,NODE_1,region001,1\n"
        )
    result = fingerprint_pair("case", left, right)
    assert result["canonical_csv_cells"] == {}
    assert len(result["identity_holds"]) == 2


def _report(result, *, status="PASS"):
    result["status"] = status
    return {
        "bundle_version": "9.7.406",
        "engine_version": "1.9.146",
        "inventory_sha256": "inventory",
        "inventory_coverage": {"complete": True},
        "inputs": {"case": result},
    }


def test_compare_fails_on_current_internal_pair_divergence(tmp_path):
    left = _package(tmp_path / "left", "1")
    right = _package(tmp_path / "right", "1")
    (right / "unexpected.txt").write_text("unexpected")
    baseline_pair = fingerprint_pair("case", left, left)
    current_pair = fingerprint_pair("case", left, right)
    comparison = compare_reports(_report(current_pair, status="FAIL_PARITY"), _report(baseline_pair))
    assert comparison["match"] is False
    assert comparison["current_report_ok"] is False
    assert any(row["column"] in {"status", "current_internal_status"} for row in comparison["changes"])


def test_manifest_substantive_change_is_not_masked_as_volatile(tmp_path):
    left = _package(tmp_path / "left", "1")
    right = _package(tmp_path / "right", "1")
    (left / "manifest.json").write_text('{"strain_id":"PUBLIC-FIX","scientific_state":"A"}')
    (right / "manifest.json").write_text('{"strain_id":"PUBLIC-FIX","scientific_state":"B"}')
    result = fingerprint_pair("case", left, right)
    assert "manifest.json" in result["byte_differences"]
    assert result["non_timestamp_byte_parity"] is False


def test_timestamp_normalization_is_field_level_and_propagates_through_hashes(tmp_path):
    packages = []
    for label, stamp in (("left", "2026-01-01T00:00:00Z"), ("right", "2026-01-02T00:00:00Z")):
        package = _package(tmp_path / label, "1")
        register = package / "PUBLIC-FIX_judgment_register.json"
        register.write_text(json.dumps({"mamey_init_timestamp": stamp, "judgment_status": "PENDING"}))
        raw_digest = hashlib.sha256(register.read_bytes()).hexdigest()
        manifest = {"strain_id": "PUBLIC-FIX", "files": [{"path": register.name, "sha256": raw_digest,
                                                              "bytes": register.stat().st_size}]}
        (package / "manifest.json").write_text(json.dumps(manifest))
        manifest_digest = hashlib.sha256((package / "manifest.json").read_bytes()).hexdigest()
        (package / "checksums_sha256.txt").write_text(
            f"{raw_digest}  {register.name}\n{manifest_digest}  manifest.json\n"
        )
        packages.append(package)
    result = fingerprint_pair("case", packages[0], packages[1])
    assert result["byte_differences"] == []
    assert set(result["volatile_field_only_differences"]) == {
        "PUBLIC-FIX_judgment_register.json", "checksums_sha256.txt", "manifest.json",
    }


def test_compare_gates_versions_inventory_hash_input_hash_and_probe_status():
    baseline = {
        "bundle_version": "9.7.406", "engine_version": "1.9.146", "inventory_sha256": "A",
        "inventory_coverage": {"complete": True},
        "inputs": {"probe": {"status": "PASS", "input_sha256": "X", "byte_parity": True}},
    }
    current = json.loads(json.dumps(baseline))
    current.update(bundle_version="9.7.407", engine_version="1.9.147", inventory_sha256="B")
    current["inputs"]["probe"].update(status="FAIL", input_sha256="Y", byte_parity=False)
    comparison = compare_reports(current, baseline)
    columns = {row["column"] for row in comparison["changes"]}
    assert {"bundle_version", "engine_version", "inventory_sha256", "status", "input_sha256", "byte_parity"} <= columns
    assert comparison["match"] is False
    assert report_ok(current) is False


def test_cli_returns_nonzero_when_current_pair_fails(tmp_path):
    left = _package(tmp_path / "left", "1")
    right = _package(tmp_path / "right", "2")
    out = tmp_path / "fingerprint.json"
    code = main(["--out", str(out), "--package-pair", "example_smoke", str(left), str(right)])
    assert code == 1
    assert json.loads(out.read_text())["inputs"]["example_smoke"]["status"] == "FAIL_PARITY"
import importlib.util


def _tool():
    path = Path(__file__).parents[1] / "tools" / "determinism_fingerprint.py"
    spec = importlib.util.spec_from_file_location("determinism_fingerprint", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_compare_reports_bgc_column_and_value(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(); b.mkdir()
    for root, score in ((a, "1"), (b, "2")):
        (root / "manifest.json").write_text('{"strain_id":"PUBLIC-FIX"}')
        (root / "S_2_inventory.csv").write_text(
            "BGC_ID,Node_ID,antiSMASH_Region,Score\n"
            "BGC001,contig_001,region001," + score + "\n"
        )
    result = _tool().fingerprint_pair("case", a, b)
    assert result["typed_bgc_cell_differences"] == [{
        "file": "S_2_inventory.csv",
        "identity": "PUBLIC-FIX / contig_001 / region001 / BGC001",
        "column": "Score",
        "left": "1",
        "right": "2",
    }]
