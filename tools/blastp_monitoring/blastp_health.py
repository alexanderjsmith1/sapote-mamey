#!/usr/bin/env python3
"""blastp_health.py (VGP, 2026-08-21) — GROUND-TRUTH health of the BLASTp crawl.

Root-cause fix for the 2026-08-21 incident: the old monitoring read ONLY the ledger
(`_ledger.csv`, status=='fetched'). A *submit failure* never creates a fetched row — it is logged to
`_run.log` — so 90 minutes of "submit failed ... backing off 300s" across 42 lanes showed up as a
harmless FLAT LINE in the throughput plot. Absence-of-fetches looked identical to active-failure.

This tool reads ALL THREE layers and reports the WORST, never the rosiest:
  1. _run.log  — per LIVE lane, count recent submit-failures / backoff / UNKNOWN / poll ERROR.
                 THROTTLE shows up here FIRST and LOUDEST. (alarm on errors PRESENT)
  2. results/  — the actual output files; open the newest and confirm it holds real hits
                 (a subject accession + a %identity). "fetched" can never silently mean empty/garbage.
  3. _ledger   — last successful fetch time + today's fetched count (the throughput signal).

Canonical output path (documented here so no session hunts for it again):
  Blastp RESULTS/_NR_CLUSTER_RID_GAP_<strain>/results/<strain>/_gap/_gap_blastp_top10_clustered.csv
  (nr lanes: _NR_RID_GAP_<strain>/results/.../_gap_blastp_top10.csv ; raw XML in <lane>/xml/)

Verdicts: HEALTHY · IDLE (no live lanes) · DEGRADED (some errors, still fetching) ·
          THROTTLED (many live lanes stuck in submit-failure backoff) ·
          STALLED (live lanes, no fetch in >STALL_MIN AND errors present).

Run: python3 "tools/blastp_monitoring/blastp_health.py"
"""
import csv
import datetime
import glob
import os
import re
import subprocess
import sys

ROOT = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd())
BR = os.path.join(ROOT, "Blastp RESULTS")
STALL_MIN = 30          # no fetch for this long, with live lanes, = trouble
RECENT_MIN = 30         # window for counting run.log errors
# BC2-398: blastp_last_returns.py's own header docstring states it "Mirrors blastp_health.py's
# process/error anchoring" — verified live it did not (and this pattern was missing the sibling's
# bare "rc=(?:16|56|6|7|18)" and "throttl" signals in the other direction). Union of both — keep
# in sync with the sibling copy in blastp_last_returns.py.
ERR_RE = re.compile(
    r"submit failed|backing off|UNKNOWN|poll ERROR|curl rc=|expired"
    r"|rc=(?:16|56|6|7|18)|throttl",
    re.I,
)
TS_RE = re.compile(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]")
ROWS_RE = re.compile(r"(\d+)\s*row")


def live_lanes():
    """RID_BASE dir-names for EVERY running runner process — default-aware.

    A runner started without a RID_BASE= env uses the runner's own default ('_NR_RID'). An earlier
    version only matched lines containing 'RID_BASE=', so it reported 0 live lanes while a
    caffeinate-wrapped `nr_rid_runner.py run --hours 48` on the DEFAULT queue was actively fetching —
    the same blind spot (trusting a narrow signal) this whole tool exists to kill. Now: count every
    nr_rid_runner process and resolve its base (explicit env, else the default).
    """
    ps = subprocess.run(["ps", "-eo", "command"], capture_output=True, text=True).stdout
    bases = set()
    total = 0
    for line in ps.splitlines():
        if "nr_rid_runner.py" not in line or "grep" in line:
            continue
        total += 1
        if "RID_BASE=" in line:
            bases.add(line.split("RID_BASE=")[1].split()[0])
        else:
            bases.add("_NR_RID")  # runner default when no env is set
    return bases, total


