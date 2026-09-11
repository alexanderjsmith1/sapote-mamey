from __future__ import annotations

import json
import csv

from mamey.package_continuity_widgets import (
    assess_continuity,
    assess_sapote_engine_compatibility,
    compare_package_fingerprints,
    explain_validation_refusal,
    preflight_handoff,
)


def _inventory_package(root, strain, rows):
    package = root / f"{strain}_package"
    package.mkdir(parents=True)
    path = package / f"{strain}_2_inventory.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["BGC_ID", "Node_ID", "Start", "End", "Products"])
        writer.writeheader()
        writer.writerows(rows)
    return package


def test_fingerprint_comparator_ignores_alias_renumbering_but_reports_it(tmp_path):
    prior = _inventory_package(tmp_path / "prior", "GENERIC-001", [
        {"BGC_ID": "BGC001", "Node_ID": "node_1", "Start": 10, "End": 100, "Products": "NRPS"},
    ])
    current = _inventory_package(tmp_path / "current", "GENERIC-001", [
        {"BGC_ID": "BGC009", "Node_ID": "node_1", "Start": 10, "End": 100, "Products": "NRPS"},
    ])
    result = compare_package_fingerprints(prior, current)
    assert result["comparison_state"] == "SAME"
    assert result["alias_reconciliation_summary"]["renumbered_count"] == 1
    serialized = json.dumps(result)
    assert "GENERIC-001" not in serialized and "BGC009" not in serialized


def test_fingerprint_comparator_detects_locus_change(tmp_path):
    prior = _inventory_package(tmp_path / "prior", "GENERIC-001", [
        {"BGC_ID": "BGC001", "Node_ID": "node_1", "Start": 10, "End": 100, "Products": "NRPS"},
    ])
    current = _inventory_package(tmp_path / "current", "GENERIC-001", [
        {"BGC_ID": "BGC001", "Node_ID": "node_1", "Start": 10, "End": 140, "Products": "NRPS"},
    ])
    result = compare_package_fingerprints(prior, current)
    assert result["comparison_state"] == "CHANGED"
    assert result["fingerprints"]["prior_inventory_sha256"] != result["fingerprints"]["current_inventory_sha256"]


def test_fingerprint_comparator_refuses_cross_strain_comparison(tmp_path):
    prior = _inventory_package(tmp_path / "prior", "GENERIC-001", [])
    current = _inventory_package(tmp_path / "current", "GENERIC-002", [])
    result = compare_package_fingerprints(prior, current)
    assert result["comparison_state"] == "STRAIN_CONTRADICTION"


def _package(tmp_path, *, matching=True, gate_status="MAMEY_COMPLETE"):
    package = tmp_path / "portable_package"
    package.mkdir()
    (package / "manifest.json").write_text(json.dumps({"strain_id": "GENERIC-001"}), encoding="utf-8")
    short_id = "GENERIC-001" if matching else "GENERIC-002"
    (package / "manifest_short.json").write_text(json.dumps({"strain_id": short_id}), encoding="utf-8")
    (package / "gate_validation.json").write_text(json.dumps({
        "status": gate_status,
        "file_presence": "PASS",
        "rggmci_gate": "PASS",
        "depth_floor": "PASS",
        "gold_completeness": "PASS",
    }), encoding="utf-8")
    (package / "checksums_sha256.txt").write_text("abc  manifest.json\n", encoding="utf-8")
    (package / "GENERIC-001_2b_bgc_crosswalk.csv").write_text("bgc_id,node\n", encoding="utf-8")
    return package


def test_continuity_requires_matching_independent_identity_receipts(tmp_path):
    result = assess_continuity(_package(tmp_path, matching=False))
    assert result["widget_id"] == "W402-14"
    assert result["continuity_decision"] == "WAITING_ON_BINDING"
    assert result["identity_binding"]["state"] == "CONTRADICTION"


