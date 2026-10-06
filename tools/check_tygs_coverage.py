#!/usr/bin/env python3
"""Check that every TYGS top-N type strain is either in an isolate's panel or logged as an issue.

Guards the failure fixed in neighbour_panel_candidates.py (2026-10-05): TYGS rows that the panel builder could not read or
resolve were dropped without a trace. For each strain this reads the TYGS digital-DDH tables directly (independently of the panel
builder's parser), takes the strain's top N type strains by d4 plus any rows tied with the N-th, and looks each one up in
<panels-dir>/<strain>/PANEL_TREE.tsv (column tygs_type_strain; several names may be joined by "; ") and in
<panels-dir>/<strain>/PANEL_ISSUES.tsv (any source starting with "TYGS"). Names are compared with all non-alphanumerics removed.

Usage:
  check_tygs_coverage.py --tygs <table.tsv> [...] --panels-dir PANELS --strains <strain:N> [...] --out TYGS_TOP_COVERAGE.tsv
Exit 0 when nothing is missing; 1 when any top-N row is neither in the panel nor logged; 2 on a usage error.
"""
from __future__ import annotations

import argparse
import csv
import html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _console import emit  # noqa: E402
try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ModuleNotFoundError:
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter


def _clean(cell: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", cell)).replace('"', " ")).strip()


def _key(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def read_tables(paths):
    """query strain -> set of (d4, subject text) from TYGS 'U vs. T' rows."""
    rows = {}
    for p in paths:
        with open(p, encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh, delimiter="\t"):
                if (r.get("comp_type") or "").strip() != "U vs. T":
                    continue
                q = re.sub(r"<[^>]+>|'|\"|\.fna|\.fasta|\s", "", r.get("query_genome", ""))
                try:
                    d4 = float(r.get("digital_ddh_d4", ""))
                except ValueError:
                    continue
                rows.setdefault(q, set()).add((d4, _clean(r.get("subject_genome", ""))))
    return rows


def top_with_ties(rows, n):
    ranked = sorted(rows, key=lambda x: (-x[0], x[1]))
    if not ranked or n <= 0:
        return []
    cut = ranked[min(n, len(ranked)) - 1][0]
    return [r for r in ranked if r[0] >= cut]


def check(tables, panels_dir, strains):
    out, missing = [], 0
    for strain, n in strains:
        tree = os.path.join(panels_dir, strain, "PANEL_TREE.tsv")
        issues = os.path.join(panels_dir, strain, "PANEL_ISSUES.tsv")
        panel = set()
        if os.path.exists(tree):
            with open(tree, encoding="utf-8") as fh:
                for r in csv.DictReader(fh, delimiter="\t"):
                    panel |= {_key(x) for x in (r.get("tygs_type_strain") or "").split("; ") if x}
        logged = set()
        if os.path.exists(issues):
            with open(issues, encoding="utf-8") as fh:
                logged = {_key(r.get("item", "")) for r in csv.DictReader(fh, delimiter="\t") if (r.get("source") or "").startswith("TYGS")}
        for rank, (d4, subj) in enumerate(top_with_ties(tables.get(strain, set()), n), 1):
            k = _key(subj)
            status = "in_panel" if k in panel else ("logged" if k in logged else "MISSING_NOT_LOGGED")
            missing += status == "MISSING_NOT_LOGGED"
            out.append((strain, rank, subj, d4, status))
    return out, missing


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--tygs", nargs="+", required=True, help="TYGS digital DDH table(s)")
    ap.add_argument("--panels-dir", required=True, help="folder holding <strain>/PANEL_TREE.tsv and PANEL_ISSUES.tsv")
    ap.add_argument("--strains", nargs="+", required=True, help="strain:N, N = that strain's --tygs-top")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    strains = []
    for s in args.strains:
        if ":" not in s or not s.rsplit(":", 1)[1].isdigit():
            ap.error(f"--strains entries are strain:N, got {s!r}")
        name, n = s.rsplit(":", 1); strains.append((name, int(n)))
    rows, missing = check(read_tables(args.tygs), args.panels_dir, strains)
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = _SafeWriter(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["strain", "tygs_rank", "subject", "d4", "status"]); w.writerows(rows)
    emit(f"{len(rows)} TYGS top-N rows checked; {missing} missing and not logged")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
