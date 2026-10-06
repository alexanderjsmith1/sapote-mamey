#!/usr/bin/env python3
"""blastp_health.py (2026-08-21) — GROUND-TRUTH health of the BLASTp crawl.

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

Per-lane table (v9.7.443), under the verdict: for every live lane, and with --all every gap lane,
the RIDs in flight, how many are HELD (older than --hold-after, default 1 h) and the oldest age,
fetched in the last hour, and errors in the last hour split by type with the commonest curl rc.
A lane is BLOCKED when its RIDs are all held and fill its slots, so it can submit nothing new.
--idle lists stopped gap lanes with no held RIDs and work left: the answer to "which lane next".
A lane is live if its `_runner.pid` names a running process (the bundle runner writes one), or if
a runner's command line names its RID_BASE.

Run: python3 "tools/blastp_monitoring/blastp_health.py" [--all] [--idle]
"""
import argparse
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
# 398: blastp_last_returns.py's own header docstring states it "Mirrors blastp_health.py's
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


ERR_TYPES = ("submit failed", "submit ERROR", "poll ERROR", "fetch ERROR")
RC_RE = re.compile(r"curl rc=(\d+)")
GAP_LANE_RE = re.compile(r"^_STRAINGAP_SINGLE_CLNR_GAP_AS(\d+)$")


