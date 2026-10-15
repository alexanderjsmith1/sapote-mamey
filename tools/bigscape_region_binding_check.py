#!/usr/bin/env python3
"""Check that a strain's staged BiG-SCAPE region files are the same regions as its Mamey package inventory.

bigscape_prep.py names each staged file <strain>_<antiSMASH region file>; some staging routes use two underscores
(<strain>__<file>), and both are read. The package inventory (<strain>_2_inventory.csv, or a single
<strain>*_2_inventory.csv such as a versioned name) lists the same file name (Source_GBK) and the region's Start and
End. A strain passes only when the two name sets are identical and every file's "Orig. start" and "Orig. end" equal
the inventory's Start and End. Anything else is a MISMATCH: that strain's regions must not be labelled from the
inventory. A missing or ambiguous inventory, or a missing staged-file folder, is a typed STOP, not a guess.

Usage: bigscape_region_binding_check.py --inventory-dir <dir> --gbk-dir <staged gbk_input> --strain AS-... [--strain ...]
       [--out <folder>]
Writes BINDING_CHECK.tsv in --out (default: current folder) and exits 1 if any strain fails, 2 on a STOP.
"""
import os as _os, sys as _sys  # resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
try:  # CSV formula-cell guard (mamey/csv_safety.py)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import argparse
import csv
import re
import sys
from pathlib import Path

ORIG = re.compile(r"Orig\.\s+(start|end)\s*::\s*(\d+)")
FIELDS = ("strain", "result", "inventory", "inventory_regions", "staged_regions", "only_in_inventory",
          "only_staged", "coordinate_mismatches", "examples")


def _stop(msg):
    sys.stderr.write(f"BINDING_CHECK_STOP: {msg}\n")
    raise SystemExit(2)


def coords(gbk):
    found = {}
    with open(gbk, errors="replace") as fh:
        for line in fh:
            m = ORIG.search(line)
            if m:
                found.setdefault(m.group(1), int(m.group(2)))
            if line.startswith("FEATURES"):
                break
    return found.get("start"), found.get("end")


def find_inventory(inv_dir, strain):
    exact = inv_dir / f"{strain}_2_inventory.csv"
    if exact.is_file():
        return exact
    cands = sorted(p for p in inv_dir.glob("*_2_inventory.csv")
                   if re.match(re.escape(strain) + r"(_[^_].*)?_2_inventory\.csv$", p.name))
    if len(cands) != 1:
        _stop(f"{strain}: expected one inventory in {inv_dir}, found {[p.name for p in cands]}")
    return cands[0]


def check(strain, inv_dir, gbk_dir):
    inv = find_inventory(inv_dir, strain)
    with open(inv, newline="") as fh:
        rows = list(csv.DictReader(fh))
    try:
        want = {r["Source_GBK"]: (int(r["Start"]), int(r["End"])) for r in rows}
    except (KeyError, ValueError) as exc:
        _stop(f"{strain}: inventory {inv.name} lacks a usable Source_GBK/Start/End ({exc})")
    head = re.compile(re.escape(strain) + r"_+(?=[^_])")
    have = {head.sub("", p.name, count=1): p for p in gbk_dir.iterdir()
            if head.match(p.name) and re.search(r"region\d+\.gbk$", p.name)}
    only_inv, only_staged = sorted(set(want) - set(have)), sorted(set(have) - set(want))
    coord_bad = [n for n in sorted(set(want) & set(have)) if coords(have[n]) != want[n]]
    ok = not (only_inv or only_staged or coord_bad)
    return dict(strain=strain, result="MATCH" if ok else "MISMATCH", inventory=inv.name,
                inventory_regions=len(want), staged_regions=len(have), only_in_inventory=len(only_inv),
                only_staged=len(only_staged), coordinate_mismatches=len(coord_bad),
                examples=";".join((only_inv + only_staged + coord_bad)[:3]))


def main(argv=None):
    ap = argparse.ArgumentParser(allow_abbrev=False, description=__doc__.split("\n")[0])
    ap.add_argument("--inventory-dir", required=True)
    ap.add_argument("--gbk-dir", required=True)
    ap.add_argument("--strain", action="append", required=True)
    ap.add_argument("--out", default=".")
    a = ap.parse_args(argv)
    inv_dir, gbk_dir = Path(a.inventory_dir), Path(a.gbk_dir)
    for label, d in (("--inventory-dir", inv_dir), ("--gbk-dir", gbk_dir)):
        if not d.is_dir():
            _stop(f"{label} {d} is not a folder")
    rows = [check(s, inv_dir, gbk_dir) for s in a.strain]
    out = Path(a.out) / "BINDING_CHECK.tsv"
    with open(out, "w", newline="") as fh:
        w = _SafeDictWriter(fh, list(FIELDS), delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        emit("\t".join(str(r[f]) for f in FIELDS))
    return 1 if any(r["result"] != "MATCH" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
