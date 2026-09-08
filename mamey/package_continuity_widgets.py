"""Read-only package continuity and refusal-explanation widgets.

W402-14 cross-checks independently-written package receipts and provides a
fail-closed historical Sapote Engine compatibility bridge before a reviewer
resumes work. W402-15 turns a machine gate state into explicit non-bypassable
refusal reasons. W402-16 preflights an internal handoff without creating an
archive. These helpers do not validate, reseal, mutate, export, or release a
package.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path, PureWindowsPath
from typing import Any

from .bgc_alias_history import load_inventory, reconcile


def _read_object(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.is_file():
        return None, "FILE_ABSENT"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, "JSON_UNREADABLE"
    if not isinstance(value, dict):
        return None, "JSON_OBJECT_REQUIRED"
    return value, None


def _package_hold(widget_id: str, decision: str, reason: str) -> dict[str, Any]:
    return {
        "schema_version": "mamey_package_continuity_widget_v1",
        "widget_id": widget_id,
        "status": "HELD_WITH_EXACT_REASON",
        "audience": "operator reviewing an existing package",
        "decision": decision,
        "missingness": {"kind": reason, "detail": "The widget will not infer a package state from a missing or unreadable receipt."},
        "privacy_portability": "Read-only; returns only package-relative artifact names.",
    }


def assess_continuity(package_dir: str | Path) -> dict[str, Any]:
    """W402-14: check whether the small state receipts agree before resumption."""
    package = Path(package_dir)
    if not package.is_dir():
        return _package_hold("W402-14", "whether a package has a coherent resumable state", "PACKAGE_DIRECTORY_ABSENT")
    manifest, manifest_error = _read_object(package / "manifest.json")
    if manifest_error:
        return _package_hold("W402-14", "whether a package has a coherent resumable state", f"MANIFEST_{manifest_error}")
    short, short_error = _read_object(package / "manifest_short.json")
    gate, gate_error = _read_object(package / "gate_validation.json")
    observations = []
    for name, error in (("manifest_short.json", short_error), ("gate_validation.json", gate_error)):
        observations.append({"artifact": name, "state": "PRESENT" if error is None else error})
    manifest_strain = manifest.get("strain_id")
    short_strain = short.get("strain_id") if short else None
    identity_state = "UNBOUND"
    if manifest_strain and short_strain:
        identity_state = "MATCH" if str(manifest_strain) == str(short_strain) else "CONTRADICTION"
    elif manifest_strain or short_strain:
        identity_state = "PARTIAL"
    decision = "RESUME_REVIEW_READY" if identity_state == "MATCH" and not short_error and not gate_error else "WAITING_ON_BINDING"
    return {
        "schema_version": "mamey_package_continuity_widget_v1",
        "widget_id": "W402-14",
        "status": "RUNNABLE_CANDIDATE",
        "audience": "operator resuming a package review",
        "decision": "whether a package has a coherent resumable state",
        "input_schema": {"package_dir": "directory with manifest.json, manifest_short.json, and gate_validation.json"},
        "existing_owner": "mamey.session_resume.build_resume; this widget only binds its prerequisite receipts",
        "continuity_decision": decision,
        "identity_binding": {"state": identity_state, "manifest_short_vs_manifest": "MATCH" if identity_state == "MATCH" else identity_state},
        "receipt_observations": observations,
        "missingness": {"kind": "NONE" if decision == "RESUME_REVIEW_READY" else "RECEIPT_OR_IDENTITY_BINDING_INCOMPLETE"},
        "privacy_portability": "No strain identifier, evidence value, or absolute path is emitted by this widget.",
    }


def _inventory_fingerprint(rows: list[dict[str, Any]]) -> str:
    """Hash the physical-locus inventory without serializing package paths.

    BGC aliases are intentionally excluded: alias changes are reported through
    the canonical alias reconciler, while the fingerprint answers whether the
    underlying normalized locus/product inventory changed.
    """
    normalized = []
    for row in rows:
        locus = row.get("locus")
        normalized.append({
            "locus": list(locus) if locus is not None else None,
            "products": str(row.get("products", "")),
        })
    normalized.sort(key=lambda item: (
        item["locus"] is None,
        item["locus"] or ["", -1, -1],
        item["products"],
    ))
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compare_package_fingerprints(
    prior_package_dir: str | Path,
    current_package_dir: str | Path,
) -> dict[str, Any]:
    """B1: compare two same-strain package inventories, read-only and fail-closed.

    Physical-locus matching remains owned by :mod:`mamey.bgc_alias_history`.
    This widget emits hashes and aggregate reconciliation counts only: it never
    exposes a private strain identifier, an absolute path, or a bare BGC alias.
    """
    try:
        prior_strain, prior_rows = load_inventory(prior_package_dir)
        current_strain, current_rows = load_inventory(current_package_dir)
    except (FileNotFoundError, OSError, csv.Error, UnicodeDecodeError) as exc:
        result = _package_hold(
            "W406-B1",
            "whether two sealed package inventories represent the same normalized physical-locus set",
            "INVENTORY_UNREADABLE_OR_ABSENT",
        )
        result["error_type"] = type(exc).__name__
        return result
    if prior_strain != current_strain:
        return {
            "schema_version": "mamey_package_fingerprint_comparator_v1",
            "widget_id": "W406-B1",
            "status": "HELD_WITH_EXACT_REASON",
            "comparison_state": "STRAIN_CONTRADICTION",
            "missingness": {"kind": "SAME_STRAIN_BINDING_REQUIRED"},
            "privacy_portability": "No strain identifier, BGC alias, evidence value, or absolute path is emitted.",
        }
    prior_hash = _inventory_fingerprint(prior_rows)
    current_hash = _inventory_fingerprint(current_rows)
    history = reconcile(prior_rows, current_rows)
    return {
        "schema_version": "mamey_package_fingerprint_comparator_v1",
        "widget_id": "W406-B1",
        "status": "RUNNABLE_CANDIDATE",
        "decision": "whether two same-strain package inventories have the same normalized physical-locus set",
        "comparison_state": "SAME" if prior_hash == current_hash else "CHANGED",
        "fingerprints": {
            "prior_inventory_sha256": prior_hash,
            "current_inventory_sha256": current_hash,
        },
        "row_counts": {"prior": len(prior_rows), "current": len(current_rows)},
        "alias_reconciliation_summary": {
            "renumbered_count": len(history["renumbered"]),
            "unmatched_prior_count": len(history["unmatched_prior"]),
            "unmatched_current_count": len(history["unmatched_current"]),
        },
        "existing_owner": "mamey.bgc_alias_history.reconcile",
        "claim_ceiling": "Physical-locus continuity only; no product identity, novelty, activity, or release claim; judgment deferred.",
        "privacy_portability": "No strain identifier, BGC alias, evidence value, or absolute path is emitted.",
    }


_PHYLOGENOMICS_BINDINGS = (
    "comparator", "tree_sha256", "alignment_sha256", "roster_sha256",
    "tool", "model", "seed", "outgroup", "tip_crosswalk_sha256",
)
_IMPORT_RECONCILIATION_COUNTS = (
    "source_bgc_count",
    "imported_record_count",
    "invalid_identity_row_count",
    "skipped_invalid_identity_row_count",
    "duplicate_identity_row_count",
    "incomplete_identity_row_count",
)


def _is_logical_locator(value: Any) -> bool:
    """Accept a non-empty logical locator, never an absolute/user-home path."""
    if not isinstance(value, str) or not value.strip():
        return False
    text = value.strip()
    return not (Path(text).is_absolute() or PureWindowsPath(text).is_absolute() or text.startswith(("~", "file://")))


def _is_nonnegative_count(value: Any) -> bool:
    """Accept declared whole-row counts while rejecting booleans and negatives."""
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def assess_sapote_engine_compatibility(
    snapshot_path: str | Path,
    expected_bundle_version: str,
    expected_source_inventory_sha256: str,
) -> dict[str, Any]:
    """W402-14: bridge a historical engine snapshot to the current workflow owner.

    The bridge admits no evidence and runs no candidate engine. It checks that a
    snapshot binds the current baseline, uses logical rather than absolute
    locators, refuses invalid locus rows, declares versioned source schemas,
    carries all requested phylogenomics bindings, and protects candidate-output
    creation and privacy review. Any omitted or mismatched contract is a typed
    compatibility hold rather than a reason to rebase the historical package.
    """
    snapshot, error = _read_object(Path(snapshot_path))
    if error:
        return _package_hold("W402-14", "whether a historical Sapote Engine concept can enter the current workflow as a compatibility bridge", f"ENGINE_SNAPSHOT_{error}")
    issues: list[dict[str, str]] = []
    if snapshot.get("schema_version") != "sapote_engine_continuity_bridge_v1":
        issues.append({"kind": "SNAPSHOT_SCHEMA_UNSUPPORTED", "field": "schema_version"})
    baseline = snapshot.get("baseline")
    if not isinstance(baseline, dict):
        issues.append({"kind": "BASELINE_BINDING_MISSING", "field": "baseline"})
        baseline = {}
    if baseline.get("bundle_version") != expected_bundle_version:
        issues.append({"kind": "BASELINE_VERSION_MISMATCH", "field": "baseline.bundle_version"})
    if baseline.get("source_inventory_sha256") != expected_source_inventory_sha256:
        issues.append({"kind": "BASELINE_INVENTORY_MISMATCH", "field": "baseline.source_inventory_sha256"})
    if not _is_logical_locator(snapshot.get("package_locator")):
        issues.append({"kind": "PATH_BEARING_OR_MISSING_PACKAGE_LOCATOR", "field": "package_locator"})
    output = snapshot.get("output")
    if not isinstance(output, dict):
        output = {}
        issues.append({"kind": "OUTPUT_CONTRACT_MISSING", "field": "output"})
    if not _is_logical_locator(output.get("root_locator")):
        issues.append({"kind": "PATH_BEARING_OR_MISSING_OUTPUT_LOCATOR", "field": "output.root_locator"})
    for field, expected in (
        ("parent_state", "PREEXISTING_DECLARED"),
        ("existing_output_policy", "REFUSE_IF_EXISTS"),
        ("candidate_zip_policy", "CREATE_NEW_NO_OVERWRITE"),
        ("privacy_review", "REQUIRED"),
    ):
        if output.get(field) != expected:
            issues.append({"kind": "OUTPUT_TRANSACTION_OR_PRIVACY_CONTRACT_MISSING", "field": f"output.{field}"})
    admission = snapshot.get("admission")
    if not isinstance(admission, dict):
        admission = {}
        issues.append({"kind": "ADMISSION_CONTRACT_MISSING", "field": "admission"})
    for field, expected in (
        ("invalid_locus_row_policy", "REFUSE_INVALID"),
        ("source_schema_contract", "DECLARED_VERSIONED"),
        ("error_locator_policy", "LOGICAL_LOCATOR_ONLY"),
    ):
        if admission.get(field) != expected:
            issues.append({"kind": "ADMISSION_CONTRACT_MISSING", "field": f"admission.{field}"})
    reconciliation = snapshot.get("import_reconciliation")
    reconciliation_summary: dict[str, Any] = {"state": "WAITING_ON_DECLARATION"}
    if not isinstance(reconciliation, dict):
        issues.append({"kind": "IMPORT_RECONCILIATION_MISSING", "field": "import_reconciliation"})
    else:
        invalid_fields = [field for field in _IMPORT_RECONCILIATION_COUNTS if not _is_nonnegative_count(reconciliation.get(field))]
        if invalid_fields:
            for field in invalid_fields:
                issues.append({"kind": "IMPORT_RECONCILIATION_FIELD_INVALID", "field": f"import_reconciliation.{field}"})
        else:
            reconciliation_summary = {
                "state": "RECONCILED",
                **{field: reconciliation[field] for field in _IMPORT_RECONCILIATION_COUNTS},
            }
            if reconciliation["source_bgc_count"] != reconciliation["imported_record_count"]:
                issues.append({"kind": "SOURCE_TO_IMPORT_COUNT_MISMATCH", "field": "import_reconciliation.source_bgc_count"})
            if reconciliation["invalid_identity_row_count"] or reconciliation["skipped_invalid_identity_row_count"]:
                issues.append({"kind": "INVALID_IDENTITY_ROWS_OBSERVED", "field": "import_reconciliation.invalid_identity_row_count"})
            if reconciliation["duplicate_identity_row_count"] or reconciliation["incomplete_identity_row_count"]:
                issues.append({"kind": "DUPLICATE_OR_INCOMPLETE_IDENTITY_ROWS_OBSERVED", "field": "import_reconciliation.duplicate_identity_row_count"})
            if any(item["kind"] in {
                "SOURCE_TO_IMPORT_COUNT_MISMATCH",
                "INVALID_IDENTITY_ROWS_OBSERVED",
                "DUPLICATE_OR_INCOMPLETE_IDENTITY_ROWS_OBSERVED",
            } for item in issues):
                reconciliation_summary["state"] = "REFUSE_UNRECONCILED"
    phylogenomics = snapshot.get("phylogenomics", {"requested": False})
    if not isinstance(phylogenomics, dict):
        phylogenomics = {}
        issues.append({"kind": "PHYLOGENOMICS_CONTRACT_INVALID", "field": "phylogenomics"})
    if phylogenomics.get("requested") is True:
        for field in _PHYLOGENOMICS_BINDINGS:
            if not str(phylogenomics.get(field, "")).strip():
                issues.append({"kind": "PHYLOGENOMICS_BINDING_MISSING", "field": f"phylogenomics.{field}"})
    decision = "CURRENT_WORKFLOW_OWNER_COMPATIBLE" if not issues else "WAITING_ON_COMPATIBILITY_BINDING"
    return {
        "schema_version": "mamey_package_continuity_widget_v1",
        "widget_id": "W402-14",
        "status": "RUNNABLE_CANDIDATE",
        "audience": "maintainer evaluating a historical Sapote Engine candidate",
        "decision": "whether a historical Sapote Engine concept can enter the current workflow as a compatibility bridge",
        "input_schema": {
            "snapshot_path": "object-valued sapote_engine_continuity_bridge_v1 JSON",
            "expected_bundle_version": "current comparator bundle version",
            "expected_source_inventory_sha256": "current comparator inventory SHA-256",
            "import_reconciliation": "declared non-negative source/import/identity-row counts; source_bgc_count must equal imported_record_count and all identity issue counts must be zero",
        },
        "existing_owner": "mamey.sapote_workflow; this bridge never replaces its ordered gate driver",
        "compatibility_decision": decision,
        "compatibility_holds": issues,
        "import_reconciliation": reconciliation_summary,
        "phylogenomics_state": "NOT_REQUESTED" if phylogenomics.get("requested") is not True else ("BOUND" if not any(x["kind"] == "PHYLOGENOMICS_BINDING_MISSING" for x in issues) else "WAITING_ON_BINDING"),
        "privacy_portability": "Accepts and emits logical locators and hashes only; absolute paths, candidate evidence values, and candidate ZIP contents are excluded.",
        "constraint": "Historical-engine concepts are evaluated as current-owner compatibility only; no legacy package rebase, candidate ZIP creation, evidence admission, interpretation, or promotion occurs.",
    }


def explain_validation_refusal(package_dir: str | Path) -> dict[str, Any]:
    """W402-15: expose failing or unavailable validation gates without bypass advice."""
    package = Path(package_dir)
    gate, error = _read_object(package / "gate_validation.json")
    if error:
        return _package_hold("W402-15", "why validation cannot currently authorize the next extraction-stage action", f"GATE_{error}")
    terminal = str(gate.get("status", "UNKNOWN"))
    reasons: list[dict[str, str]] = []
    # validate_package owns depth-floor completeness through gold_completeness plus
    # depth_floor_breakdown; it has never emitted a separate depth_floor gate.
    for field in ("file_presence", "rggmci_gate", "gold_completeness"):
        if field not in gate:
            reasons.append({"kind": "GATE_FIELD_ABSENT", "field": field, "owner": "mamey.validate.validate_package"})
            continue
        value = str(gate[field]).upper()
        if value not in {"PASS", "MAMEY_COMPLETE", "NOT_APPLICABLE", "SKIPPED"}:
            reasons.append({"kind": "GATE_NOT_CLEAR", "field": field, "owner": "mamey.validate.validate_package"})
    decision = "NO_REFUSAL_OBSERVED" if terminal in {"PASS", "MAMEY_COMPLETE"} and not reasons else "REFUSE_PROMOTION"
    return {
        "schema_version": "mamey_package_continuity_widget_v1",
        "widget_id": "W402-15",
        "status": "RUNNABLE_CANDIDATE",
        "audience": "operator reading a validation result",
        "decision": "why validation cannot currently authorize the next extraction-stage action",
        "input_schema": {"package_dir": "directory containing object-valued gate_validation.json"},
        "existing_owner": "mamey.validate.validate_package",
        "validation_status": terminal,
        "promotion_decision": decision,
        "refusal_reasons": reasons,
        "safe_next_action": "Run the named owner after correcting its source condition; do not modify a sealed receipt to clear a gate.",
        "privacy_portability": "Returns field names and gate states only; does not copy package contents.",
    }


def preflight_handoff(package_dir: str | Path, input_zip: str | Path | None = None) -> dict[str, Any]:
    """W402-16: choose a package-only or region-support handoff before archive creation."""
    package = Path(package_dir)
    if not package.is_dir():
        return _package_hold("W402-16", "which supported handoff shape is available", "PACKAGE_DIRECTORY_ABSENT")
    manifest, manifest_error = _read_object(package / "manifest.json")
    if manifest_error:
        return _package_hold("W402-16", "which supported handoff shape is available", f"MANIFEST_{manifest_error}")
    checksums = package / "checksums_sha256.txt"
    crosswalk_present = any(package.glob("*_2b_bgc_crosswalk.csv"))
    zip_state = "NOT_REQUESTED"
    if input_zip is not None:
        zip_state = "PRESENT" if Path(input_zip).is_file() else "ABSENT"
    handoff_shape = "REGION_GBK_SUPPORT_CANDIDATE" if zip_state == "PRESENT" and crosswalk_present else "PACKAGE_ONLY"
    missing = []
    if not checksums.is_file():
        missing.append("checksums_sha256.txt")
    if handoff_shape == "REGION_GBK_SUPPORT_CANDIDATE" and not crosswalk_present:
        missing.append("*_2b_bgc_crosswalk.csv")
    return {
        "schema_version": "mamey_package_continuity_widget_v1",
        "widget_id": "W402-16",
        "status": "RUNNABLE_CANDIDATE",
        "audience": "operator preparing an internal portable handoff",
        "decision": "which supported handoff shape is available",
        "input_schema": {"package_dir": "sealed package directory", "input_zip": "optional antiSMASH ZIP path"},
        "existing_owner": "mamey.handoff.build_handoff",
        "handoff_shape": handoff_shape,
        "artifact_states": {"manifest.json": "PRESENT", "checksums_sha256.txt": "PRESENT" if checksums.is_file() else "ABSENT", "crosswalk": "PRESENT" if crosswalk_present else "ABSENT", "input_zip": zip_state},
        "missingness": {"kind": "NONE" if not missing else "HANDOFF_PREREQUISITE_ABSENT", "artifacts": missing},
        "constraint": "This preflight does not create an archive and does not authorize external or public sharing.",
        "privacy_portability": "Only relative artifact names and states are emitted.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only Mamey package continuity widgets")
    parser.add_argument("widget", choices=("continuity", "engine", "refusal", "handoff", "fingerprint"))
    parser.add_argument("package_dir", nargs="?")
    parser.add_argument("--input-zip")
    parser.add_argument("--prior-package")
    parser.add_argument("--snapshot")
    parser.add_argument("--expected-bundle-version")
    parser.add_argument("--expected-source-inventory-sha256")
    args = parser.parse_args(argv)
    if args.widget == "engine":
        result = assess_sapote_engine_compatibility(args.snapshot or "", args.expected_bundle_version or "", args.expected_source_inventory_sha256 or "")
    elif args.widget == "handoff":
        result = preflight_handoff(args.package_dir or "", args.input_zip)
    elif args.widget == "fingerprint":
        result = compare_package_fingerprints(args.prior_package or "", args.package_dir or "")
    else:
        result = {"continuity": assess_continuity, "refusal": explain_validation_refusal}[args.widget](args.package_dir or "")
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0 if result["status"] == "RUNNABLE_CANDIDATE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
