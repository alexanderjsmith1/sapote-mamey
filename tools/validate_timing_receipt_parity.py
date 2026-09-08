#!/usr/bin/env python3
"""validate_timing_receipt_parity.py — compare timing phases to run_phase_receipts.jsonl.

ChatGPT-safe runs must remain auditable when the terminal output stalls or a tool
session times out. This validator checks that receipt telemetry tells the same
story as the timing breakdown: long/quiet phases that START should have a closure
receipt (END / ERROR / TIMEOUT / SKIP), and COMPLETE timing phases should not be
inferred from a lonely START for the key ChatGPT phases.

Usage:
  python tools/validate_timing_receipt_parity.py <package_dir> [--json]

Exit 0 = PASS, 1 = FAIL. Warnings are reported but do not fail unless --strict.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import csv
import json
from pathlib import Path
from collections import defaultdict

TERMINAL_STATUSES = {"END", "ERROR", "TIMEOUT", "SKIP", "SKIPPED"}
DEFAULT_REQUIRED_CLOSURE = {
    "environment",
    "antismash_parse",
    "inventory",
    "source_scans",
    "gene_context",
    "rggmci",
    "package_addons",
    "citation_compact",
}


def _load_receipts(package_dir: Path) -> list[dict]:
    p = package_dir / "run_phase_receipts.jsonl"
    if not p.exists():
        return []
    rows = []
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            rows.append({"_parse_error": line[:120]})
            continue
        rows.append(row)
    return rows


def _find_timing_json(package_dir: Path) -> Path | None:
    cands = sorted(package_dir.glob("*_timing_breakdown.json"))
    return cands[0] if cands else None


def _load_timing_phases(package_dir: Path) -> list[dict]:
    p = _find_timing_json(package_dir)
    if p and p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return list(data.get("phases") or [])
        except Exception:
            return []
    cands = sorted(package_dir.glob("*_timing_breakdown.csv"))
    if cands:
        try:
            return list(csv.DictReader(cands[0].open(newline="", encoding="utf-8")))
        except Exception:
            return []
    return []


def audit(package_dir: str | Path, *, strict: bool = False,
          required_closure: set[str] | None = None) -> dict:
    package_dir = Path(package_dir)
    required = set(required_closure or DEFAULT_REQUIRED_CLOSURE)
    receipts = _load_receipts(package_dir)
    phases = _load_timing_phases(package_dir)
    errors: list[dict] = []
    warnings: list[dict] = []

    if not receipts:
        errors.append({"kind": "missing_receipts", "detail": "run_phase_receipts.jsonl absent or empty"})
        receipts = []
    if not phases:
        warnings.append({"kind": "missing_timing", "detail": "timing breakdown absent or empty"})

    by_phase: dict[str, list[dict]] = defaultdict(list)
    parse_errors = 0
    for row in receipts:
        if row.get("_parse_error"):
            parse_errors += 1
            continue
        phase = str(row.get("phase") or "")
        if phase:
            by_phase[phase].append(row)
    if parse_errors:
        errors.append({"kind": "receipt_parse_errors", "count": parse_errors})

    for phase, rows in sorted(by_phase.items()):
        statuses = {str(r.get("status") or "").upper() for r in rows}
        started = "START" in statuses
        closed = bool(statuses & TERMINAL_STATUSES)
        if started and not closed:
            item = {"kind": "started_without_terminal_receipt", "phase": phase,
                    "statuses": sorted(statuses)}
            if phase in required:
                errors.append(item)
            else:
                warnings.append(item)

    receipt_phase_set = set(by_phase)
    for p in phases:
        name = str(p.get("name") or p.get("phase") or "")
        status = str(p.get("status") or "").upper()
        if not name:
            continue
        if name not in receipt_phase_set:
            warnings.append({"kind": "timing_phase_without_receipt", "phase": name,
                             "timing_status": status})
            continue
        if status == "COMPLETE" and name in required:
            statuses = {str(r.get("status") or "").upper() for r in by_phase[name]}
            if "START" in statuses and not (statuses & TERMINAL_STATUSES):
                errors.append({"kind": "complete_timing_phase_missing_terminal_receipt",
                               "phase": name, "receipt_statuses": sorted(statuses)})

    if strict:
        errors.extend(warnings)
        warnings = []

    return {
        "status": "PASS" if not errors else "FAIL",
        "package_dir": str(package_dir),
        "receipt_count": len(receipts),
        "receipt_phase_count": len(receipt_phase_set),
        "timing_phase_count": len(phases),
        "required_closure_phases": sorted(required),
        "errors": errors,
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("package_dir")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="treat warnings as failures")
    ns = ap.parse_args(argv)
    result = audit(ns.package_dir, strict=ns.strict)
    if ns.json:
        emit(json.dumps(result, indent=2))
    else:
        emit(f"TIMING_RECEIPT_PARITY: {result['status']}", f"  receipts: {result['receipt_count']} rows / {result['receipt_phase_count']} phases", f"  timing:   {result['timing_phase_count']} phases", sep="\n")
        for e in result["errors"]:
            emit("  ERROR:", e)
        for w in result["warnings"]:
            emit("  WARN: ", w)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
