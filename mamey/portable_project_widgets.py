"""Read-only provenance, recompute, privacy, and budget decision widgets.

W402-17 navigates package-level provenance fields without exposing their values.
W402-18 maps a stated change to its recomputation boundary. W402-19 refuses a
prospective public export unless the package explicitly says PUBLIC, while still
requiring the public-tier audit. W402-20 measures an on-disk read budget without
predicting runtime. The module uses only the standard library and never writes.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


_RECOMPUTE_RULES: dict[str, dict[str, Any]] = {
    "raw_input": {
        "boundary": "RERUN_REQUIRED",
        "affected": ["intake", "inventory", "source scans", "triage", "manifest", "checksums"],
        "owner": "mamey.cli.run_one_strain",
    },
    "run_metadata": {
        "boundary": "RERUN_REQUIRED",
        "affected": ["manifest context", "package outputs", "checksums"],
        "owner": "mamey.cli.run_one_strain",
    },
    "sealed_report": {
        "boundary": "ADDITIVE_POSTSEAL_ONLY",
        "affected": ["new report receipt only"],
        "owner": "the named post-seal report command",
    },
    "judgment_card": {
        "boundary": "SAPOTE_OWNER_REQUIRED",
        "affected": ["judgment deliverable only"],
        "owner": "Sapote Tier 2 or Tier 3 protocol",
    },
    "release_policy": {
        "boundary": "PUBLIC_TIER_AUDIT_AND_OWNER_AUTHORIZATION_REQUIRED",
        "affected": ["candidate public tier and release records"],
        "owner": "public-tier policy and audit owner",
    },
}


def _read_manifest(package: Path) -> tuple[dict[str, Any] | None, str | None]:
    path = package / "manifest.json"
    if not path.is_file():
        return None, "MANIFEST_ABSENT"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, "MANIFEST_UNREADABLE"
    return (data, None) if isinstance(data, dict) else (None, "MANIFEST_OBJECT_REQUIRED")


def _held(widget_id: str, decision: str, reason: str) -> dict[str, Any]:
    return {
        "schema_version": "mamey_portable_project_widget_v1",
        "widget_id": widget_id,
        "status": "HELD_WITH_EXACT_REASON",
        "audience": "operator reviewing a portable project package",
        "decision": decision,
        "missingness": {"kind": reason},
        "privacy_portability": "Read-only; absolute paths and evidence values are intentionally omitted.",
    }


def build_provenance_navigation(package_dir: str | Path) -> dict[str, Any]:
    """W402-17: locate package-level provenance contracts without copying their values."""
    package = Path(package_dir)
    if not package.is_dir():
        return _held("W402-17", "where to inspect package-level input and source provenance", "PACKAGE_DIRECTORY_ABSENT")
    manifest, error = _read_manifest(package)
    if error:
        return _held("W402-17", "where to inspect package-level input and source provenance", error)
    fields = ("input_zip", "source_provenance", "source_provenance_note", "taxonomy", "source", "files")
    locations = [{"logical_locator": f"manifest.json#{field}", "state": "PRESENT" if field in manifest else "ABSENT"} for field in fields]
    locations.append({"logical_locator": "checksums_sha256.txt", "state": "PRESENT" if (package / "checksums_sha256.txt").is_file() else "ABSENT"})
    return {
        "schema_version": "mamey_portable_project_widget_v1",
        "widget_id": "W402-17",
        "status": "RUNNABLE_CANDIDATE",
        "audience": "operator needing a source/provenance audit trail",
        "decision": "where to inspect package-level input and source provenance",
        "input_schema": {"package_dir": "directory containing an object-valued manifest.json"},
        "existing_owner": "mamey.cell_provenance and mamey.source_provenance; this widget routes package-level reads only",
        "provenance_locations": locations,
        "missingness": {"kind": "NONE" if all(x["state"] == "PRESENT" for x in locations) else "PROVENANCE_LOCATOR_ABSENT"},
        "privacy_portability": "Logical locators only; field values, identifiers, and absolute paths are not emitted.",
    }


def plan_recompute_boundary(change_class: str | None) -> dict[str, Any]:
    """W402-18: give an explicit recompute boundary for one typed change class."""
    if not change_class or change_class.strip().lower() not in _RECOMPUTE_RULES:
        return _held("W402-18", "which artifacts must be recomputed after a change", "CHANGE_CLASS_REQUIRED: " + ", ".join(sorted(_RECOMPUTE_RULES)))
    rule = _RECOMPUTE_RULES[change_class.strip().lower()]
    return {
        "schema_version": "mamey_portable_project_widget_v1",
        "widget_id": "W402-18",
        "status": "RUNNABLE_CANDIDATE",
        "audience": "operator planning a correction or follow-on artifact",
        "decision": "which artifacts must be recomputed after a change",
        "input_schema": {"change_class": sorted(_RECOMPUTE_RULES)},
        "existing_owner": rule["owner"],
        "recompute_boundary": rule["boundary"],
        "affected_surface": rule["affected"],
        "constraint": "The plan does not perform recomputation and never treats a post-seal add-on as a replacement for extraction outputs.",
        "privacy_portability": "No project data are read or written.",
    }


def preview_export_readiness(package_dir: str | Path) -> dict[str, Any]:
    """W402-19: report a fail-closed prospective export decision, never authorize release."""
    package = Path(package_dir)
    if not package.is_dir():
        return _held("W402-19", "whether a package may enter the public-tier audit path", "PACKAGE_DIRECTORY_ABSENT")
    manifest, error = _read_manifest(package)
    if error:
        return _held("W402-19", "whether a package may enter the public-tier audit path", error)
    release = str(manifest.get("release", "UNSPECIFIED")).upper()
    if release != "PUBLIC":
        decision = "PUBLIC_EXPORT_REFUSED"
        reason = "Manifest release is not explicitly PUBLIC; no override is inferred."
    else:
        decision = "PUBLIC_TIER_AUDIT_REQUIRED"
        reason = "An explicit PUBLIC marker only allows audit preparation; it does not authorize release."
    return {
        "schema_version": "mamey_portable_project_widget_v1",
        "widget_id": "W402-19",
        "status": "RUNNABLE_CANDIDATE",
        "audience": "operator preparing a privacy-safe export review",
        "decision": "whether a package may enter the public-tier audit path",
        "input_schema": {"package_dir": "directory containing object-valued manifest.json with optional release"},
        "existing_owner": "tools/audit_public_cut.py and public-tier policy owner",
        "export_decision": decision,
        "reason": reason,
        "missingness": {"kind": "RELEASE_UNSPECIFIED" if release == "UNSPECIFIED" else "NONE"},
        "privacy_portability": "Does not produce, copy, redact, or export data; it refuses by default.",
    }


def estimate_read_budget(package_dir: str | Path, max_files: int = 10_000, max_bytes: int = 1_000_000_000) -> dict[str, Any]:
    """W402-20: count a local package read surface without estimating execution time."""
    package = Path(package_dir)
    if not package.is_dir():
        return _held("W402-20", "whether a package fits the declared bounded read budget", "PACKAGE_DIRECTORY_ABSENT")
    if max_files < 1 or max_bytes < 1:
        return _held("W402-20", "whether a package fits the declared bounded read budget", "POSITIVE_LIMIT_REQUIRED")
    files = sorted(path for path in package.rglob("*") if path.is_file())
    total_bytes = sum(path.stat().st_size for path in files)
    fits = len(files) <= max_files and total_bytes <= max_bytes
    return {
        "schema_version": "mamey_portable_project_widget_v1",
        "widget_id": "W402-20",
        "status": "RUNNABLE_CANDIDATE",
        "audience": "operator preparing a bounded offline review",
        "decision": "whether a package fits the declared bounded read budget",
        "input_schema": {"package_dir": "directory", "max_files": "positive integer", "max_bytes": "positive integer"},
        "existing_owner": "mamey.discover bounded discovery controls; this widget only measures one package surface",
        "file_count": len(files),
        "apparent_bytes": total_bytes,
        "limits": {"max_files": max_files, "max_bytes": max_bytes},
        "budget_decision": "WITHIN_DECLARED_BUDGET" if fits else "REQUIRES_BOUNDED_REVIEW_PLAN",
        "reproducibility_note": "Counts are deterministic for the observed directory contents; this is not a runtime or memory prediction.",
        "privacy_portability": "Only counts and byte totals are returned; filenames and content are omitted.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only Mamey portable-project decision widgets")
    parser.add_argument("widget", choices=("provenance", "recompute", "export", "budget"))
    parser.add_argument("--package-dir")
    parser.add_argument("--change-class")
    parser.add_argument("--max-files", type=int, default=10_000)
    parser.add_argument("--max-bytes", type=int, default=1_000_000_000)
    args = parser.parse_args(argv)
    if args.widget == "provenance":
        result = build_provenance_navigation(args.package_dir or "")
    elif args.widget == "recompute":
        result = plan_recompute_boundary(args.change_class)
    elif args.widget == "export":
        result = preview_export_readiness(args.package_dir or "")
    else:
        result = estimate_read_budget(args.package_dir or "", args.max_files, args.max_bytes)
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0 if result["status"] == "RUNNABLE_CANDIDATE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
