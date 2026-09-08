#!/usr/bin/env python3
"""candidate_census.py — file-count and debris census for a candidate cut tree.

Counts total files under <dir>, plus four debris classes that must never ship in a sealed or
composed candidate tree: `.pyc` files, `__pycache__` directories, `.pytest_cache` directories,
and `.DS_Store` files. Read-only -- never deletes or mutates anything; it only counts and
reports. Exits non-zero when ANY debris class has a non-zero count, so it can gate a cut without
itself cleaning it (cleaning is a separate, explicit operator decision).

Usage:
    python3 tools/candidate_census.py <dir> [--baseline N] [--output PATH]

`--baseline N` compares the measured total_files count against an expected N and reports the
delta in the receipt; it is informational only and never affects the exit code -- only debris
gates this tool. A large unexplained baseline delta is a signal for a human to look, not
something this tool can judge on its own (a legitimate cut can add or remove many files).
"""
from __future__ import annotations

import argparse
import json
import os
import sys


ROOT_RUN_OUTPUTS = {"COHORT_MASTER.csv", "COHORT_PRIORITY_LEADS.csv"}


def census(root: str) -> dict:
    """Walk `root` once and return the census dict. Read-only: no file is opened, only
    `os.walk`'s own directory-entry metadata is inspected. Traversal errors are retained in
    the receipt so an unreadable subtree can never be mistaken for a complete clean census."""
    total_files = 0
    pyc_files = 0
    pycache_dirs = 0
    pytest_cache_dirs = 0
    ds_store_files = 0
    root_run_outputs = 0
    traversal_errors = []

    def _record_walk_error(exc: OSError) -> None:
        failed_path = getattr(exc, "filename", None) or root
        traversal_errors.append({
            "path": os.path.abspath(os.fspath(failed_path)),
            "error_type": type(exc).__name__,
            "message": str(exc),
        })

    for _dirpath, dirnames, filenames in os.walk(root, onerror=_record_walk_error):
        for d in dirnames:
            if d == "__pycache__":
                pycache_dirs += 1
            elif d == ".pytest_cache":
                pytest_cache_dirs += 1
        for fn in filenames:
            total_files += 1
            if fn.endswith(".pyc"):
                pyc_files += 1
            elif fn == ".DS_Store":
                ds_store_files += 1
            elif fn in ROOT_RUN_OUTPUTS and os.path.abspath(_dirpath) == os.path.abspath(root):
                # v9.7.408: cohort-assemble / cohort-leads default `--out` to a bare filename, so a run
                # from the bundle root writes analysis products INTO the engine tree. Two empty ones
                # shipped inside both sealed .407 zips. Root-only: the same names deeper down are
                # legitimate fixtures/outputs.
                root_run_outputs += 1
    debris = {
        "pyc_files": pyc_files,
        "pycache_dirs": pycache_dirs,
        "pytest_cache_dirs": pytest_cache_dirs,
        "ds_store_files": ds_store_files,
        "root_run_outputs": root_run_outputs,
    }
    debris_total = sum(debris.values())
    coverage_complete = not traversal_errors
    if not coverage_complete:
        status = "INCOMPLETE"
    elif debris_total:
        status = "DEBRIS_FOUND"
    else:
        status = "CLEAN"
    return {
        "schema_version": "sapote-candidate-census-1.0",
        "root": os.path.abspath(root),
        "total_files": total_files,
        "debris": debris,
        "debris_total": debris_total,
        "coverage_complete": coverage_complete,
        "traversal_errors": traversal_errors,
        "status": status,
    }


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="File-count and debris census for a candidate cut tree")
    ap.add_argument("dir", help="root directory to census")
    ap.add_argument("--baseline", type=int, default=None,
                    help="expected total_files count; delta is reported but never gates exit status")
    ap.add_argument("--output", default=None, help="optional JSON receipt path")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not os.path.isdir(args.dir):
        sys.stderr.write(f"candidate_census: not a directory: {args.dir}\n")
        return 2
    report = census(args.dir)
    if args.baseline is not None:
        report["baseline"] = args.baseline
        report["baseline_delta"] = report["total_files"] - args.baseline
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        out_path = args.output
        out_dir = os.path.dirname(os.path.abspath(out_path))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(text)
    sys.stdout.write(text)
    return 0 if report["status"] == "CLEAN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
