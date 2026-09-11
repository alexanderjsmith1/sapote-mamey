#!/usr/bin/env python3
"""Render a session-close checklist from a governed, portable durability root.

Render a formal end-of-session checklist: which Sapote–Mamey deliverables are AVAILABLE, which are DONE,
and which were not produced — plus a data-loss / persistence advisory (G2). Output is a plain-text
numbered checklist (the Developer or User's formatting preference) + a markdown copy.

  python tools/session_checklist.py --durable-root-config roots.json \
    --durable-root-id session_outputs --scan-relative current \
    --receipt-relative receipts/close_receipt.json

Status tokens:  [x] DONE (found)   [ ] NOT PRODUCED (available on request)   [~] PARTIAL
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse
import csv
import glob
import json
import os
from pathlib import Path
import sys
import sys as _sys, os as _os
_TOOL_DIR = Path(__file__).resolve().parent
_BUNDLE_ROOT = _TOOL_DIR.parent
_sys.path.insert(0, str(_TOOL_DIR))
_sys.path.insert(0, str(_BUNDLE_ROOT))
from _wbio import atomic_write_text
from mamey.deliverables_registry import load_registry  # v9.7.405 (CODEX_391 G4): the registry is the ONE menu
from mamey.evidence_roots import (
    EvidenceRootError,
    load_json,
    logical_locator,
    resolve_output,
    resolve_roots,
)

# (label, glob pattern relative to scan dir, stage) — OPERATIONAL run records, not scientific deliverables.
# v9.7.405 (CODEX_391 G4): the scientific deliverable menu now comes from mamey/data/deliverables_registry.json
# via mamey.deliverables_registry.load_registry(), so docs, CLI and this checklist cannot disagree.
OPERATIONAL_ARTIFACTS = [
    ("Strain extraction package(s)",        "**/*_Complete_Package.zip",         "3 extract"),
    ("Intake registry (strain ledger)",     "**/intake_registry.csv",            "2 intake"),
    ("Intake metrics (timings/RSS)",        "**/intake_metrics.csv",             "2 intake"),
    ("Batch run report(s)",                 "**/intake_batch*_report.md",        "2 intake"),
    ("ANALYSIS_FORWARD directive(s)",       "**/*_ANALYSIS_FORWARD.md",          "3→4 handoff"),
    ("Diagnostic Rescue 4B lead(s)",        "**/*_4B_Diagnostic_Rescue_Leads.*", "3 extract"),
    ("Full Mode B judgment write-up",       "**/*[Mm]ode*[Bb]*.md",              "4 judgment"),
    ("KCB sweep / lead board",              "**/*[Kk][Cc][Bb]*",                 "4 judgment"),
    ("Cohort / strain front page",          "**/*front_page*",                   "outward"),
    ("Chat export (md + PDF)",              "**/chat_export/*.pdf",              "records"),
    ("Patch audit / order list",            "**/PATCH_*",                        "records"),
    ("Merge handoff bundle",                "**/merge_handoff*",                 "handoff"),
    ("Re-cut tier zips (release)",          "**/sapote-mamey-v*.zip",            "release"),
]

def _count(scan, pattern):
    return len(glob.glob(os.path.join(scan, pattern), recursive=True))


def _parse_root_override(values: list[str]) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise EvidenceRootError("--durable-root values must be ROOT_ID=/absolute/path")
        root_id, path = value.split("=", 1)
        if not root_id or root_id in overrides:
            raise EvidenceRootError(f"Missing or duplicate durable root ID: {root_id!r}")
        overrides[root_id] = path
    return overrides


def _resolve_governed_scan(
    config_path: Path,
    root_id: str,
    relative_path: str,
    overrides: dict[str, str],
) -> tuple[Path, Path, dict]:
    roots = resolve_roots(
        load_json(config_path), config_path, cli_roots=overrides
    )
    if root_id not in roots:
        raise EvidenceRootError(f"Durable root is unbound: {root_id!r}")
    root = roots[root_id]
    if not root.is_dir():
        raise EvidenceRootError(f"Configured durable root is unavailable: {root_id!r}")
    scan = resolve_output(roots, root_id, relative_path)
    if not scan.is_dir():
        raise EvidenceRootError(
            f"Configured scan locator is unavailable: {logical_locator(root_id, relative_path)}"
        )
    locator = logical_locator(root_id, relative_path)
    return root, scan, {
        "schema_version": "sapote_session_durability_receipt_v1",
        "status": "PASS_GOVERNED_DURABLE_ROOT",
        "durable": True,
        "root_id": root_id,
        "scan_locator": locator,
        "copy_target_locator": logical_locator(root_id, "."),
        "host_paths_redacted": True,
        "authority_ceiling": "ENGINEERING_RUNTIME_RECEIPT_NOT_RELEASE_APPROVAL",
    }


def _count_patterns(scan, patterns):
    return len({
        path
        for pattern in patterns
        for path in glob.glob(os.path.join(scan, pattern), recursive=True)
    })


def _registered_deliverables():
    """Return the same menu records used by docs and the CLI."""
    registry = load_registry()
    return [
        (
            f"{item['label']} {item['name']}",
            tuple(item.get("detection_globs", [])),
            item["delivery_class"],
        )
        for item in registry["deliverables"]
    ]


def main(argv: list[str] | None = None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--durable-root-config", type=Path, required=True)
    ap.add_argument("--durable-root-id", required=True)
    ap.add_argument("--scan-relative", default=".")
    ap.add_argument("--durable-root", action="append", default=[])
    ap.add_argument("--registry", default=None)
    ap.add_argument("--out-relative", default=None, help="optional governed markdown output")
    ap.add_argument(
        "--receipt-relative", required=True,
        help="governed machine-readable, path-redacted JSON receipt",
    )
    a = ap.parse_args(argv)
    root, scan, receipt = _resolve_governed_scan(
        a.durable_root_config,
        a.durable_root_id,
        a.scan_relative,
        _parse_root_override(a.durable_root),
    )
    bound_root = {a.durable_root_id: root}
    receipt_path = resolve_output(bound_root, a.durable_root_id, a.receipt_relative)
    receipt["receipt_locator"] = logical_locator(a.durable_root_id, a.receipt_relative)
    out_path = None
    if a.out_relative:
        out_path = resolve_output(bound_root, a.durable_root_id, a.out_relative)
        if out_path == receipt_path:
            raise EvidenceRootError("Checklist and receipt locators must be distinct")
        receipt["checklist_locator"] = logical_locator(a.durable_root_id, a.out_relative)

    n_strains = None
    if a.registry and os.path.exists(a.registry):
        with open(a.registry, encoding="utf-8", newline="") as handle:
            n_strains = len(list(csv.DictReader(handle)))

    lines = []
    lines.append("SAPOTE–MAMEY — END-OF-SESSION CHECKLIST")
    if n_strains is not None:
        lines.append(f"Strains run this session (registry): {n_strains}")
    lines.append("")
    lines.append("Registered deliverables  [x]=matching artifact found  [ ]=not detected  [?]=not auto-detectable")
    lines.append("Artifact presence is not gate success, scientific acceptance, or release approval.")
    lines.append("")
    for i, (label, patterns, stage) in enumerate(_registered_deliverables(), 1):
        n = _count_patterns(scan, patterns) if patterns else 0
        box = "[x]" if n else ("[ ]" if patterns else "[?]")
        suffix = f" — {n} found" if n else ""
        lines.append(f"{i:2}. {box} {label}  ({stage}){suffix}")

    lines.append("")
    lines.append("Operational run records (not scientific deliverables)")
    for i, (label, pattern, stage) in enumerate(OPERATIONAL_ARTIFACTS, 1):
        n = _count(scan, pattern)
        box = "[x]" if n else "[ ]"
        suffix = f" — {n} found" if n else ""
        lines.append(f"O{i:02}. {box} {label}  ({stage}){suffix}")

    # G2 — data-loss / persistence advisory
    lines.append("")
    lines.append("PERSISTENCE & DATA-LOSS ADVISORY")
    lines.append(
        f"  • Scanned {receipt['scan_locator']} — GOVERNED DURABLE ROOT. "
        "Files are inside the configured persistence boundary."
    )
    lines.append(
        f"  • Keep retained outputs under {receipt['copy_target_locator']}; "
        "absolute host paths are intentionally redacted."
    )
    lines.append("  • Uploaded antiSMASH input ZIPs are not retained server-side between sessions.")
    lines.append("    Low stakes (re-uploadable), but re-running a strain needs its ZIP again — keep them.")
    lines.append("  • No accumulated master workbook unless a run used --master; otherwise per-strain only.")

    # judgment reminder
    lines.append("")
    lines.append("NEXT: if Mode B is unchecked above, judgment is still PENDING — trigger:")
    lines.append("  Run full Sapote analysis on <strain>   (see each package's ANALYSIS_FORWARD.md)")

    text = "\n".join(lines)
    emit(text)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(out_path, "# Sapote–Mamey — end-of-session checklist\n\n```\n" + text + "\n```\n")
        sys.stdout.write(str("\n(markdown written)") + "\n")
    receipt["deliverable_counts"] = {
        label: _count(scan, pattern) for label, pattern, _stage in OPERATIONAL_ARTIFACTS
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(receipt_path, json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    sys.stdout.write(str("(durability receipt written)") + "\n")


if __name__ == "__main__":
    main()
