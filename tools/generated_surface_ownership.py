#!/usr/bin/env python3
"""generated_surface_ownership.py — fail-closed, check-only cut-surface planner.

The project has several generated release surfaces, but their owners are intentionally
different.  This utility records the phase boundary without taking ownership away from
the existing writers.  It never runs a generator, edits a tree, or claims to prove a
historical generation time from a checkout.

An operator must explicitly declare both the already-final generated inputs and the
outputs being declared final for one phase.  A wrong declaration is a typed non-zero
refusal.  This prevents a source-stage tree from treating the per-tier TIER_MANIFEST
or SOURCE_CHECKSUMS as source-final inputs/outputs.

Examples:
  python tools/generated_surface_ownership.py --phase source-generated \
      --assert-input none --assert-final module_manifest,tools_inventory
  python tools/generated_surface_ownership.py --phase source-final \
      --assert-input module_manifest,tools_inventory \
      --assert-final module_manifest,tools_inventory,version_build,release_manifest
  python tools/generated_surface_ownership.py --phase tier-final \
      --assert-input module_manifest,tools_inventory,version_build,release_manifest \
      --assert-final tier_manifest,source_checksums
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parent.parent


SURFACES = {
    "module_manifest": {
        "outputs": ("MODULE_MANIFEST.txt",),
        "owner": "tools/check_module_accretion.py --write",
        "owner_paths": ("tools/check_module_accretion.py",),
        "trigger": "mamey/**/*.py membership changes",
        "validator": "tools/check_module_accretion.py --json",
    },
    "tools_inventory": {
        "outputs": ("docs/TOOLS_INVENTORY.generated.md", "docs/BUNDLE_CAPABILITIES.md"),
        "owner": "tools/gen_tools_inventory.py",
        "owner_paths": ("tools/gen_tools_inventory.py",),
        "trigger": "tools/*.py or tools/*.sh membership, or rendered first-line summary changes",
        "validator": "tools/gen_tools_inventory.py --check",
    },
    "version_build": {
        "outputs": ("BUILD_STAMP.txt", "TAG", "CITATION.cff"),
        "owner": "cut owner sets BUILD_STAMP anchors; tools/sync_version.py owns derived restatements and bootstrap rendering",
        "owner_paths": ("tools/sync_version.py", "tools/render_bootstrap_contract.py"),
        "trigger": "authorized bundle/engine/build decision after implementation QA",
        "validator": "tools/sync_version.py --check; tools/render_bootstrap_contract.py --check",
    },
    "release_manifest": {
        "outputs": ("RELEASE_MANIFEST.md",),
        "owner": "tools/gen_release_manifest.py --apply --pytest-log <final-green-log>",
        "owner_paths": ("tools/gen_release_manifest.py",),
        "trigger": "final source QA produces a green final pytest log",
        "validator": "tools/gen_release_manifest.py --check",
    },
    "tier_manifest": {
        "outputs": ("TIER_MANIFEST.txt",),
        "owner": "tools/make_public_tier.sh via tools/tracked_file_policy.py --emit-manifest",
        "owner_paths": ("tools/make_public_tier.sh", "tools/tracked_file_policy.py"),
        "trigger": "per-tier staging is complete and the tier/version/stamp are bound",
        "validator": "tools/check_release_manifest.py --root <final-stage>",
    },
    "source_checksums": {
        "outputs": ("SOURCE_CHECKSUMS_SHA256.txt",),
        "owner": "tools/make_public_tier.sh final staged-tree checksum step",
        "owner_paths": ("tools/make_public_tier.sh", "tools/check_release_manifest.py"),
        "trigger": "after all per-tier stripping, redaction, generated membership, and staged BUILD_STAMP edits",
        "validator": "tools/check_release_manifest.py --root <final-stage>",
    },
}


PHASES = {
    "source-generated": {
        "inputs": (),
        "final_outputs": ("module_manifest", "tools_inventory"),
        "description": "Regenerate only source inventories whose declared triggers fired.",
    },
    "source-final": {
        "inputs": ("module_manifest", "tools_inventory"),
        "final_outputs": ("module_manifest", "tools_inventory", "version_build", "release_manifest"),
        "description": "Freeze final source surfaces; per-tier membership and checksums remain deferred.",
    },
    "tier-final": {
        "inputs": ("module_manifest", "tools_inventory", "version_build", "release_manifest"),
        "final_outputs": ("tier_manifest", "source_checksums"),
        "description": "Finalize one staged tier; SOURCE_CHECKSUMS is last after TIER_MANIFEST and staged edits.",
    },
}


def _parse_surface_list(value: str) -> tuple[str, ...]:
    raw = value.strip()
    if raw.lower() == "none":
        return ()
    names = tuple(part.strip() for part in raw.split(",") if part.strip())
    unknown = sorted(set(names) - set(SURFACES))
    if unknown:
        raise ValueError(f"unknown surface identifier(s): {', '.join(unknown)}")
    if len(set(names)) != len(names):
        raise ValueError("surface identifiers must not be repeated")
    return names


def _surface_payload(name: str) -> dict:
    surface = SURFACES[name]
    return {
        "id": name,
        "outputs": list(surface["outputs"]),
        "owner": surface["owner"],
        "trigger": surface["trigger"],
        "validator": surface["validator"],
    }


def evaluate(root: pathlib.Path, phase: str, declared_inputs: tuple[str, ...],
             declared_finals: tuple[str, ...]) -> dict:
    contract = PHASES[phase]
    expected_inputs = tuple(contract["inputs"])
    expected_finals = tuple(contract["final_outputs"])
    all_final = tuple(SURFACES)
    deferred = tuple(name for name in all_final if name not in expected_finals)
    findings = []

    if set(declared_inputs) != set(expected_inputs):
        findings.append({
            "code": "DECLARED_INPUT_SET_MISMATCH",
            "expected": list(expected_inputs),
            "declared": list(declared_inputs),
        })
    if set(declared_finals) != set(expected_finals):
        findings.append({
            "code": "DECLARED_FINAL_SET_MISMATCH",
            "expected": list(expected_finals),
            "declared": list(declared_finals),
        })

    required = set(expected_inputs) | set(expected_finals)
    for name in sorted(required):
        surface = SURFACES[name]
        for relpath in (*surface["owner_paths"], *surface["outputs"]):
            if not (root / relpath).is_file():
                findings.append({
                    "code": "MISSING_OWNER_OR_SURFACE_PATH",
                    "surface": name,
                    "path": relpath,
                })

    return {
        "tool": "generated_surface_ownership",
        "mode": "check-only",
        "root": str(root),
        "phase": phase,
        "phase_description": contract["description"],
        "declared_inputs": list(declared_inputs),
        "declared_final_outputs": list(declared_finals),
        "expected_inputs": list(expected_inputs),
        "expected_final_outputs": list(expected_finals),
        "deferred_outputs": list(deferred),
        "surface_owners": [_surface_payload(name) for name in all_final],
        "limitations": [
            "This check validates an explicit ownership-phase declaration; it cannot infer historical write order from tree timestamps.",
            "This check never regenerates, rewrites, signs, cuts, archives, or publishes a surface.",
        ],
        "findings": findings,
        "status": "PASS" if not findings else "REFUSED",
    }


def _print_human(payload: dict) -> None:
    print(f"generated_surface_ownership: {payload['status']} phase={payload['phase']}", '  expected inputs: ' + (', '.join(payload['expected_inputs']) or 'none'), '  expected final outputs: ' + ', '.join(payload['expected_final_outputs']), '  deferred outputs: ' + ', '.join(payload['deferred_outputs']), sep="\n")
    for finding in payload["findings"]:
        print("  " + finding["code"] + ": " + json.dumps(finding, sort_keys=True))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Check an explicit generated-surface ownership declaration.")
    parser.add_argument("--root", default=ROOT, type=pathlib.Path, help="project root (read-only; default: tool root)")
    parser.add_argument("--phase", choices=tuple(PHASES), required=True)
    parser.add_argument("--assert-input", required=True, help="comma-separated prior final surfaces, or none")
    parser.add_argument("--assert-final", required=True, help="comma-separated final surfaces for this phase")
    parser.add_argument("--json", action="store_true", help="emit machine-readable result")
    args = parser.parse_args(argv)

    try:
        declared_inputs = _parse_surface_list(args.assert_input)
        declared_finals = _parse_surface_list(args.assert_final)
    except ValueError as exc:
        payload = {"tool": "generated_surface_ownership", "status": "REFUSED", "findings": [{"code": "INVALID_DECLARATION", "message": str(exc)}]}
        print(json.dumps(payload, indent=2, sort_keys=True) if args.json else f"generated_surface_ownership: REFUSED {exc}")
        return 2

    root = args.root.resolve()
    if not root.is_dir():
        payload = {"tool": "generated_surface_ownership", "status": "REFUSED", "findings": [{"code": "ROOT_NOT_DIRECTORY", "path": str(root)}]}
        print(json.dumps(payload, indent=2, sort_keys=True) if args.json else f"generated_surface_ownership: REFUSED root is not a directory: {root}")
        return 2

    payload = evaluate(root, args.phase, declared_inputs, declared_finals)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        _print_human(payload)
    return 0 if payload["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
