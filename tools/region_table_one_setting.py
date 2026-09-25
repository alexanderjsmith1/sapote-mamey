#!/usr/bin/env python3
"""One table of antiSMASH regions across genomes, all from ONE detection strictness.

Why: a genus region-count figure was once built from counts that mixed loose-strictness antiSMASH
runs with default-strictness runs. Loose runs call extra regions, saccharide above all, so the
loose-run genomes looked richer than the rest.
check_antismash_profile.py exists to catch exactly this, but it reads package manifests, and the
count tables behind figures are not packages. This tool builds the count table straight from the
antiSMASH zips and refuses to mix settings.

What it does:
  * reads each zip's strictness with mamey.antismash_input.detect_strictness;
  * refuses (exit 2) if any zip is not --strictness, or is unknown, or two different zips
    claim one strain (byte-identical copies count once);
  * drops hard-excluded strains (mamey.exclusions) unless --no-exclusions, and says which;
  * drops regions on contigs listed in --drop-contigs STRAIN=removed_contigs.tsv (first column =
    record id), for decontaminated assemblies, and reports how many listed contigs matched;
  * writes one row per region and a receipt with each zip's sha256.

Usage:
  region_table_one_setting.py --zips <dir|zip> [...] --strictness loose --out regions.tsv
      [--drop-contigs STRAIN=<strain>/decontam_<date>/<strain>_removed_contigs.tsv]
      [--no-exclusions]
Writes <out> and <out stem>_RECEIPT.tsv. Name the strictness in any caption built on it.
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

import argparse
import csv
import hashlib
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path
try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run from a foreign cwd
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

from mamey.antismash_input import VALID_STRICTNESS, detect_strictness
from mamey.ziputil import regular_file_names

REGION_GBK = re.compile(r"(?:^|/)([^/]+)\.region(\d+)\.gbk$")
REGION_BLOCK = re.compile(r"\n     region .*?(?=\n     \S|\nORIGIN)", re.S)
PRODUCT = re.compile(r'/product="([^"]+)"')


def strain_of(zip_path: Path) -> str:
    return re.sub(r"\.zip$", "", zip_path.name, flags=re.I)


def find_zips(inputs: list[Path]) -> list[Path]:
    out = []
    for p in inputs:
        cands = [p] if p.is_file() else sorted(p.rglob("*.zip"))
        out += [z for z in cands if z.suffix.lower() == ".zip" and not z.name.startswith("._")
                and "__MACOSX" not in z.parts]
    return out


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_drop_lists(specs: list[str]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for spec in specs:
        strain, sep, path = spec.partition("=")
        if not strain or not sep or not path:
            raise ValueError(f"--drop-contigs needs STRAIN=path, got {spec!r}")
        if strain in out:
            raise ValueError(f"duplicate --drop-contigs strain {strain!r}")
        with open(path, encoding="utf-8", newline="") as fh:
            values = [row[0].strip() for row in csv.reader(fh, delimiter="\t")
                      if row and row[0].strip() and not row[0].strip().startswith("#")]
        if values and values[0].casefold() in {"contig", "record", "record_id"}:
            values.pop(0)
        if not values:
            raise ValueError(f"--drop-contigs for {strain!r} has no contig IDs")
        out[strain] = set(values)
    return out


def regions_of(zf: zipfile.ZipFile) -> list[dict]:
    rows = []
    seen_files = set()
    for name in regular_file_names(zf):
        m = REGION_GBK.search(name)
        if not m:
            continue
        region_file = Path(name).name
        if region_file in seen_files:
            raise ValueError(f"duplicate region filename in ZIP: {region_file}")
        seen_files.add(region_file)
        text = zf.read(name).decode(errors="ignore")
        m_block = REGION_BLOCK.search(text)
        block = m_block.group(0) if m_block else ""
        rows.append(dict(record=m.group(1), region_file=region_file,
                         products=";".join(PRODUCT.findall(block)),
                         contig_edge=int('contig_edge="True"' in block)))
    return rows


def build(zips: list[Path], strictness: str, drop: dict[str, set[str]], excluded: set[str],
          allow_zero_drop: set[str] | None = None):
    allow_zero_drop = set() if allow_zero_drop is None else allow_zero_drop
    problems, receipt, rows = [], [], []
    by_strain: dict[str, list[Path]] = {}
    for z in zips:
        by_strain.setdefault(strain_of(z), []).append(z)
    copies = {s: len(zs) for s, zs in by_strain.items()}
    for s, zs in sorted(by_strain.items()):
        if len(zs) > 1:
            # A genome's identity is its zip digest: byte-identical copies are one input.
            if len({sha256(z) for z in zs}) == 1:
                by_strain[s] = zs[:1]
            else:
                problems.append(f"{s}: {len(zs)} different zips claim this strain: " + "; ".join(map(str, zs)))
    unmatched_drop = set(drop) - set(by_strain)
    for s in sorted(unmatched_drop):
        problems.append(f"{s}: --drop-contigs given but no zip for this strain")
    for s, zs in sorted(by_strain.items()):
        if len(zs) > 1:
            continue
        z = zs[0]
        if s in excluded:
            receipt.append(dict(strain=s, zip=str(z), sha256=sha256(z), strictness="", evidence="",
                                n_regions=0, n_dropped=0, drop_list_matched="", identical_copies=copies[s],
                                status="hard-excluded"))
            continue
        try:
            with zipfile.ZipFile(z) as zf:
                got, evidence = detect_strictness(zf)
                regs = regions_of(zf)
        except (ValueError, OSError, zipfile.BadZipFile) as exc:
            problems.append(f"{s}: {exc}")
            continue
        if got != strictness:
            problems.append(f"{s}: strictness {got} ({evidence}); table is {strictness}")
        dl = drop.get(s, set())
        kept = [r for r in regs if r["record"] not in dl]
        matched = len({r["record"] for r in regs} & dl)
        if dl and matched == 0 and s not in allow_zero_drop:
            problems.append(f"{s}: ZERO_DROP_REFUSED; no region record matched the drop list")
        digest = sha256(z)
        for r in kept:
            rows.append(dict(strain=s, strictness=got, **r, zip_sha256=digest))
        receipt.append(dict(strain=s, zip=str(z), sha256=digest, strictness=got, evidence=evidence,
                            n_regions=len(kept), n_dropped=len(regs) - len(kept),
                            drop_list_matched=f"{matched}/{len(dl)}" if dl else "", identical_copies=copies[s],
                            status="kept"))
    return rows, receipt, problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--zips", nargs="+", type=Path, required=True)
    ap.add_argument("--strictness", required=True, choices=VALID_STRICTNESS)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--drop-contigs", action="append", default=[], metavar="STRAIN=TSV")
    ap.add_argument("--allow-zero-drop", action="append", default=[], metavar="STRAIN",
                    help="permit zero matching regions for this drop-list strain after review")
    ap.add_argument("--no-exclusions", action="store_true", help="do not drop mamey.exclusions hard-excluded strains")
    a = ap.parse_args(argv)
    zips = find_zips(a.zips)
    if not zips:
        print("no antiSMASH zips found", file=sys.stderr)
        return 1
    excluded: set[str] = set()
    if not a.no_exclusions:
        from mamey.exclusions import load_exclusions
        excluded = set(load_exclusions(strict=True)["hard_excluded"])
    try:
        drop = read_drop_lists(a.drop_contigs)
    except (OSError, ValueError) as exc:
        ap.error(str(exc))
    if set(a.allow_zero_drop) - set(drop):
        ap.error("--allow-zero-drop requires a matching --drop-contigs strain")
    rows, receipt, problems = build(zips, a.strictness, drop, excluded, set(a.allow_zero_drop))
    if problems:
        print("REFUSED: the table would mix inputs.", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        return 2
    a.out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["strain", "strictness", "record", "region_file", "products", "contig_edge", "zip_sha256"]
    with open(a.out, "w", newline="") as fh:
        w = _SafeDictWriter(fh, fieldnames=fields, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    rec = a.out.with_name(a.out.stem + "_RECEIPT.tsv")
    with open(rec, "w", newline="") as fh:
        w = _SafeDictWriter(fh, fieldnames=list(receipt[0]), delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(receipt)
    kept = [r for r in receipt if r["status"] == "kept"]
    print(f"{len(kept)} genomes, {len(rows)} regions, all {a.strictness}; "
          f"hard-excluded {sum(r['status'] == 'hard-excluded' for r in receipt)}; "
          f"contig-dropped {sum(r['n_dropped'] for r in kept)} -> {a.out}")
    per = Counter(r["strain"] for r in rows)
    print("regions per genome: " + ", ".join(f"{s} {n}" for s, n in sorted(per.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
