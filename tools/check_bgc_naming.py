#!/usr/bin/env python3
"""check_bgc_naming.py — portable enforcement of the AS-strain BGC node-naming rule.

GOVERNANCE (the Developer or User HARD RULE, 2026-08-06): for AS-strains, every BGC-scoped file and
document must carry the antiSMASH node/contig token (e.g. NODE_13...region001), never a
bare sequential id like "BGC016" on its own. Each BGC should also live in its own folder,
not as floating files. Bare "BGCnn" is a wrong-attribution risk because the sequential id
is positional (parse order), while the NODE.rNNN token is the stable, contig-anchored key.

This checker is the PORTABLE enforcer (per the portable-rules-principle): it is stdlib-only,
runs anywhere / in CI / from `validate`, and does NOT depend on Claude Code hooks. The
`.claude/hooks/bgc_node_name_guard.sh` convenience net just mirrors this logic.

Two capabilities:

  scan    Walk a tree and flag AS-strain BGC files whose basename has a bare BGCnn token
          with no node/contig token. Exit non-zero if any violation is found (CI-friendly).

  crosswalk
          Read a sealed antiSMASH package inventory (`*_2_inventory.csv`) and emit the
          authoritative BGCnn -> NODE.rNNN crosswalk for one strain. This is the rename key:
          it is derived from the antiSMASH node/region columns, so it is ENGINE-INDEPENDENT
          (the mapping is fixed at parse time and does not move with the Mamey engine version).

Examples
--------
  python tools/check_bgc_naming.py scan "strain_data" --strains AS-XXX
  python tools/check_bgc_naming.py scan "strain_data" --tsv violations.tsv
  python tools/check_bgc_naming.py crosswalk AS-XXX_2_inventory.csv --out AS-XXX_crosswalk.tsv
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
import re
import sys

__version__ = "1.0.0"

# A bare sequential BGC id: BGC016, BGC_16, bgc-3, etc.
BGC_RE = re.compile(r"BGC[_-]?\d{1,4}", re.IGNORECASE)

# A full node / contig / accession token that anchors the id to a real sequence.
# Region is deliberately separate: region001 alone is not a sequence anchor.
NODE_ANCHOR_RE = re.compile(
    r"NODE[_-]?\d+_length_\d+_cov_[0-9.]+"
    r"|contig[_-]?\d+"
    r"|scaffold[_-]?\d+"
    r"|tig0*\d+"
    r"|N[CZ]_[0-9]+"        # RefSeq
    r"|CP\d{5,}",           # GenBank complete
    re.IGNORECASE,
)
REGION_RE = re.compile(r"region0*\d+", re.IGNORECASE)
BASENAME_STRAIN_RE = re.compile(r"AS-\d+", re.IGNORECASE)

# An AS-strain folder in the path (AS-XXX, AS-XXX, ...). Governance applies to AS strains.
AS_STRAIN_RE = re.compile(r"(^|[/\\])AS-\d+([/\\]|$)")

# Directories we never descend into: raw antiSMASH output legitimately uses upstream names,
# and build/cache dirs are noise.
SKIP_DIRS = {
    "antiSMASH", "antismash", "__pycache__", ".git", "raw", "raw_json",
    "blastp_raw", "source_locator_evidence", ".DS_Store", "knownclusterblast",
    "node_modules",
}


def _basename_violates(name: str) -> bool:
    """True when a BGC basename lacks any required exact-locus identity field."""
    if not BGC_RE.search(name):
        return False
    return not (BASENAME_STRAIN_RE.search(name)
                and NODE_ANCHOR_RE.search(name)
                and REGION_RE.search(name))


def scan(root: str, strains: list[str] | None, tsv_out: str | None) -> int:
    violations: list[tuple[str, str]] = []  # (strain, path)
    want = set(strains) if strains else None
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        if not AS_STRAIN_RE.search(dirpath):
            # still allow files whose OWN path segment names an AS strain
            pass
        # Determine the AS strain this path belongs to, if any.
        # BC2-CASE-01 (v9.7.395): this used a bare `re.search(r"AS-\d+", dirpath)` with no
        # IGNORECASE, while BASENAME_STRAIN_RE (used two lines above for the actual per-basename
        # governance check) and crosswalk()'s own strain lookup are both case-insensitive (the
        # latter additionally normalizes with .upper()). A lowercase/mixed-case strain directory
        # (e.g. "as-nn") failed this match, so `strain` came back None and the whole subtree hit
        # `continue` below — every BGC-naming violation under that directory went completely
        # unscanned, and `scan()` printed "0 violation(s) ... exit code 0" (a clean CI pass) for a
        # tree that actually contained a bare-BGCnn governance violation. Reused the already-
        # case-insensitive BASENAME_STRAIN_RE and normalized to uppercase, matching crosswalk()'s
        # convention, so --strains filtering and grouping are also case-consistent.
        m = BASENAME_STRAIN_RE.search(dirpath)
        strain = m.group(0).upper() if m else None
        if strain is None:
            continue
        if want is not None and strain not in want:
            continue
        # check directory names too (folder-per-BGC rule: a BGC dir must be node-named)
        for d in dirnames:
            if _basename_violates(d):
                violations.append((strain, os.path.join(dirpath, d) + os.sep))
        for f in filenames:
            if _basename_violates(f):
                violations.append((strain, os.path.join(dirpath, f)))

    violations.sort()
    if tsv_out:
        with open(tsv_out, "w", newline="", encoding="utf-8") as fh:
            w = _SafeWriter(fh, delimiter="\t")
            w.writerow(["strain", "path"])
            w.writerows(violations)
    by_strain: dict[str, int] = {}
    for s, _ in violations:
        by_strain[s] = by_strain.get(s, 0) + 1
    emit(f"BGC node-naming scan: {len(violations)} violation(s) "
          f"across {len(by_strain)} strain(s) under {root!r}")
    for s in sorted(by_strain, key=lambda k: -by_strain[k]):
        emit(f"  {s}: {by_strain[s]}")
    if tsv_out:
        emit(f"  wrote {tsv_out}")
    if violations and not tsv_out:
        for s, p in violations[:20]:
            emit(f"    {s}\t{p}")
        if len(violations) > 20:
            emit(f"    ... and {len(violations) - 20} more (use --tsv for the full list)")
    # Exit non-zero on any violation so this fails a CI / validate step.
    return 1 if violations else 0


def _canonical_token(node_id: str, region: str) -> str:
    """Build the NODE.rNNN token from inventory columns.

    node_id like 'NODE_13_length_178295_cov_71'; region like '1' or 'region001'.
    Emits e.g. 'NODE_13_length_178295_cov_71.region001'.
    """
    node = node_id.strip()
    r = region.strip()
    rm = re.search(r"(\d+)", r)
    rnum = int(rm.group(1)) if rm else 0
    return f"{node}.region{rnum:03d}"


def crosswalk(inventory_csv: str, out: str | None) -> int:
    rows: list[tuple[str, str, str, str]] = []
    with open(inventory_csv, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        cols = {c.lower(): c for c in (reader.fieldnames or [])}
        bgc_col = cols.get("bgc_id")
        node_col = cols.get("node_id")
        region_col = cols.get("region") or cols.get("antismash_region")
        if not (bgc_col and node_col and region_col):
            emit("ERROR: inventory is missing BGC_ID / Node_ID / Region columns; "
                  f"found: {reader.fieldnames}", file=sys.stderr)
            return 2
        for row in reader:
            bgc = (row.get(bgc_col) or "").strip()
            node = (row.get(node_col) or "").strip()
            region = (row.get(region_col) or "").strip()
            if not bgc:
                continue
            token = _canonical_token(node, region)
            strain_match = re.search(r"AS-\d+", inventory_csv, re.IGNORECASE)
            strain = strain_match.group(0).upper() if strain_match else ""
            region_token = token.rsplit(".", 1)[-1]
            safe = (f"{strain}__{node}__{region_token}__{bgc}"
                    if strain else f"{node}__{region_token}__{bgc}")
            rows.append((strain, bgc, token, safe))

    if out:
        with open(out, "w", newline="", encoding="utf-8") as fh:
            w = _SafeWriter(fh, delimiter="\t")
            w.writerow(["strain", "legacy_bgc_id", "canonical_node_token",
                        "canonical_exact_locus_prefix"])
            w.writerows(rows)
    emit(f"BGCnn -> NODE.rNNN crosswalk: {len(rows)} BGC(s) from {os.path.basename(inventory_csv)}", "  (engine-independent: derived from antiSMASH node/region, not from scoring)", sep="\n")
    for strain, bgc, token, safe in rows[:8]:
        emit(f"    {strain or '?'} / {token} / {bgc}\t->\t{safe}")
    if len(rows) > 8:
        emit(f"    ... and {len(rows) - 8} more")
    if out:
        emit(f"  wrote {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("scan", help="flag AS-strain BGC files missing a node token")
    ps.add_argument("root", help="directory to scan (e.g. 'strain_data')")
    ps.add_argument("--strains", nargs="*", default=None,
                    help="limit to these AS strains (e.g. AS-XXX AS-XXX)")
    ps.add_argument("--tsv", dest="tsv", default=None, help="write full violation list here")

    pc = sub.add_parser("crosswalk", help="emit BGCnn -> NODE.rNNN from a sealed inventory")
    pc.add_argument("inventory_csv", help="a sealed package's *_2_inventory.csv")
    pc.add_argument("--out", default=None, help="write the crosswalk TSV here")

    args = ap.parse_args(argv)
    if args.cmd == "scan":
        return scan(args.root, args.strains, args.tsv)
    if args.cmd == "crosswalk":
        return crosswalk(args.inventory_csv, args.out)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
