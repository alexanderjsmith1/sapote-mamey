#!/usr/bin/env python3
"""
check_deliverable_suite.py — mechanical enforcement of the Sapote full-run deliverable contract.

Turns FULL_RUN_PROFILE Section A (13 items) + the Tier-2 packaging items + the Section H gate
from "prose the model is trusted to self-run" into a checkable artifact. Reads a filled
DELIVERABLE_MANIFEST_<strain>.md (from docs/DELIVERABLE_MANIFEST_TEMPLATE.md) and fails closed on:
  - any of the 13 suite items left blank / still showing the 'COMPLETE/SKIPPED/N/A' placeholder
  - a COMPLETE item with no artifact path
  - a SKIPPED or N/A item with no reason
  - (gold runs) gold_completeness still JUDGMENT_PENDING, or Mode B cards < raw BGC count

Usage:
  python tools/check_deliverable_suite.py --manifest DELIVERABLE_MANIFEST_Amyco-M39.md [--mode gold] [--json]
Exit 0 = PASS, 1 = FAIL. Designed for the release gate and for end-of-run self-check.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, json, re, sys

PLACEHOLDER = "COMPLETE/SKIPPED/N/A"
SUITE_ROWS = 13  # the ordered §A contract

def parse_rows(text):
    rows = []
    for m in re.finditer(r'^\|\s*(\d+)\s*\|([^|]+)\|\s*([A-Za-z/_-]+)\s*\|([^|]*)\|', text, re.M):
        num, name, status, art = m.group(1), m.group(2).strip(), m.group(3).strip(), m.group(4).strip()
        rows.append({"n": int(num), "name": name, "status": status, "artifact": art})
    return rows

def check(text, mode):
    findings = []
    rows = parse_rows(text)
    suite = [r for r in rows if r["n"] <= SUITE_ROWS]
    seen = {r["n"] for r in suite}
    for i in range(1, SUITE_ROWS + 1):
        if i not in seen:
            findings.append(f"item {i}: MISSING row (not found in manifest)")
    for r in suite:
        st = r["status"].upper()
        art = r["artifact"].strip("_ ").strip()
        if st == PLACEHOLDER.upper() or st == "" or PLACEHOLDER.upper() in r["status"].upper():
            findings.append(f"item {r['n']} ({r['name']}): status not filled in (still placeholder)")
        elif st == "COMPLETE" and not art:
            findings.append(f"item {r['n']} ({r['name']}): COMPLETE but no artifact path given")
        elif st in ("SKIPPED", "N/A", "NA") and not art:
            findings.append(f"item {r['n']} ({r['name']}): {st} but no reason given")
        elif st not in ("COMPLETE", "SKIPPED", "N/A", "NA"):
            findings.append(f"item {r['n']} ({r['name']}): invalid status '{r['status']}'")
    # Section H gate (gold)
    if mode == "gold":
        m = re.search(r'gold_completeness:\s*([A-Z_ |\[\]]+)', text)
        if not m:
            # fail CLOSED: a gold manifest that omits the line cannot be assumed complete
            findings.append("Section H: gold_completeness line MISSING (gold manifest must report it)")
        elif "JUDGMENT_PENDING" in m.group(1):
            findings.append("Section H: gold_completeness is JUDGMENT_PENDING (gold run must be COMPLETE)")
        mb = re.search(r'Mode B cards written:\s*(\d+)\s*/\s*(\d+)', text)
        if not mb:
            findings.append("Section H: 'Mode B cards written: X/Y' line MISSING (gold manifest must report it)")
        elif int(mb.group(1)) < int(mb.group(2)):
            findings.append(f"Section H: only {mb.group(1)}/{mb.group(2)} Mode B cards written (gold needs all)")
    # v9.7.374: the old pattern only ever fired when the line's value was ALREADY the literal
    # token PASS or FAIL. docs/DELIVERABLE_MANIFEST_TEMPLATE.md ships this line with the unfilled
    # placeholder value `[PASS|FAIL]` -- which never matches `(PASS|FAIL)` at all, so `sc` was
    # None and the claim-safety/MRSA-Candida/affiliation gate was silently never checked on a
    # manifest that otherwise passed every other item. This is the same fail-open shape as
    # Bug #3 (see test_bug3_deliverable_suite_gold_failclosed.py), fixed there for
    # gold_completeness/Mode B cards but left open here. Capture whatever value the line actually
    # holds and require it to literally be PASS; anything else (FAIL, an unfilled placeholder, or
    # garbage) is a finding.
    sc = re.search(r'Standing-constraint check[^\n]*:\s*([^\n]*)', text)
    if sc:
        sc_val = sc.group(1).strip()
        if sc_val.upper() == "FAIL":
            findings.append("Section H: standing-constraint check reported FAIL")
        elif sc_val.upper() != "PASS":
            findings.append(f"Section H: standing-constraint check not filled in (still shows '{sc_val}')")
    n_complete = sum(1 for r in suite if r["status"].upper() == "COMPLETE")
    return findings, {"suite_items": len(suite), "complete": n_complete}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--mode", default="standard", choices=["smoke", "standard", "gold"])
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    try:
        with open(a.manifest, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        emit(f"error: cannot read manifest '{a.manifest}': {e.strerror}", file=sys.stderr)
        sys.exit(2)
    findings, stats = check(text, a.mode)
    ok = not findings
    if a.json:
        emit(json.dumps({"pass": ok, "mode": a.mode, **stats, "findings": findings}, indent=2))
    else:
        emit(f"Deliverable-suite check [{a.mode}] — {'PASS' if ok else 'FAIL'}", f"  {stats['complete']}/{stats['suite_items']} suite items COMPLETE", sep="\n")
        for f in findings:
            emit(f"  ✗ {f}")
        if ok:
            emit("  ✓ all 13 contract items accounted for; Section H gate satisfied")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