def _pid_alive(base_dir):
    try:
        pid = int(open(os.path.join(base_dir, "_runner.pid")).read().strip())
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def _ts(s):
    try:
        return datetime.datetime.strptime((s or "")[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def lane_row(base, now, live, hold_after, max_inflight, max_held, bundle_runner):
    """One lane's slot and error picture from its ledger, query tree and _run.log."""
    d = os.path.join(BR, base)
    try:
        rows = list(csv.DictReader(open(os.path.join(d, "_ledger.csv"), newline="")))
    except OSError:
        rows = []
    by_file = {r.get("file", ""): r for r in rows}
    ages = sorted(((now - t).total_seconds() for r in rows if r.get("status") == "submitted"
                   for t in [_ts(r.get("submit_iso"))] if t), reverse=True)
    held = [a for a in ages if a >= hold_after]
    fetched_1h = sum(1 for r in rows if r.get("status") == "fetched"
                     and (_ts(r.get("fetch_iso")) or datetime.datetime.min) >= now - datetime.timedelta(hours=1))
    runnable = None
    m = GAP_LANE_RE.match(base)
    if m:
        q = os.path.join(BR, f"_QUERIES_GAP_AS-{m.group(1)}_K")
        if os.path.isdir(q):
            skip = {"fetched", "submitted", "submit_failed_parked", "unsure"}
            runnable = sum(1 for f in glob.glob(os.path.join(q, "**", "*.faa"), recursive=True)
                           if by_file.get(os.path.relpath(f, q), {}).get("status") not in skip)
    errs = dict.fromkeys(ERR_TYPES, 0)
    rcs = {}
    try:
        tail = open(os.path.join(d, "_run.log"), errors="ignore").read().splitlines()[-2000:]
    except OSError:
        tail = []
    for ln in tail:
        mt = TS_RE.search(ln)
        if not mt or (now - _ts(mt.group(1))).total_seconds() > 3600:
            continue
        for kind in ERR_TYPES:
            if kind in ln:
                errs[kind] += 1
                rc = RC_RE.search(ln)
                if rc:
                    rcs[rc.group(1)] = rcs.get(rc.group(1), 0) + 1
                break
    # The bundle runner frees a slot once a RID is held and stops at --max-held; the older
    # workspace runner lets held RIDs fill --max-inflight.
    if bundle_runner:
        blocked = len(held) >= max_held
    else:
        blocked = bool(ages) and len(held) == len(ages) and len(ages) >= max_inflight
    handed_off = os.path.exists(os.path.join(d, "_HANDOFF_OUT.txt"))
    return dict(base=base, live=live, handed_off=handed_off, in_flight=len(ages), held=len(held),
                oldest_h=(ages[0] / 3600 if ages else None), fetched_1h=fetched_1h,
                runnable=runnable, errs=errs, rcs=rcs, blocked=blocked)


def _runner_flags():
    """(max_inflight, max_held, bundle_runner) from the first runner command line, with defaults."""
    ps = subprocess.run(["ps", "-eo", "command"], capture_output=True, text=True).stdout
    for line in ps.splitlines():
        if "nr_rid_runner.py" in line and " run" in line:
            mi = re.search(r"--max-inflight[= ](\d+)", line)
            mh = re.search(r"--max-held[= ](\d+)", line)
            return (int(mi.group(1)) if mi else 2, int(mh.group(1)) if mh else 4,
                    "blastp_crawl/nr_rid_runner.py" in line)
    return 2, 4, True


def print_lane_table(rows):
    print(f"{'lane':<40} {'live':>4} {'runnable':>8} {'in flight':>9} {'held (oldest)':>14} "
          f"{'fetched 1h':>10}  errors 1h (submit failed/submit ERROR/poll/fetch; top rc)")
    for r in rows:
        oldest = f"{r['held']} ({r['oldest_h']:.1f} h)" if r["oldest_h"] is not None else "0"
        rc = max(r["rcs"], key=r["rcs"].get) if r["rcs"] else "-"
        e = r["errs"]
        print(f"{r['base']:<40} {'yes' if r['live'] else ('out' if r['handed_off'] else 'no'):>4} "
              f"{'-' if r['runnable'] is None else r['runnable']:>8} {r['in_flight']:>9} {oldest:>14} "
              f"{r['fetched_1h']:>10}  {e['submit failed']}/{e['submit ERROR']}/{e['poll ERROR']}/"
              f"{e['fetch ERROR']}; rc {rc}" + ("   BLOCKED" if r["blocked"] else ""))
    polls = sum(r["errs"]["poll ERROR"] for r in rows)
    total = sum(sum(r["errs"].values()) for r in rows)
    lanes_with_polls = sum(1 for r in rows if r["errs"]["poll ERROR"])
    if total >= 10 and polls >= 0.6 * total and lanes_with_polls >= 2:
        print("Errors are mostly failed status checks across lanes: check the local network, and "
              "whether NCBI is slow for everyone, before stopping lanes.")


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
    files = glob.glob(os.path.join(BR, "*", "results", "*", "_gap",
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
    ap = argparse.ArgumentParser(description="Ground-truth health of the BLASTp crawl.")
    ap.add_argument("--all", action="store_true", help="table every gap lane, not only live ones")
    ap.add_argument("--idle", action="store_true",
                    help="list stopped gap lanes with no held RIDs and work left (which lane next)")
    ap.add_argument("--hold-after", type=float, default=3600.0,
                    help="seconds after which a waiting RID counts as held (default 1 h)")
    a = ap.parse_args()
    now = datetime.datetime.now()
    live, nproc = live_lanes()
    live |= {os.path.basename(os.path.dirname(p))
             for p in glob.glob(os.path.join(BR, "*", "_runner.pid")) if _pid_alive(os.path.dirname(p))}
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
    for led in glob.glob(os.path.join(BR, "*", "_ledger.csv")):
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
    max_inflight, max_held, bundle_runner = _runner_flags()
    bases = sorted(b for b in live if os.path.isdir(os.path.join(BR, b)))
    if a.all or a.idle:
        bases = sorted(set(bases) | {"_STRAINGAP_SINGLE_CLNR_GAP_AS" + re.search(r"AS-(\d+)", q).group(1)
                                     for q in glob.glob(os.path.join(BR, "_QUERIES_GAP_AS-*_K"))})
    table = [lane_row(b, now, b in live, a.hold_after, max_inflight, max_held, bundle_runner)
             for b in bases]
    if a.idle:
        out = [r["base"] for r in table if r["handed_off"]]
        if out:
            print(f"Handed off to another machine, not listed ({len(out)}): "
                  + ", ".join(b.replace("_STRAINGAP_SINGLE_CLNR_GAP_", "") for b in out))
        table = sorted((r for r in table if not r["live"] and not r["handed_off"]
                        and r["in_flight"] == 0 and r["runnable"]),
                       key=lambda r: -r["runnable"])
        print(f"Stopped gap lanes with no RIDs out and work left ({len(table)}), most work first:")
    if table:
        print_lane_table(table)
    # nonzero exit if not healthy/idle, so it can gate a restart
    return 0 if verdict.startswith(("HEALTHY", "IDLE")) else 2


if __name__ == "__main__":
    sys.exit(main())
