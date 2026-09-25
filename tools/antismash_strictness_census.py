#!/usr/bin/env python3
"""antismash_strictness_census.py — say which antiSMASH detection strictness each result used, before anyone compares
region counts across genomes.

Why: the same genome gives very different region counts at different hmmdetection strictness settings (loose calls extra
classes such as saccharide). A cohort table that mixes settings inflates some genomes against others. Found 2026-09-24:
the governed per-genome region counts mixed loose and default runs for 7 bee/wasp genomes.

Input: antiSMASH result ZIPs or result folders (anything holding the run's main .json). The setting is read from each record's
results: records[].modules["antismash.detection.hmm_detection"].strictness. Region counts are unique *.regionNNN.gbk
names, ignoring macOS copies ("__MACOSX/" entries and "._" AppleDouble files anywhere).

Usage:
  python tools/antismash_strictness_census.py RESULT [RESULT ...] [--tsv out.tsv] [--require-uniform]
Exit 0 always, unless --require-uniform and more than one strictness is present (exit 3), or a result has no readable
setting (reported as "unknown"; exit 3 under --require-uniform).
"""
from __future__ import annotations
import argparse, json, re, sys, zipfile
from pathlib import Path
try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run from a foreign cwd
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

REGION = re.compile(r"\.region\d+\.gbk$")


def _read_members(path: Path):
    """Yield (name, bytes-reader) for the files of a ZIP or folder."""
    if path.is_file() and zipfile.is_zipfile(path):
        z = zipfile.ZipFile(path)
        for n in z.namelist():
            if "__MACOSX" in n or n.rsplit("/", 1)[-1].startswith("._"):   # macOS copies, inside or outside __MACOSX/
                continue
            yield n, (lambda n=n: z.read(n))
    elif path.is_dir():
        for p in path.rglob("*"):
            if p.is_file() and "__MACOSX" not in p.parts and not p.name.startswith("._"):
                yield str(p.relative_to(path)), (lambda p=p: p.read_bytes())
    else:
        raise FileNotFoundError(f"not an antiSMASH ZIP or folder: {path}")


def strictness_of_json(data: dict) -> set[str]:
    found = set()
    for rec in data.get("records", []):
        hmm = (rec.get("modules") or {}).get("antismash.detection.hmm_detection") or {}
        if isinstance(hmm, dict) and hmm.get("strictness"):
            found.add(str(hmm["strictness"]))
    return found


def census(path: Path) -> dict:
    regions, settings, version = set(), set(), ""
    for name, read in _read_members(path):
        base = Path(name).name
        if REGION.search(base):
            regions.add(base)
        elif base.endswith(".json"):
            try:
                data = json.loads(read())
            except (ValueError, UnicodeDecodeError):
                continue
            if isinstance(data, dict) and "records" in data:
                settings |= strictness_of_json(data)
                version = version or str(data.get("version", ""))
    strict = ",".join(sorted(settings)) if settings else "unknown"
    return {"result": str(path), "antismash_version": version, "strictness": strict, "regions": len(regions)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("results", nargs="+", type=Path)
    ap.add_argument("--tsv", type=Path)
    ap.add_argument("--require-uniform", action="store_true")
    a = ap.parse_args(argv)
    rows = [census(p) for p in a.results]
    w = _SafeDictWriter(open(a.tsv, "w", newline="") if a.tsv else sys.stdout, fieldnames=list(rows[0]), delimiter="\t",
                       lineterminator="\n")
    w.writeheader(); w.writerows(rows)
    kinds = {r["strictness"] for r in rows}
    if a.require_uniform and (len(kinds) > 1 or "unknown" in kinds):
        print(f"STRICTNESS_MIXED: {sorted(kinds)} — do not compare region counts across these results", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
