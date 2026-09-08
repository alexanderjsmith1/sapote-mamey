#!/usr/bin/env python3
"""plot_crawl_12h_15min.py (VGP, 2026-08-21) — the standing "is blastp still moving?" plot.

Last 12 hours, 15-minute bins, ALL lanes pooled. Two panels:
  * top    — query proteins per 15-min bin, stacked nr vs ClusteredNR, with the 1/min floor line
  * bottom — cumulative within the 12 h window (rising = healthy, flat tail = stalled)

15-min bins were chosen (vs 30) because a single empty bar flags a stall ~2x sooner. Units are correct:
y = QUERY PROTEINS fetched (the '>' records in each fetched panel), NOT returned hit rows — it reuses
plot_crawl_recent.load_fetches(), the single source of truth for ledger parsing.

Also prints a one-line health check: last-fetch age, in-flight RID count, and empty-vs-hit tally for the
window (an all-lane empty spike would mean NCBI is returning nothing, distinct from a submission stall).

Run: python3 "tools/blastp_monitoring/plot_crawl_12h_15min.py"
"""
import csv
import datetime
import glob
import importlib.util
import os
import re
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd())
VGP = os.environ.get("SAPOTE_BLASTP_PLOT_DIR", os.path.join(ROOT, "blastp_plots"))
OUT = os.path.join(VGP, "crawl_plots")
BR = os.path.join(ROOT, "Blastp RESULTS")
ROWS_RE = re.compile(r"(\d+)\s*row")
HOURS = int(next((a.split("=")[1] for a in sys.argv[1:] if a.startswith("--hours=")),
                 (sys.argv[sys.argv.index("--hours") + 1] if "--hours" in sys.argv else 12)))
BINM = 15

os.chdir(ROOT)  # load_fetches uses BR relative to cwd
spec = importlib.util.spec_from_file_location("pcr", os.path.join(VGP, "plot_crawl_recent.py"))
pcr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pcr)


def live_lanes():
    """True count of live crawl lanes = the real runner python processes (NOT ledger history).
    Anchored to lines that START with the python executable, so the zsh/caffeinate wrappers that
    merely CONTAIN the invocation string are not double-counted. Mirrors blastp_health.py."""
    try:
        ps = subprocess.run(["ps", "-eo", "command"], capture_output=True, text=True).stdout
    except Exception:
        return None
    n = 0
    for line in ps.splitlines():
        if re.match(r"^([^ ]*/)?python[0-9.]*\s.*nr_rid_runner\.py run", line) and "grep" not in line:
            n += 1
    return n


def recent_errors(minutes=30):
    """Count THROTTLE errors in the last `minutes`, split from benign transient poll retries.
    Returns (throttle, transient). A `submit failed`/`backing off` line is a real NCBI throttle
    signal; an isolated `poll ERROR ... curl rc=16/18` is a transient HTTP/2 glitch the runner
    recovers from by re-polling the SAME RID (not a stall). We must not cry throttle on the latter."""
    cutoff = datetime.datetime.now() - datetime.timedelta(minutes=minutes)
    throttle_pat = re.compile(r"submit failed|backing off|throttl", re.I)
    transient_pat = re.compile(r"poll ERROR|curl rc=(?:16|56|6|7|18)", re.I)
    ts = re.compile(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]")
    throttle = transient = 0
    for lg in glob.glob(os.path.join(BR, "_NR_*RID*", "_run.log")):
        try:
            for line in open(lg, errors="ignore"):
                is_thr = throttle_pat.search(line)
                is_tra = transient_pat.search(line)
                if not (is_thr or is_tra):
                    continue
                m = ts.search(line)
                if not m:
                    continue
                try:
                    if datetime.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S") >= cutoff:
                        if is_thr:
                            throttle += 1
                        else:
                            transient += 1
                except Exception:
                    pass
        except Exception:
            continue
    return throttle, transient


def health(start, now):
    last_fetch = None
    inflight = 0
    hits = empty = 0
    today = now.strftime("%Y-%m-%d")
    for led in glob.glob(os.path.join(BR, "_NR_*RID*", "_ledger.csv")):
        try:
            rows = list(csv.DictReader(open(led)))
        except Exception:
            continue
        for r in rows:
            # only count TODAY's submitted rows as in-flight — stale rows from earlier
            # throttled waves are dead RIDs, not real in-flight work (they made the old "47").
            if r.get("status") == "submitted" and (r.get("submit_iso") or "").startswith(today):
                inflight += 1
            if r.get("status") == "fetched" and r.get("fetch_iso"):
                try:
                    t = datetime.datetime.strptime(r["fetch_iso"][:19], "%Y-%m-%d %H:%M:%S")
                except Exception:
                    continue
                if last_fetch is None or t > last_fetch:
                    last_fetch = t
                if t >= start:
                    m = ROWS_RE.search(r.get("note", "") or "")
                    if m and int(m.group(1)) > 0:
                        hits += 1
                    else:
                        empty += 1
    return last_fetch, inflight, hits, empty


