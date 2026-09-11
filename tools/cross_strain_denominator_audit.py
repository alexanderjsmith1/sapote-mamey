#!/usr/bin/env python3
"""cross_strain_denominator_audit.py — fail-closed invariant on cohort-size denominators (v9.7.116).

WHY THIS EXISTS
---------------
A multi-strain master grows as strains are added. Cross-strain sheets state findings as `N/M`
(e.g. "ectoine 17/18", "universal classes 18/18") where M is the cohort size. If a populator
hardcodes M, or a recompute fails to re-fire on cohort growth, the sheet silently keeps a stale
denominator — a wrong number that *looks* computed. This bit the 24-strain master: every sheet was
current at 24 except two rows of Cross_Strain_Findings frozen at 18-strain literals (18/18,
17/18, 15/18). A synthesis writer reading that sheet would faithfully reproduce stale numbers and
look correct doing it.

THE INVARIANT
-------------
Every cohort-size denominator on a cross-strain sheet must equal len(A2_Strain_Registry). This is a
cheap, fail-closed content check: scan the cross-strain sheets for `N/M` tokens where M is a
plausible cohort denominator and assert M == registry length.

It deliberately does NOT flag every `N/M` — only denominators that look like cohort-size counts.
Ratios over BGC totals (e.g. "164/1131") use a different denominator (the BGC count), so the audit
only checks M against EITHER the registry length OR the BGC total, failing only when M matches
neither.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import re
import sys

import openpyxl

# sheets whose findings use cohort-size denominators
_CROSS_STRAIN_SHEETS = (
    "Cross_Strain_Findings",
    "Cross_Strain_Class_Prevalence",
    "Cross_Strain_Compare",
    "Strain_Cohort_Context",
)

# v9.7.409 (CLAUDE_409_mibig_comparator_fixes): the registry/BGC-total sheet names were hardwired
# to a single workbook TEMPLATE (A2_Strain_Registry / B1_BGC_Master / Cross_Strain_*). The cohort
# pipeline actually emits COHORT_MASTER.xlsx with sheets `strain_summary` (one row per strain) and
# `bgc_inventory` (one row per BGC). On the real master the template names are absent, so
# _registry_length() returned 0 and the audit ALWAYS fired "cannot establish cohort size" (exit 1) --
# fail-safe (no false PASS) but non-functional: it could never audit real cohort output. The lookups
# below auto-detect the schema: they try the template sheet first (byte-identical behaviour on any
# template workbook), then fall back to the emitted equivalent. Each candidate's first data column
# is the strain (registry) or BGC id, so the same "count non-empty col-0 rows below the header" rule
# applies to both schemas.
_REGISTRY_SHEETS = ("A2_Strain_Registry", "strain_summary")
_BGC_SHEETS = ("B1_BGC_Master", "bgc_inventory")

# an N/M token: one or more "<int>/<int>" occurrences inside a cell value
_NM = re.compile(r"\b(\d+)\s*/\s*(\d+)\b")


def _count_col0_rows(ws) -> int:
    """Count data rows (below the header) whose first column is non-empty."""
    return sum(1 for r in ws.iter_rows(min_row=2, values_only=True) if r and r[0])


def _registry_length(wb) -> int:
    for name in _REGISTRY_SHEETS:
        if name in wb.sheetnames:
            return _count_col0_rows(wb[name])
    return 0


def _bgc_total(wb) -> int:
    for name in _BGC_SHEETS:
        if name in wb.sheetnames:
            return _count_col0_rows(wb[name])
    return 0


def audit_denominators(workbook_path: str) -> list[str]:
    """Return a list of violation strings (empty == clean). A violation is an N/M denominator on a
    cross-strain sheet whose M equals neither the registry length nor the BGC total."""
    wb = openpyxl.load_workbook(workbook_path, read_only=True, data_only=True)
    n_reg = _registry_length(wb)
    n_bgc = _bgc_total(wb)
    if n_reg == 0:
        wb.close()
        return ["strain registry empty or absent (looked for sheets: "
                + ", ".join(_REGISTRY_SHEETS) + ") — cannot establish cohort size."]

    # plausible cohort denominators: the registry length and (separately) the BGC total.
    allowed = {n_reg, n_bgc}
    # v9.7.401 (BC2): the window's LOWER bound used to be `n_reg - 12` -- symmetric with the
    # upper bound. But a stale cohort denominator is, by construction, always SMALLER than the
    # live registry length (the cohort only ever grows; that is the entire failure mode this
    # tool's own docstring documents: an 18-strain snapshot surviving inside a 24-strain
    # master). A fixed +/-12 window therefore gets WORSE at its actual job as the cohort grows
    # and the drift between "when a number went stale" and "now" gets larger -- exactly
    # inverted from what a fail-closed invariant should do. Reproduced live: a genuine stale
    # denominator (17/18) inside a 44-strain registry (drift 26, outside the old +/-12 window)
    # reported a clean PASS on the real pristine script -- the identical defect class this
    # tool's own docstring cites as its origin (18/18, 17/18, 15/18 stale in a 24-strain
    # master), just with more elapsed drift. No existing test exercised the lower bound as
    # protecting anything real: the one "different ratio, not a cohort count" case this project
    # actually has (a BGC-total ratio, e.g. 164/1131) is already excluded by the exact-match
    # `allowed` set above, not by window proximity. Lower bound widened to a small fixed floor
    # (any cohort this project has ever had is comfortably above single digits); the upper
    # bound is UNCHANGED -- a denominator ABOVE the live registry length is a different,
    # rarer failure shape with no historical incident motivating a wider allowance here.
    lo, hi = 2, n_reg + 12

    violations: list[str] = []
    for sheet in _CROSS_STRAIN_SHEETS:
        if sheet not in wb.sheetnames:
            continue
        ws = wb[sheet]
        for ri, row in enumerate(ws.iter_rows(values_only=True), 1):
            for cell in row:
                if not cell:
                    continue
                for m in _NM.finditer(str(cell)):
                    denom = int(m.group(2))
                    if denom in allowed:
                        continue
                    # only flag denominators that look like a (stale) cohort count
                    if lo <= denom <= hi:
                        violations.append(
                            f"{sheet} row {ri}: denominator {m.group(0)!r} uses M={denom}, "
                            f"but the cohort size is {n_reg} (registry length). Stale cohort count.")
    wb.close()
    return violations


def ambiguous_denominators(workbook_path: str) -> list[str]:
    """Return informational notes for N/M tokens on the cross-strain sheets whose M matches
    neither the registry length nor the BGC total AND falls OUTSIDE audit_denominators()'s
    +/-12 cohort-size window — i.e. tokens that function is structurally unable to see at all.

    BC2-CSD-01 (v9.7.396): the +/-12 window exists to avoid false-flagging a genuinely smaller,
    unrelated per-category ratio as a stale cohort count — a reasonable anti-false-positive design.
    But a denominator that is FAR from the current registry length (e.g. a synthesis sheet frozen
    at a much smaller cohort snapshot from an earlier pass — exactly the "wrong number that looks
    computed" failure this tool's own docstring says it exists to catch, just a bigger drift than
    its motivating 18-vs-24 incident) falls outside the window and is silently invisible: not in
    `allowed`, not in `[lo, hi]`, never mentioned in the audit's output at all. Reproduced: a
    registry of 44 strains with a Cross_Strain_Findings cell reading "5/10" (a badly-stale count,
    nowhere near 44) produces zero violations from audit_denominators().

    This is deliberately NOT folded into audit_denominators()'s blocking `violations` list — a
    denominator this far from cohort size genuinely could be an unrelated per-category ratio, and
    forcing a hard FAIL on it risks the false positives the window was built to avoid. Instead this
    makes the previously invisible boundary VISIBLE (main() prints these as a non-blocking NOTE
    section) so a human reviewer can judge cases the fail-closed check structurally cannot.
    audit_denominators()'s own return contract, blocking behavior, and every existing pinned test
    against it are unchanged.
    """
    wb = openpyxl.load_workbook(workbook_path, read_only=True, data_only=True)
    n_reg = _registry_length(wb)
    n_bgc = _bgc_total(wb)
    if n_reg == 0:
        wb.close()
        return []
    allowed = {n_reg, n_bgc}
    lo, hi = max(2, n_reg - 12), n_reg + 12

    notes: list[str] = []
    for sheet in _CROSS_STRAIN_SHEETS:
        if sheet not in wb.sheetnames:
            continue
        ws = wb[sheet]
        for ri, row in enumerate(ws.iter_rows(values_only=True), 1):
            for cell in row:
                if not cell:
                    continue
                for m in _NM.finditer(str(cell)):
                    denom = int(m.group(2))
                    if denom in allowed or (lo <= denom <= hi):
                        continue  # already handled (matched or in audit_denominators()'s window)
                    notes.append(
                        f"{sheet} row {ri}: denominator {m.group(0)!r} uses M={denom}, far from "
                        f"cohort size {n_reg} — outside the audit's detection window; not "
                        f"auto-flagged (could be an unrelated ratio), but review manually.")
    wb.close()
    return notes


def denominator_audit_result(workbook_path: str) -> dict:
    """Return the machine-readable audit state without pooling blocking and review-only rows.

    ``PASS`` means no blocking violations and no review-only denominator tokens.
    ``PASS_WITH_REVIEW_NOTES`` means no blocking violations were found, but one or more
    denominator tokens fell outside the detector window and still require human review.
    ``FAIL`` is reserved for blocking stale cohort-size denominators.
    """
    violations = audit_denominators(workbook_path)
    notes = [] if violations else ambiguous_denominators(workbook_path)
    status = "FAIL" if violations else ("PASS_WITH_REVIEW_NOTES" if notes else "PASS")
    return {
        "schema_version": "sapote-mamey.cross-strain-denominator-audit.v1",
        "status": status,
        "blocking_violations": violations,
        "blocking_violation_count": len(violations),
        "review_notes": notes,
        "review_note_count": len(notes),
    }


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        emit("usage: cross_strain_denominator_audit.py <master_workbook.xlsx>", file=sys.stderr)
        return 2
    result = denominator_audit_result(argv[0])
    if result["status"] == "FAIL":
        emit("CROSS-STRAIN DENOMINATOR AUDIT FAILED — stale cohort-size denominators:",
              file=sys.stderr)
        for v in result["blocking_violations"]:
            emit(f"  {v}", file=sys.stderr)
        return 1
    if result["status"] == "PASS_WITH_REVIEW_NOTES":
        emit("cross-strain denominator audit PASS_WITH_REVIEW_NOTES - "
              "no blocking denominator violations; review-only tokens remain.")
        emit("NOTE — denominator(s) outside the audit's detection window (not auto-flagged, "
              "review manually):", file=sys.stderr)
        for n in result["review_notes"]:
            sys.stderr.write(str(f"  {n}") + "\n")
        return 0
    emit("cross-strain denominator audit PASS - no blocking denominator violations and no "
          "review-only denominator tokens.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
