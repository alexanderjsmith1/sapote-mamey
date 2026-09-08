#!/usr/bin/env python3
"""lead_propagation_gate.py — does every triage-board lead reach every lead-listing surface?

Operator front door for mamey/lead_propagation.py (v9.7.405; revives the June-2026
required_destinations audit). Post-seal, read-only, advisory unless --strict.

    python tools/lead_propagation_gate.py <package_dir> [--strict] [--tiers Exceptional High]
                                          [--write-receipt]

Prints the receipt JSON on stdout (this tool's stdout IS its receipt; it is registered as
excluded-by-design in tools/repo_health.py). Exit 0 on PASS/NO_LEADS, 2 on FAIL with --strict,
3 when no triage board is found. Never edits a package unless --write-receipt is given, and then
only adds lead_propagation.json. Claim-safety: presence of locked BGC ids only, no judgment.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mamey.lead_propagation import LEAD_TIERS, audit_package, write_receipt  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("package", help="sealed Mamey package directory")
    ap.add_argument("--tiers", nargs="+", default=list(LEAD_TIERS),
                    help="Lead_tier_auto values counted as leads (default: %(default)s)")
    ap.add_argument("--strict", action="store_true", help="exit 2 on FAIL")
    ap.add_argument("--write-receipt", action="store_true", help="also write lead_propagation.json into the package")
    args = ap.parse_args(argv)
    pkg = Path(args.package)
    if not pkg.is_dir():
        print(json.dumps({"status": "ERROR", "error_code": "NOT_A_DIRECTORY"}), file=sys.stderr)
        return 3
    receipt = audit_package(pkg, tiers=tuple(args.tiers))
    if args.write_receipt:
        receipt["receipt_path"] = os.path.basename(str(write_receipt(pkg, receipt)))
    print(json.dumps(receipt, indent=2, sort_keys=True))
    if receipt["status"] == "NO_BOARD":
        return 3
    if receipt["status"] == "FAIL" and args.strict:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
