#!/usr/bin/env python3
"""cohort_blastp_driver.py — drive BLASTp + overlay ingest across a scoped set of BGCs.

v9.7.240. The companion to `docs/INSTRUCTIONS_cohort_wide_blastp.md`.

Why this exists: until v9.7.239 nothing wrote `<package>/blastp_online/<BGC>_online_blastp.csv`, the file
`authored_verify` and `genome_explore` read to prefer nr over ClusterBlast. A BLASTp round that skips
`ingest-blastp --package` therefore arms nothing — days of compute, guard still disarmed. This driver
refuses to mark a BGC done unless that overlay exists on disk with populated identity + coverage.

It does not re-implement BLASTp or the ingest; it shells to the real commands and checks the real artifact.

Scoping (do not run 15,800 proteins by default):
  --tier leads     BGCs whose lead_tier is Exceptional/Strong  (the ~10% where a wrong novelty call hurts)
  --tier modular   all modular BGCs
  --tier all       everything in the tally (needs an explicit reason)
  --bgc BGC001 --bgc BGC014   explicit list, overrides --tier

Usage:
  python3 tools/cohort_blastp_driver.py --tally COHORT_BGC_FULL_TALLY.csv \\
      --strain AS-XXX --package runs/AS-XXX/package --antismash AS-XXX.zip \\
      --master master.xlsx --tier leads --database nr --batch-size 10 --plan-only
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
import json
import os
import subprocess
import sys
import time
from pathlib import Path

LEAD_TIERS = {"Exceptional", "Strong"}
OVERLAY_MIN_COLS = ("locus_tag", "pct_identity", "query_coverage")


def select_bgcs(tally: Path, strain: str, tier: str, explicit: list[str]) -> list[dict]:
    rows = [r for r in csv.DictReader(tally.open(encoding="utf-8")) if r.get("strain") == strain]
    if explicit:
        want = set(explicit)
        return [r for r in rows if r.get("bgc_id") in want]
    if tier == "leads":
        return [r for r in rows if (r.get("lead_tier") or "").strip() in LEAD_TIERS]
    if tier == "modular":
        return [r for r in rows if (r.get("assembly_locator") or "").strip()]
    return rows


def overlay_path(package: Path, bgc: str) -> Path:
    return package / "blastp_online" / f"{bgc}_online_blastp.csv"


def overlay_ok(p: Path) -> tuple[bool, str]:
    """The artifact IS the receipt. A log line is not evidence the guard is armed."""
    if not p.is_file():
        return False, "overlay missing"
    rows = list(csv.DictReader(p.open(encoding="utf-8")))
    if not rows:
        return False, "overlay empty"
    missing = [c for c in OVERLAY_MIN_COLS if not any(str(r.get(c, "")).strip() for r in rows)]
    if missing:
        return False, f"overlay has no {', '.join(missing)}"
    return True, f"{len(rows)} genes"


def run(cmd: list[str], dry: bool) -> int:
    emit("    $ " + " ".join(cmd[:6]) + (" …" if len(cmd) > 6 else ""), flush=True)
    if dry:
        return 0
    return subprocess.run(cmd).returncode


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tally", required=True, type=Path, help="COHORT_BGC_FULL_TALLY.csv")
    ap.add_argument("--strain", required=True)
    ap.add_argument("--package", required=True, type=Path, help="sealed package dir (overlay lands here)")
    ap.add_argument("--antismash", type=Path, help="antiSMASH ZIP / region GBK for blastp-online")
    ap.add_argument("--master", type=Path, help="master workbook for ingest-blastp")
    ap.add_argument("--tier", choices=["leads", "modular", "all"], default="leads")
    ap.add_argument("--bgc", action="append", default=[], help="explicit BGC id (repeatable)")
    ap.add_argument("--database", default="nr", choices=["nr", "refseq_protein", "swissprot"])
    # v9.7.250: default 30 -> 10. The .240 raise to 30 was recorded as "after empirical validation";
    # whatever that validation measured, it did not measure per-gene hit recovery against a
    # batch-size-10 control. A 30-query batch has been observed (3x, real nr) to return zero
    # alignments for every query, which the overlay then records as tested-negatives.
    ap.add_argument("--batch-size", type=int, default=10,
                    help="proteins per submission (default 10 = SAFE_BATCH; hard cap 30; "
                         ">10 warns and is guarded against zero-alignment batches)")
    ap.add_argument("--evalue", default="1e-5")
    ap.add_argument("--plan-only", action="store_true", help="print the plan + scale, run nothing")
    ap.add_argument("--skip-done", action="store_true", help="skip BGCs whose overlay already verifies")
    ap.add_argument("--ledger", type=Path, help="append a run-ledger row per BGC (record-keeping protocol)")
    a = ap.parse_args(argv)

    sel = select_bgcs(a.tally, a.strain, a.tier, a.bgc)
    if not sel:
        emit(f"no BGCs selected for {a.strain} (tier={a.tier})", file=sys.stderr)
        return 2

    emit(f"{a.strain}: {len(sel)} BGC(s) selected [tier={a.tier}, db={a.database}, batch={a.batch_size}]")
    if a.plan_only:
        emit("\n  plan (no commands run):")
        for r in sel:
            done, why = overlay_ok(overlay_path(a.package, r["bgc_id"]))
            emit(f"    {r['bgc_id']:8s} {r.get('lead_tier',''):12s} "
                  f"{r.get('assembly_locator','')[:44]:44s} {'DONE ' + why if done else 'todo'}")
        emit(f"\n  NOTE: 1 submission per {a.batch_size} proteins. EBI has no nr and is 1 job/protein — "
              f"use this NCBI path for any nr question.")
        return 0

    if not (a.antismash and a.master):
        emit("--antismash and --master are required unless --plan-only", file=sys.stderr)
        return 2

    ok, failed, skipped = [], [], []
    for r in sel:
        bgc = r["bgc_id"]
        ov = overlay_path(a.package, bgc)
        if a.skip_done and overlay_ok(ov)[0]:
            skipped.append(bgc)
            continue
        emit(f"\n  [{bgc}] {r.get('assembly_locator','')}")
        rc = run([sys.executable, "-m", "mamey.cli", "blastp-online",
                  "--package", str(a.antismash), "--bgc", bgc, "--crosswalk", str(a.package),
                  "--database", a.database, "--evalue", a.evalue,
                  "--batch-size", str(a.batch_size),
                  "--outdir", str(a.package / "bgc_blastp_panel")], dry=False)
        if rc != 0:
            failed.append((bgc, f"blastp-online rc={rc}")); continue

        hits = a.package / "bgc_blastp_panel" / f"{bgc}_online_blastp.csv"
        xml = a.package / "bgc_blastp_panel" / f"{bgc}.xml"
        cmd = [sys.executable, "-m", "mamey.cli", "ingest-blastp",
               "--master", str(a.master), "--strain", a.strain,
               "--hit-table", str(hits), "--package", str(a.package)]
        if xml.is_file():          # --xml fills blastp_top_def / blastp_organism (outfmt10 carries neither)
            cmd += ["--xml", str(xml)]
        rc = run(cmd, dry=False)
        if rc != 0:
            failed.append((bgc, f"ingest-blastp rc={rc}")); continue

        good, why = overlay_ok(ov)          # verify the ARTIFACT, not the exit code
        (ok if good else failed).append(bgc if good else (bgc, why))
        emit(f"    overlay: {'OK — ' + why if good else 'FAIL — ' + why}")

        if a.ledger:
            with a.ledger.open("a", newline="", encoding="utf-8") as fh:
                _SafeWriter(fh).writerow([time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                         a.strain, bgc, r.get("assembly_locator", ""), a.database,
                                         "PASS" if good else "FAIL", why])

    emit(f"\n  armed: {len(ok)} | failed: {len(failed)} | skipped(done): {len(skipped)}")
    for b, why in failed:
        emit(f"    FAIL {b}: {why}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
