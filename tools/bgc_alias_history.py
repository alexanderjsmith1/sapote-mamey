#!/usr/bin/env python3
"""bgc_alias_history.py — which BGC id did this locus carry in the PRIOR run of the same strain?

    python tools/bgc_alias_history.py --prior <old package dir> --current <new package dir>
                                      [--min-overlap 0.5] [--write]

Prints the alias history JSON on stdout (stdout IS the receipt; registered excluded-by-design in
tools/repo_health.py). --write also stores it as bgc_alias_history.json in the CURRENT package.
Refuses (exit 2, typed JSON on stderr) when the two packages are not the same strain. v9.7.405;
revives the June-2026 legacy-id idea. Claim-safety: locus bookkeeping only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mamey.bgc_alias_history import load_inventory, reconcile, write_history  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--prior", required=True); ap.add_argument("--current", required=True)
    ap.add_argument("--min-overlap", type=float, default=0.5)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    try:
        ps, prior = load_inventory(a.prior)
        cs, cur = load_inventory(a.current)
    except FileNotFoundError as e:
        sys.stderr.write(json.dumps({"status": "REFUSED", "error_code": "NO_INVENTORY", "message": str(e)}) + "\n")
        return 2
    if ps != cs:
        sys.stderr.write(json.dumps({"status": "REFUSED", "error_code": "STRAIN_MISMATCH",
                                     "message": f"prior={ps} current={cs}"}) + "\n")
        return 2
    hist = reconcile(prior, cur, min_overlap=a.min_overlap)
    hist.update({"strain": cs, "prior_package": Path(a.prior).name, "current_package": Path(a.current).name})
    if a.write:
        hist["receipt_path"] = write_history(a.current, hist).name
    print(json.dumps(hist, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