def recent_errors(logpath, now):
    """count ERR_RE lines in the last RECENT_MIN minutes of a _run.log."""
    if not os.path.exists(logpath):
        return 0, None
    n = 0
    last = None
    try:
        lines = open(logpath, errors="ignore").read().splitlines()[-400:]
    except Exception:
        return 0, None
    for ln in lines:
        m = TS_RE.search(ln)
        if not m:
            continue
        try:
            t = datetime.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
        except Exception:
            continue
        if (now - t).total_seconds() <= RECENT_MIN * 60 and ERR_RE.search(ln):
            n += 1
            last = ln.strip()
    return n, last


def newest_result_hit():
    """open the newest result CSV; return (path, n_rows, sample) or (None,0,None)."""
    files = glob.glob(os.path.join(BR, "_NR_*RID*", "results", "*", "_gap",
                                   "_gap_blastp_top10*.csv"))
    if not files:
        return None, 0, None
    f = max(files, key=os.path.getmtime)
    try:
        rows = list(csv.DictReader(open(f)))
    except Exception:
        return f, 0, None
    sample = None
    if rows:
        r = rows[0]
        def g(*names):
            for k in r:
                if k.lower() in names:
                    return r[k]
            return "?"
        sample = (f"{g('subject_acc','sacc')} id%={g('pct_identity','pident')} "
                  f"{str(g('subject_def','stitle','subject_title'))[:45]}")
    return f, len(rows), sample


def main():
    now = datetime.datetime.now()
    live, nproc = live_lanes()
    # per-live-lane run.log errors
    stuck = 0
    err_total = 0
    example = None
    for base in live:
        n, last = recent_errors(os.path.join(BR, base, "_run.log"), now)
        if n:
            err_total += n
            if n >= 3:
                stuck += 1
                example = example or last
    # ledger: last fetch + today's fetched
    last_fetch = None
    fetched_today = 0
    for led in glob.glob(os.path.join(BR, "_NR_*RID*", "_ledger.csv")):
        try:
            rows = list(csv.DictReader(open(led)))
        except Exception:
            continue
        for r in rows:
            if r.get("status") == "fetched" and r.get("fetch_iso"):
                try:
                    t = datetime.datetime.strptime(r["fetch_iso"][:19], "%Y-%m-%d %H:%M:%S")
                except Exception:
                    continue
                if last_fetch is None or t > last_fetch:
                    last_fetch = t
                if t.date() == now.date():
                    fetched_today += 1
    fetch_age = int((now - last_fetch).total_seconds() / 60) if last_fetch else None
    # results ground-truth
    rf, nrows, sample = newest_result_hit()

    # verdict — worst of the three layers
    if not live:
        verdict = "IDLE (no live lanes)"
    elif stuck >= max(2, len(live) // 3):
        verdict = f"THROTTLED ({stuck}/{len(live)} live lanes stuck in submit-failure backoff)"
    elif fetch_age is not None and fetch_age > STALL_MIN and err_total > 0:
        verdict = f"STALLED (no fetch {fetch_age}m + {err_total} recent errors)"
    elif err_total > 0:
        verdict = f"DEGRADED ({err_total} recent errors, still fetching)"
    else:
        verdict = "HEALTHY"

    print('=' * 60, f"BLASTp HEALTH @ {now.strftime('%Y-%m-%d %H:%M')}   ->  {verdict}", '=' * 60, f'live lanes            : {len(live)}  ({nproc} runner processes)', f'lanes stuck (>=3 err) : {stuck}   recent errors (<{RECENT_MIN}m): {err_total}', sep="\n")
    if example:
        print(f"  example error       : {example[:90]}")
    print(f"last successful fetch  : {last_fetch.strftime('%H:%M') if last_fetch else 'none'}"
          f" ({fetch_age}m ago)   fetched today: {fetched_today}")
    if rf:
        print(f'newest result file     : {os.path.relpath(rf, BR)}', f'  hit rows={nrows}  sample: {sample}', sep="\n")
    else:
        print("newest result file     : NONE FOUND")
    print("=" * 60)
    # nonzero exit if not healthy/idle, so it can gate a restart
    return 0 if verdict.startswith(("HEALTHY", "IDLE")) else 2


if __name__ == "__main__":
    sys.exit(main())