def _engine_snapshot(tmp_path, *, legacy_risks=False):
    snapshot = {
        "schema_version": "sapote_engine_continuity_bridge_v1",
        "baseline": {"bundle_version": "9.7.401", "source_inventory_sha256": "a" * 64},
        "package_locator": "package://sealed-input",
        "output": {
            "root_locator": "project://candidate-output",
            "parent_state": "PREEXISTING_DECLARED",
            "existing_output_policy": "REFUSE_IF_EXISTS",
            "candidate_zip_policy": "CREATE_NEW_NO_OVERWRITE",
            "privacy_review": "REQUIRED",
        },
        "admission": {
            "invalid_locus_row_policy": "REFUSE_INVALID",
            "source_schema_contract": "DECLARED_VERSIONED",
            "error_locator_policy": "LOGICAL_LOCATOR_ONLY",
        },
        "import_reconciliation": {
            "source_bgc_count": 1,
            "imported_record_count": 1,
            "invalid_identity_row_count": 0,
            "skipped_invalid_identity_row_count": 0,
            "duplicate_identity_row_count": 0,
            "incomplete_identity_row_count": 0,
        },
        "phylogenomics": {
            "requested": True,
            "comparator": "comparator-set-v1",
            "tree_sha256": "b" * 64,
            "alignment_sha256": "c" * 64,
            "roster_sha256": "d" * 64,
            "tool": "generic-tool",
            "model": "generic-model",
            "seed": "1",
            "outgroup": "generic-outgroup",
            "tip_crosswalk_sha256": "e" * 64,
        },
    }
    if legacy_risks:
        snapshot["package_locator"] = r"C:\legacy\absolute\package"
        snapshot["output"]["existing_output_policy"] = "OVERWRITE"
        snapshot["admission"]["invalid_locus_row_policy"] = "SKIP"
        snapshot["import_reconciliation"] = {
            "source_bgc_count": 1,
            "imported_record_count": 0,
            "invalid_identity_row_count": 0,
            "skipped_invalid_identity_row_count": 1,
            "duplicate_identity_row_count": 0,
            "incomplete_identity_row_count": 0,
        }
        snapshot["phylogenomics"] = {"requested": True, "comparator": "only-binding"}
    path = tmp_path / "engine_snapshot.json"
    path.write_text(json.dumps(snapshot), encoding="utf-8")
    return path


def test_engine_bridge_accepts_current_bound_generic_snapshot(tmp_path):
    result = assess_sapote_engine_compatibility(_engine_snapshot(tmp_path), "9.7.401", "a" * 64)
    assert result["widget_id"] == "W402-14"
    assert result["compatibility_decision"] == "CURRENT_WORKFLOW_OWNER_COMPATIBLE"
    assert result["phylogenomics_state"] == "BOUND"


def test_engine_bridge_holds_legacy_path_skip_and_underbound_phylogenomics(tmp_path):
    result = assess_sapote_engine_compatibility(_engine_snapshot(tmp_path, legacy_risks=True), "9.7.401", "a" * 64)
    holds = {(item["kind"], item["field"]) for item in result["compatibility_holds"]}
    assert result["compatibility_decision"] == "WAITING_ON_COMPATIBILITY_BINDING"
    assert ("PATH_BEARING_OR_MISSING_PACKAGE_LOCATOR", "package_locator") in holds
    assert ("ADMISSION_CONTRACT_MISSING", "admission.invalid_locus_row_policy") in holds
    assert ("PHYLOGENOMICS_BINDING_MISSING", "phylogenomics.tree_sha256") in holds


def test_engine_bridge_refuses_one_to_zero_import_and_absolute_locator_before_success(tmp_path):
    result = assess_sapote_engine_compatibility(_engine_snapshot(tmp_path, legacy_risks=True), "9.7.401", "a" * 64)
    holds = {item["kind"] for item in result["compatibility_holds"]}
    assert result["compatibility_decision"] == "WAITING_ON_COMPATIBILITY_BINDING"
    assert "PATH_BEARING_OR_MISSING_PACKAGE_LOCATOR" in holds
    assert "SOURCE_TO_IMPORT_COUNT_MISMATCH" in holds
    assert "INVALID_IDENTITY_ROWS_OBSERVED" in holds
    assert result["import_reconciliation"]["state"] == "REFUSE_UNRECONCILED"


def test_refusal_translator_does_not_bypass_nonpass_gate(tmp_path):
    result = explain_validation_refusal(_package(tmp_path, gate_status="FAIL"))
    assert result["widget_id"] == "W402-15"
    assert result["promotion_decision"] == "REFUSE_PROMOTION"
    assert result["safe_next_action"].startswith("Run the named owner")


def test_refusal_translator_accepts_actual_complete_gate_shape(tmp_path):
    """validate_package writes depth_floor_breakdown, not a depth_floor gate."""
    package = _package(tmp_path, gate_status="MAMEY_COMPLETE")
    gate_path = package / "gate_validation.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    gate.pop("depth_floor")
    gate["depth_floor_breakdown"] = {
        "total_bgcs": 1,
        "full_mode_b": 1,
        "abbreviated_ledger": 0,
    }
    gate_path.write_text(json.dumps(gate), encoding="utf-8")

    result = explain_validation_refusal(package)
    assert result["promotion_decision"] == "NO_REFUSAL_OBSERVED"
    assert result["refusal_reasons"] == []


def test_handoff_preflight_is_package_only_without_raw_zip(tmp_path):
    result = preflight_handoff(_package(tmp_path))
    assert result["widget_id"] == "W402-16"
    assert result["handoff_shape"] == "PACKAGE_ONLY"
    assert result["constraint"].startswith("This preflight does not create")