def main():
    fetches = pcr.load_fetches()
    if not fetches:
        sys.exit("no fetched rows found")
    now = datetime.datetime.now()
    start = now - datetime.timedelta(hours=HOURS)
    sel = [f for f in fetches if f[0] >= start]
    nb = int(HOURS * 60 / BINM)
    edges = [start + datetime.timedelta(minutes=BINM * i) for i in range(nb + 1)]
    nr = [0] * nb
    cl = [0] * nb
    for t, n, ch, _ in sel:
        i = int((t - start).total_seconds() // (BINM * 60))
        if 0 <= i < nb:
            (cl if ch == "ClusteredNR" else nr)[i] += n
    xs = [edges[i] for i in range(nb)]
    w = BINM / 1440.0

    fig, ax = plt.subplots(2, 1, figsize=(14, 9))
    b = [0] * nb
    ax[0].bar(xs, nr, w, bottom=b, color="#1f77b4", align="edge", label="nr")
    b = [x + y for x, y in zip(b, nr)]
    ax[0].bar(xs, cl, w, bottom=b, color="#ff7f0e", align="edge", label="ClusteredNR")
    ax[0].axhline(BINM, color="crimson", ls="--", lw=1, label=f"1/min floor ({BINM}/bin)")
    tot = sum(n for _, n, _, _ in sel)
    ax[0].set_title(f"Last {HOURS} h — {BINM}-min bins · {tot:,} query proteins · "
                    f"{tot/(HOURS*60):.2f}/min · {len(sel)} panels", fontsize=11)
    ax[0].set_ylabel(f"query proteins / {BINM}-min bin")
    ax[0].legend(fontsize=8, loc="upper left")
    ax[0].grid(alpha=.25, axis="y")

    times, cum, s = [], [], 0
    for t, n, ch, _ in sel:
        s += n
        times.append(t)
        cum.append(s)
    if times:
        ax[1].step(times, cum, where="post", color="#111", lw=2)
    ax[1].set_title(f"Last {HOURS} h — cumulative (rising = not stalled; flat tail = stalled)", fontsize=11)
    ax[1].set_ylabel("cumulative query proteins (12 h)")
    ax[1].grid(alpha=.25)
    for a in ax:
        for lbl in a.get_xticklabels():
            lbl.set_rotation(30)
            lbl.set_ha("right")
        a.set_xlim(start, now)
    fig.suptitle(f"BLASTp crawl — last 12 h, {BINM}-min bins, all lanes ({now.strftime('%H:%M')})",
                 fontsize=13)
    fig.tight_layout()
    os.makedirs(OUT, exist_ok=True)
    stamp = now.strftime("%Y%m%d_%H%M%S")
    for p in (os.path.join(OUT, f"last{HOURS}h_15min_{stamp}.png"),
              os.path.join(OUT, f"last{HOURS}h_15min_latest.png")):
        fig.savefig(p, dpi=130)

    lf, inflight, hits, empty = health(start, now)
    age = int((now - lf).total_seconds() / 60) if lf else None
    lanes = live_lanes()
    throttle, transient = recent_errors(30)
    print(f'{HOURS}h total: {tot} proteins = {tot / (HOURS * 60):.2f}/min | last bin({BINM}min): {nr[-1] + cl[-1]} | last 3 bins: {sum(nr[-3:]) + sum(cl[-3:])}', f"last fetch: {(lf.strftime('%H:%M') if lf else '?')} ({age} min ago) | live lanes: {(lanes if lanes is not None else '?')} | in-flight today: {inflight} | throttle errs(<30m): {throttle} | transient poll retries: {transient} (benign) | {HOURS}h fetches with hits: {hits}, empty: {empty}", sep="\n")
    # Verdict logic: a flat tail is only alarming if it means the crawl is actually STUCK.
    # With ClusteredNR, a single RID takes ~3-4 h, so several empty 15-min bins are NORMAL as
    # long as lanes are alive and there are no recent submit/poll errors. Only cry throttle when
    # lanes are live but errors are firing; call it stalled only when NO lane is alive.
    moving = (nr[-1] + cl[-1] + nr[-2] + cl[-2]) > 0
    if moving:
        status = "RISING"
    elif lanes is None:
        status = "FLAT TAIL — could not read processes; check manually"
    elif lanes == 0:
        status = "STALLED — no live lanes (all runners exited)"
    elif throttle > 0:
        status = f"FLAT TAIL + {throttle} THROTTLE errors — check run.logs (cool a lane)"
    else:
        status = (f"FLAT TAIL — normal for ClusteredNR ({lanes} lanes live, 0 throttle; "
                  f"{transient} transient poll retries are benign; slow RIDs in flight)")
    print(f"status: {status}")
    print("wrote", os.path.join(OUT, f"last{HOURS}h_15min_latest.png"))


if __name__ == "__main__":
    main()
