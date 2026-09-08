#!/usr/bin/env python3
"""build_domain_reference.py — emit a per-package domain functional-context dictionary (DOMREF-01).

Closes the long-standing DOMREF-01 gap: the Mode-B cards/figures referred to a
``domain_reference.tsv`` that the bundle never shipped. This tool regenerates that substrate
FROM a sealed Mamey package (its banked ``*_domains.csv`` + ``*_3_antismash_hmm.csv``),
using the single-sourced vocabulary in ``mamey.domain_reference``. Run once per package (or
point ``--package`` at several and it unions them) → ``domain_reference.tsv`` (machine) +
``domain_reference.md`` (grouped, human-readable). Mode-B cards then pull category + context
from here instead of re-writing the same domain description in every card.

CLAIM SAFETY (mandatory): every row states the *domain's* biochemical role (what the domain
does), NEVER that any BGC makes a given product. Category is a deterministic function bucket;
counts are how many BGCs (across the given packages) carry the domain. Function only — no
activity, structure, or product claim. This is a reference emitter: it ranks nothing and moves
no tier.

Usage:
  python tools/build_domain_reference.py --package runs/AS-XXX/package
  python tools/build_domain_reference.py --package pkgA --package pkgB --out /tmp/domref
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import csv
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wbio import atomic_open
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mamey.domain_reference import CAT_ORDER, build_reference_rows, categorize, is_curated


def _merge_packages(package_dirs: list[str]) -> list[dict]:
    """Union per-package reference rows; n_bgcs sums across packages, n_packages counts them."""
    agg: dict[str, dict] = {}
    pkgcount: dict[str, set] = defaultdict(set)
    for pkg in package_dirs:
        for row in build_reference_rows(pkg):
            dom = row["domain"]
            e = agg.setdefault(dom, dict(row, n_bgcs=0))
            e["n_bgcs"] = int(e["n_bgcs"]) + int(row["n_bgcs"])
            if not e.get("pfam_acc") and row.get("pfam_acc"):
                e["pfam_acc"] = row["pfam_acc"]
            if not e.get("antismash_desc") and row.get("antismash_desc"):
                e["antismash_desc"] = row["antismash_desc"]
            pkgcount[dom].add(pkg)
    rows = []
    for dom, e in agg.items():
        # re-categorize from the merged description (deterministic, order-independent)
        cat, ctx = categorize(dom, e.get("antismash_desc", ""))
        e["category"], e["context"], e["curated"] = cat, ctx, int(is_curated(dom))
        e["n_packages"] = len(pkgcount[dom])
        rows.append(e)
    rows.sort(key=lambda x: (CAT_ORDER.index(x["category"]) if x["category"] in CAT_ORDER else 99,
                             -int(x["n_bgcs"]), x["domain"]))
    return rows


FIELDS = ["domain", "pfam_acc", "category", "context", "n_bgcs", "n_packages",
          "antismash_desc", "curated"]


def write_tsv(rows: list[dict], out_dir: str) -> str:
    path = os.path.join(out_dir, "domain_reference.tsv")
    # v9.7.374 fix: was a bare open(path,'w') -- writes straight into the sealed package dir by
    # default (`--out` optional, defaults to the first package dir). atomic_open (tools/_wbio.py)
    # is the same tmp-sibling+os.replace helper used elsewhere in this codebase, exposed as a
    # context manager so the rest of this function's write logic is unchanged.
    with atomic_open(path, "w", encoding="utf-8", newline="") as fh:
        w = _SafeDictWriter(fh, fieldnames=FIELDS, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})
    return path


def write_md(rows: list[dict], out_dir: str, n_pkgs: int) -> str:
    by_cat: dict[str, list] = defaultdict(list)
    for r in rows:
        by_cat[r["category"]].append(r)
    path = os.path.join(out_dir, "domain_reference.md")
    # v9.7.374 fix: same non-atomic-write gap as write_tsv() above, same fix.
    with atomic_open(path, "w", encoding="utf-8") as fh:
        fh.write(f"# Domain reference — {len(rows)} unique domains across {n_pkgs} package(s)\n\n")
        fh.write("Each domain's **function** written once (the Mode-B substrate). Category is a "
                 "deterministic role bucket; context is a curated one-liner for core biosynthetic "
                 "domains, otherwise the antiSMASH description. Counts = how many BGCs carry the "
                 "domain. **Function only — never a claim about the product of any given BGC.**\n\n")
        fh.write("| category | n_domains | example domains |\n|---|---:|---|\n")
        for cat in CAT_ORDER:
            if cat in by_cat:
                ex = ", ".join(d["domain"] for d in by_cat[cat][:5])
                fh.write(f"| {cat} | {len(by_cat[cat])} | {ex} |\n")
        fh.write("\n")
        for cat in CAT_ORDER:
            if cat not in by_cat:
                continue
            fh.write(f"## {cat} ({len(by_cat[cat])})\n\n")
            fh.write("| domain | Pfam/acc | BGCs | context |\n|---|---|---:|---|\n")
            for d in by_cat[cat]:
                ctx = (d.get("context") or "").replace("|", "\\|")
                fh.write(f"| `{d['domain']}` | {d.get('pfam_acc','')} | {d.get('n_bgcs',0)} | {ctx} |\n")
            fh.write("\n")
    return path


def _reader_out_dir(out, package_dir, suffix):
    """v9.7.409 (AUDIT_cli_code_bugs #5): a read-only reader must never write INSIDE the package
    it reads — an untracked file there makes `mamey validate` fail checksum_integrity. Default
    output to a SIBLING dir OUTSIDE the package; refuse an explicit --out that resolves inside it
    (mirrors mamey/activity_predictions.resolve_output_dir). Raises ValueError on an inside path."""
    pkg = os.path.abspath(package_dir)
    target = os.path.abspath(out) if out else os.path.join(
        os.path.dirname(pkg), os.path.basename(pkg) + suffix)
    if target == pkg or (target + os.sep).startswith(pkg + os.sep):
        raise ValueError(f"reader output must be OUTSIDE the sealed package ({pkg}); "
                         f"pass --out <a directory outside the package>")
    return target


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build the Mode-B domain reference dictionary from sealed package(s)")
    ap.add_argument("--package", action="append", required=True,
                    help="path to a sealed Mamey package directory (repeatable)")
    ap.add_argument("--out", default=None, help="output dir (default: first package dir)")
    a = ap.parse_args(argv)
    for pkg in a.package:
        if not os.path.isdir(pkg):
            ap.error(f"not a directory: {pkg}")
    try:
        out_dir = _reader_out_dir(a.out, a.package[0], "_domain_reference")
    except ValueError as _e:
        ap.error(str(_e))
    os.makedirs(out_dir, exist_ok=True)
    rows = _merge_packages(a.package)
    if not rows:
        emit("no domains found (package(s) carry no *_domains.csv / *_3_antismash_hmm.csv)", file=sys.stderr)
        return 1
    tsv = write_tsv(rows, out_dir)
    write_md(rows, out_dir, len(a.package))
    ncur = sum(1 for r in rows if r.get("curated"))
    cats = len({r["category"] for r in rows})
    emit(f"{len(rows)} domains ({ncur} curated core, {cats} categories) -> {tsv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
