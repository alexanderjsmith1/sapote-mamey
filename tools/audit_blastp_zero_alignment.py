#!/usr/bin/env python3
"""audit_blastp_zero_alignment.py — find fabricated tested-negatives in BLASTp evidence.

v9.7.250. Companion to the `_zero_alignment_batch` guard in `mamey/blastp_online.py`.

THE DEFECT. `reconcile()` maps an empty `hit_def` to `NO_HIT`. If a whole submission batch returns
zero alignments -- observed 3x on real nr at `--batch-size 30` (AS-XXX BGC034) -- all of its genes are
written to `<BGC>_online_blastp.csv` as tested-negatives, indistinguishable from a gene that was
genuinely queried and has no nr homolog. Those rows feed `conservation_median_id`, the input to
`NOVELTY_CONTRADICTION`. The guard stops new ones. This finds the old ones.

TWO MODES, and the difference is the whole point.

  --overlay <dir|csv>   Heuristic. An overlay CSV records `agreement=NO_HIT` and nothing else: it
                        CANNOT distinguish "queried, no homolog" from "never came back". So this mode
                        looks for the *signature*: a run of >= --min-run consecutive NO_HIT rows, in
                        submission order, sitting next to genes at >= --near-id % identity. Suggestive,
                        never conclusive. Reports SUSPECT, not GUILTY.

  --xml <dir>           Authoritative, where the raw NCBI BLAST XML2 survives. XML2 emits one <Search>
                        per query even when that query has no hits, so a tested-negative is *recorded*.
                        A batch whose every <Search> has zero <Hit> is a zero-alignment batch. A file
                        with some zero-hit and some hit-bearing searches is a normal result.

                        Measured on the 36-RID AS-XXX archive (2026-07-09): 479 queries, 55 with zero
                        hits, spread across 28 of 36 RIDs -- and ZERO all-zero batches. Those 55 are
                        genuine tested-negatives, and NONE of them appear in the sibling HitTable CSVs.
                        That is the ingest gap: the HitTable path cannot mark a tested-negative at all.

Exit 0 = nothing found. Exit 1 = suspects/zero-alignment batches found. Exit 2 = bad input.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse
import csv
import pathlib
import sys
import xml.etree.ElementTree as ET

NS = "{http://www.ncbi.nlm.nih.gov}"


# --------------------------------------------------------------------------- XML2 (authoritative)
def audit_xml(path: pathlib.Path) -> dict:
    """Return {'queries': n, 'zero_hit': n, 'all_zero': bool} for one BLAST XML2 file."""
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        return {"error": f"parse failed: {exc}"}
    searches = root.findall(f".//{NS}Search")
    if not searches:
        return {"error": "no <Search> elements — not BLAST XML2?"}
    zero = sum(1 for s in searches if not s.findall(f".//{NS}Hit"))
    return {"queries": len(searches), "zero_hit": zero,
            "all_zero": len(searches) >= 2 and zero == len(searches)}


# ------------------------------------------------------------------------- overlay (heuristic)
def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def audit_overlay(path: pathlib.Path, min_run: int, near_id: float) -> dict:
    """Longest run of consecutive NO_HIT rows, and the identity of the flanking hits."""
    with open(path, newline="", encoding="utf-8", errors="replace") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        return {"error": "empty overlay"}

    def is_nohit(r):
        if (r.get("agreement") or "").strip().upper() == "NO_HIT":
            return True
        return not (r.get("blastp_top_def") or "").strip()

    best, run, start = 0, 0, None
    best_start = None
    for i, r in enumerate(rows):
        if is_nohit(r):
            if run == 0:
                start = i
            run += 1
            if run > best:
                best, best_start = run, start
        else:
            run = 0

    flank = []
    if best_start is not None:
        for j in (best_start - 1, best_start + best):
            if 0 <= j < len(rows):
                pid = _f(rows[j].get("pct_identity"))
                if pid is not None:
                    flank.append(pid)

    suspect = best >= min_run and any(p >= near_id for p in flank)
    return {"rows": len(rows), "no_hit": sum(1 for r in rows if is_nohit(r)),
            "longest_run": best, "flank_pct_id": flank, "suspect": suspect}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--xml", help="dir of *-Alignment.xml (BLAST XML2) — authoritative")
    g.add_argument("--overlay", help="dir of *_online_blastp.csv, or one CSV — heuristic")
    ap.add_argument("--min-run", type=int, default=10,
                    help="consecutive NO_HIT rows before a run is suspicious (default 10 = SAFE_BATCH)")
    ap.add_argument("--near-id", type=float, default=90.0,
                    help="a flanking gene at >= this %%identity makes a run suspicious (default 90)")
    a = ap.parse_args()

    if a.xml:
        root = pathlib.Path(a.xml)
        if not root.exists():
            emit(f"INPUT_NOT_FOUND: --xml {root}", file=sys.stderr)
            return 2
        files = sorted(root.glob("*.xml")) if root.is_dir() else [root]
        if not files:
            emit(f"no *.xml under {root}", file=sys.stderr)
            return 2
        bad, errored, tot_q, tot_z = [], [], 0, 0
        for f in files:
            r = audit_xml(f)
            if "error" in r:
                emit(f"  {f.name}: {r['error']}", file=sys.stderr)
                errored.append(f.name)  # v9.7.409 A9 (G1): an unreadable file is NOT a tested-negative
                continue
            tot_q += r["queries"]; tot_z += r["zero_hit"]
            if r["all_zero"]:
                bad.append((f.name, r["queries"]))
        _partial = (f"\n{len(errored)} file(s) UNREADABLE -- audit is PARTIAL, not a clean bill: {', '.join(errored)}"
                    if errored else "")
        emit(f"XML2 audit: {len(files) - len(errored)}/{len(files)} file(s) parsed, {tot_q} queries, {tot_z} with zero hits.{_partial}")
        if bad:
            emit("\nZERO-ALIGNMENT BATCHES (every query returned nothing) — these are NOT negatives:")
            for n, q in bad:
                emit(f"  {n}: all {q} queries returned zero alignments")
            emit("\nRe-run these batches at --batch-size 10 before trusting any novelty read.")
            return 1
        emit(*(("PARTIAL AUDIT: some XML did not parse; NOT asserting genuine tested-negatives (exit 3).",)
               if errored else
               ("No all-zero batches. Zero-hit queries above are genuine tested-negatives —",
                "note they are recorded in XML2 and ABSENT from the sibling HitTable CSVs.")),
             sep="\n", file=sys.stderr if errored else sys.stdout)
        return 3 if errored else 0  # v9.7.409 A9: 3 = PARTIAL, distinct from 1 (bad batches) and 2 (no input)

    root = pathlib.Path(a.overlay)
    if not root.exists():
        emit(f"INPUT_NOT_FOUND: --overlay {root}", file=sys.stderr)
        return 2
    files = sorted(root.rglob("*_online_blastp.csv")) if root.is_dir() else [root]
    if not files:
        emit(f"no *_online_blastp.csv under {root}", file=sys.stderr)
        return 2
    suspects = []
    errored = []
    for f in files:
        r = audit_overlay(f, a.min_run, a.near_id)
        if "error" in r:
            emit(f"  {f.name}: {r['error']}", file=sys.stderr)
            errored.append(f.name)  # v9.7.409 A9: same PARTIAL rule as the XML branch
            continue
        tag = "SUSPECT" if r["suspect"] else "ok"
        emit(f"  [{tag:>7}] {f.name}: {r['no_hit']}/{r['rows']} NO_HIT, "
              f"longest run {r['longest_run']}, flanking %id {r['flank_pct_id']}")
        if r["suspect"]:
            suspects.append(f.name)
    if suspects:
        emit(f"\n{len(suspects)} overlay(s) carry the zero-alignment signature. HEURISTIC ONLY: an "
              f"overlay cannot distinguish 'never returned' from 'tested, no homolog'. Confirm against "
              f"the raw XML2 (--xml) or re-run at --batch-size 10.")
        return 1
    emit(f"\nPARTIAL AUDIT: {len(errored)} overlay(s) unreadable; NOT asserting a clean bill (exit 3)." if errored
         else "\nNo overlay carries the signature.", file=sys.stderr if errored else sys.stdout)
    return 3 if errored else 0  # v9.7.409 A9


if __name__ == "__main__":
    raise SystemExit(main())
