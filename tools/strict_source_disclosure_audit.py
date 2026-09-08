#!/usr/bin/env python3
"""strict_source_disclosure_audit.py — COMPATIBILITY ENTRY POINT. Holds no policy.

WHERE THE POLICY WENT (v9.7.405, CODEX_396 REPAIR_16 integration)
-----------------------------------------------------------------
The strict pass — an opt-in scan of the two surfaces the default release gate deliberately does
not look at, executable Python content and the tests/ tree — now lives in
`tools/public_release_audit.py` as `strict_source_disclosure_findings()`, reachable from the gate
itself as `audit(root, policy, strict_source_disclosure=True)` or `--strict-source-disclosure`.

That is where this module always said it belonged. It was written standalone ONLY to avoid
colliding with the then-unlanded Archive Transaction Repair 15, and its own docstring recorded the
intent: its core was "written so the Repair-15 evaluator can absorb it verbatim ... once that
repair lands and the owner rules on placement". Repair 15 landed in v9.7.405 and the owner ruled,
so the separation has served its purpose and ended.

Why the move matters rather than being tidying: the gate that decides whether a staged tree may
produce output must OWN this policy. While it lived out here, a caller could run the release gate
and never run the strict pass — "did not look" reported as PASS is the precise failure this pass
was built to prevent, and leaving it in a second file that callers had to remember reproduced that
failure one level up.

WHAT REMAINS HERE
-----------------
The public names, re-exported so existing callers, CI invocations and tests keep working
unchanged, plus the same CLI:

    python tools/strict_source_disclosure_audit.py <tree-root> [--json]

Exit 0 = strict-clean. Exit 1 = finding(s). Exit 2 = invalid root / usage.

A finding is a DISCLOSURE finding, not proof of a leak in a shipped artifact — the default gate's
own scope decisions still stand. This pass exists so nobody mistakes "did not look" for "clean".

NOTE FOR WHOEVER EDITS THIS FILE: it must contain no identifier pattern, allowlist, normalisation
rule or scan predicate. If you find yourself adding one here, it belongs in public_release_audit.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import public_release_audit as pra

# Compatibility aliases. The historical names are the contract for existing callers and tests;
# the implementations are the release gate's, and there is exactly one of each in the tree.
strict_findings = pra.strict_source_disclosure_findings
load_synthetic_allowlist = pra._strict_synthetic_allowlist
_normalise = pra._strict_normalise


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Opt-in strict source-disclosure pass (python content + tests/ tree); "
                    "a thin front door onto public_release_audit's strict pass.")
    ap.add_argument("root", help="path to the tree to audit")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--show-identifiers", action="store_true",
                    help="verbose findings (paths + matched identifiers); default is redacted")
    a = ap.parse_args(argv)
    root = Path(a.root).resolve()
    hits = strict_findings(root, show_identifiers=a.show_identifiers)
    invalid = any(h.startswith("root ") for h in hits)
    if a.json:
        sys.stdout.write(json.dumps({"findings": hits}, indent=2) + "\n")
        return 2 if invalid else (1 if hits else 0)
    if invalid:
        for h in hits:
            sys.stderr.write(f"  ✗ {h}\n")
        return 2
    if hits:
        sys.stdout.write(f"STRICT SOURCE DISCLOSURE: FAIL ({len(hits)} finding(s)"
                         f"{'' if a.show_identifiers else '; diagnostics redacted, --show-identifiers to expand'})\n")
        for h in hits:
            sys.stdout.write(f"  ✗ {h}\n")
        return 1
    sys.stdout.write("STRICT SOURCE DISCLOSURE: PASS (python source + tests/ tree strict-clean)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
