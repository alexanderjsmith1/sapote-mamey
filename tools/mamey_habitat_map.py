#!/usr/bin/env python3
"""
mamey_habitat_map.py — build the strain->habitat map L5/L6 need, store-backed.

Reads each sealed package's manifest.json `source` field (the --source string set at
run time) and normalizes it to a habitat category via a rule table. This is the real
tool for the map: it generalizes to any cohort (glob packages), and every row is
store-backed from the manifest — no guessing. Rows it can't classify are emitted as
`UNASSIGNED` with the raw source, flagged for the Master Strain List rather than
silently bucketed.

Usage: python mamey_habitat_map.py <packages_dir_or_glob> --out habitat_map.csv
       (packages_dir contains <strain>/package/manifest.json, or pass a manifest glob)
Output cols: strain, taxonomy, raw_source, habitat, provenance
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import sys, json, csv, glob, argparse, re, os
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wbio import atomic_open


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)


# rule table: (regex over lowercased source) -> habitat. First match wins. ORDER IS LOAD-BEARING:
# `termite` MUST precede `attine` — "fungus-growing termite" matches both, and first-match must give termite.
RULES = [
    (r"bumblebee|bombus|honey ?bee|\bapis\b|\bbee\b|bee-assoc", "bee"),
    (r"\bwasp\b|vespul|polist|\bvespa\b|hornet", "wasp"),
    (r"\bmoss\b|bryophyt|sphagnum|liverwort", "moss"),
    (r"termite|macroterm", "termite"),  # fungus-growing termites are a distinct lineage from attine ants
    (r"attine|acromyrmex|\batta\b|trachymyrmex|leaf.?cutter|fungus.?grow.*ant|attine ant", "attine"),
    (r"clinical|homo sapiens|human|sputum|patient|bronch|wound", "clinical"),
    (r"\bsoil\b|rhizosph|marine|sediment|environ|freshwater|\bwater\b", "environmental"),
]
def classify(src):
    s = (src or "").lower()
    for rx, hab in RULES:
        if re.search(rx, s): return hab
    # accession-only reference/type strains with no host term
    if re.search(r"gca_|nz_|type strain|reference", s) or not s.strip():
        return "reference/type"
    return "UNASSIGNED"

def find_manifests(target):
    p = Path(target)
    if p.is_dir():
        return sorted(glob.glob(f"{target}/*/package/manifest.json")) or \
               sorted(glob.glob(f"{target}/**/manifest.json", recursive=True))
    return sorted(glob.glob(target))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="packages dir (with <strain>/package/manifest.json) or manifest glob")
    ap.add_argument("--out", default="habitat_map.csv")
    a = ap.parse_args()
    rows = []
    for mf in find_manifests(a.target):
        try:
            d = _read_json(mf, encoding="utf-8")
        except Exception as e:
            emit(f"  skip {mf}: {e}"); continue
        strain = d.get("strain_id") or d.get("strain") or Path(mf).parents[1].name
        src = d.get("source", "")
        hab = classify(src)
        rows.append([strain, d.get("taxonomy", ""), src, hab, "store-backed:manifest.source"])
    rows.sort()
    # v9.7.374 fix: was a bare open(a.out, "w") -- this tool's own docstring calls itself
    # "the real tool" (store-backed, no guessing) that L5/L6 depend on; a kill mid-write left a
    # truncated habitat_map.csv silently indistinguishable from a genuine complete one to any
    # downstream consumer. atomic_open (tools/_wbio.py) supports the same newline="" CSV-writer
    # contract as a drop-in.
    with atomic_open(a.out, newline="") as fh:
        w = _SafeWriter(fh); w.writerow(["strain", "taxonomy", "raw_source", "habitat", "provenance"]); w.writerows(rows)
    from collections import Counter
    c = Counter(r[3] for r in rows)
    emit(f"[habitat-map] {len(rows)} strains -> {dict(c)}")
    un = [r[0] for r in rows if r[3] == "UNASSIGNED"]
    if un: emit(f"  UNASSIGNED (need Master Strain List): {un}")
    emit(f"  wrote {a.out}")

if __name__ == "__main__":
    main()
