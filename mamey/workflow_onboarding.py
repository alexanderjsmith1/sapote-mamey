"""Read-only onboarding decision widgets for portable Mamey bundles.

W402-11 routes an operator's stated goal to an existing command without
inventing an input state.  W402-12 states the boundary between extraction,
post-seal add-ons, Sapote judgment, and release.  W402-13 resolves the smallest
document read-set present in the current bundle.  These widgets do not run an
analysis, write a package, or authorize a release.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


_ROUTES: dict[str, dict[str, str]] = {
    "start": {
        "audience": "new operator with an antiSMASH output ZIP",
        "decision": "whether the supplied file is an intake-ready antiSMASH ZIP",
        "owner": "mamey.package_inspector.inspect_command",
        "command": "mamey inspect <antiSMASH-output.zip>",
        "next_if_ready": "mamey run --strain <id> --input-zip <zip> --taxonomy <taxonomy> --source <source> --mode gold",
    },
    "understand": {
        "audience": "operator orienting in an existing workspace",
        "decision": "which existing package or capability to inspect first",
        "owner": "mamey.discover.discover_command and mamey.cli.capabilities_command",
        "command": "mamey discover <root> --json",
        "next_if_ready": "mamey capabilities <plain-language-keywords>",
    },
    "validate": {
        "audience": "operator with a completed package directory",
        "decision": "whether the package passes its deterministic extraction gates",
        "owner": "mamey.validate.validate_package",
        "command": "mamey validate <package-dir>",
        "next_if_ready": "read gate_validation.json; do not promote a non-PASS result",
    },
    "continue": {
        "audience": "operator resuming a sealed-package review",
        "decision": "what package state and Sapote work remain",
        "owner": "mamey.session_resume.build_resume and mamey.sapote_workflow.workflow_command",
        "command": "mamey resume <package-dir> --json",
        "next_if_ready": "mamey workflow --package <package-dir> --json",
    },
    "share": {
        "audience": "operator preparing a portable internal handoff",
        "decision": "whether a package-only or region-GBK handoff is needed",
        "owner": "mamey.handoff.build_handoff",
        "command": "mamey handoff --package <package-dir> --out <handoff.zip>",
        "next_if_ready": "use the handoff preflight before creating an archive",
    },
}

_BOUNDARIES: dict[str, dict[str, str]] = {
    "extract": {
        "decision": "Does a changed input require a new deterministic extraction?",
        "owner": "mamey.cli.run_one_strain",
        "boundary": "RERUN_REQUIRED",
        "reason": "Raw antiSMASH input, strain metadata, or extraction mode changes are core inputs.",
    },
    "postseal": {
        "decision": "Can this non-scoring report be added after a sealed extraction?",
        "owner": "post-seal mamey subcommands",
        "boundary": "ADDITIVE_ONLY",
        "reason": "A post-seal report may consume an existing package but must not rewrite score-bearing outputs.",
    },
    "judgment": {
        "decision": "Can extraction output be interpreted as a scientific conclusion here?",
        "owner": "Sapote Tier 2 or Tier 3 protocols",
        "boundary": "JUDGMENT_DEFERRED",
        "reason": "Mamey extracts deterministically; scientific judgment is not an extraction widget action.",
    },
    "release": {
        "decision": "May this package be exported publicly?",
        "owner": "release policy plus public-tier audit owners",
        "boundary": "OWNER_AUTHORIZATION_REQUIRED",
        "reason": "A candidate or passing local report does not authorize release, export, or public disclosure.",
    },
}

_READSETS: dict[str, tuple[str, ...]] = {
    "start": ("README.md", "docs/START_HERE.md", "docs/SINGLE_STRAIN_QUICKSTART.md"),
    "understand": ("CURRENT_DOCS_INDEX.md", "docs/FILE_ATLAS.md", "docs/TOOLS_INVENTORY.generated.md"),
    "validate": ("docs/DELIVERABLE_CONTRACT.md", "docs/PER_MODE_ARTIFACT_SET.md", "docs/TROUBLESHOOTING.md"),
    "continue": ("docs/SAPOTE_WORKFLOW_CONTRACT.md", "docs/MODE_B_DOCUMENT_INDEX.md", "docs/PORTABLE_EVIDENCE_WORKSPACE.md"),
    "share": ("docs/PORTABLE_STRAIN_PRIVACY_AND_EVIDENCE.md", "docs/PUBLIC_RELEASE_GUIDE.md", "docs/DELIVERABLE_CONTRACT.md"),
}


def _held(widget_id: str, audience: str, decision: str, reason: str) -> dict[str, Any]:
    return {
        "schema_version": "mamey_workflow_widget_v1",
        "widget_id": widget_id,
        "status": "HELD_WITH_EXACT_REASON",
        "audience": audience,
        "decision": decision,
        "missingness": {"kind": "REQUIRED_INPUT_MISSING", "detail": reason},
        "privacy_portability": "Read-only; no paths or input contents are copied into the result.",
    }


def route_operator_intent(intent: str | None, input_shape: str | None) -> dict[str, Any]:
    """W402-11: return a read-only next-command route or a typed input hold."""
    if not intent or intent.strip().lower() not in _ROUTES:
        return _held("W402-11", "new or returning operator", "which command should run next", "intent must be one of: " + ", ".join(sorted(_ROUTES)))
    if not input_shape or input_shape.strip().upper() not in {"RAW_ANTISMASH_ZIP", "PACKAGE_DIR", "WORKSPACE_ROOT"}:
        return _held("W402-11", _ROUTES[intent.strip().lower()]["audience"], _ROUTES[intent.strip().lower()]["decision"], "input_shape must be RAW_ANTISMASH_ZIP, PACKAGE_DIR, or WORKSPACE_ROOT")
    key = intent.strip().lower()
    route = _ROUTES[key]
    return {
        "schema_version": "mamey_workflow_widget_v1",
        "widget_id": "W402-11",
        "status": "RUNNABLE_CANDIDATE",
        "audience": route["audience"],
        "decision": route["decision"],
        "input_schema": {"intent": sorted(_ROUTES), "input_shape": ["RAW_ANTISMASH_ZIP", "PACKAGE_DIR", "WORKSPACE_ROOT"]},
        "input_shape": input_shape.strip().upper(),
        "existing_owner": route["owner"],
        "next_command": route["command"],
        "next_if_ready": route["next_if_ready"],
        "privacy_portability": "Commands use caller-provided paths only; no path is persisted or exported.",
    }


def classify_work_boundary(change_class: str | None) -> dict[str, Any]:
    """W402-12: declare the authority boundary for a requested work class."""
    if not change_class or change_class.strip().lower() not in _BOUNDARIES:
        return _held("W402-12", "operator planning a follow-on action", "whether a change is extraction, additive, judgment, or release work", "change_class must be one of: " + ", ".join(sorted(_BOUNDARIES)))
    item = _BOUNDARIES[change_class.strip().lower()]
    return {
        "schema_version": "mamey_workflow_widget_v1",
        "widget_id": "W402-12",
        "status": "RUNNABLE_CANDIDATE",
        "audience": "operator planning a follow-on action",
        "decision": item["decision"],
        "input_schema": {"change_class": sorted(_BOUNDARIES)},
        "existing_owner": item["owner"],
        "boundary": item["boundary"],
        "reason": item["reason"],
        "privacy_portability": "No package or evidence data are read or written.",
    }


def build_onboarding_readset(bundle_root: str | Path, intent: str | None) -> dict[str, Any]:
    """W402-13: resolve a small, present/absent documentation read-set honestly."""
    if not intent or intent.strip().lower() not in _READSETS:
        return _held("W402-13", "operator seeking documentation", "which portable documents to open first", "intent must be one of: " + ", ".join(sorted(_READSETS)))
    root = Path(bundle_root)
    if not root.is_dir():
        return _held("W402-13", "operator seeking documentation", "which portable documents to open first", "bundle_root is not a readable directory")
    key = intent.strip().lower()
    entries = []
    for locator in _READSETS[key]:
        path = root / locator
        entries.append({"logical_locator": locator, "state": "PRESENT" if path.is_file() else "ABSENT"})
    return {
        "schema_version": "mamey_workflow_widget_v1",
        "widget_id": "W402-13",
        "status": "RUNNABLE_CANDIDATE" if all(e["state"] == "PRESENT" for e in entries) else "HELD_WITH_EXACT_REASON",
        "audience": "operator seeking documentation",
        "decision": "which portable documents to open first",
        "input_schema": {"bundle_root": "readable directory", "intent": sorted(_READSETS)},
        "existing_owner": "bundle documentation owners; this widget does not generate documentation",
        "readset": entries,
        "missingness": {"kind": "DOCUMENT_ABSENT", "count": sum(e["state"] == "ABSENT" for e in entries)},
        "privacy_portability": "Only logical bundle-relative locators are returned; absolute paths are omitted.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only Mamey onboarding decision widgets")
    parser.add_argument("widget", choices=("route", "boundary", "readset"))
    parser.add_argument("--intent")
    parser.add_argument("--input-shape")
    parser.add_argument("--change-class")
    parser.add_argument("--bundle-root", default=".")
    args = parser.parse_args(argv)
    if args.widget == "route":
        result = route_operator_intent(args.intent, args.input_shape)
    elif args.widget == "boundary":
        result = classify_work_boundary(args.change_class)
    else:
        result = build_onboarding_readset(args.bundle_root, args.intent)
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0 if result["status"] == "RUNNABLE_CANDIDATE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
