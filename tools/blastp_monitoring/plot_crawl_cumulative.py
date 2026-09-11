#!/usr/bin/env python3
"""plot_crawl_cumulative.py (VGP, 2026-08-21) — CUMULATIVE query proteins retrieved over time,
pooled across EVERY blastp lane. The question this answers: "is the number retrieved still rising,
or has it gone flat (stalled)?"

Reuses plot_crawl_recent.load_fetches() verbatim, so the units are correct: y = QUERY PROTEINS
fetched (the '>' records in each fetched panel), NOT returned hit rows. See the UNITS WARNING in
plot_crawl_recent.py.

Two panels, both cumulative step lines (all lanes summed):
  * full history — the whole crawl, so you see the long arc
  * last 24 hours — zoomed, so a recent flat stretch = a stall is obvious
Each panel prints the current total and the trailing-60-min slope (proteins/min); a flat tail and a
near-zero slope both mean stalling.

Run: python3 "tools/blastp_monitoring/plot_crawl_cumulative.py"
"""
import datetime
import importlib.util
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd())
VGP = os.environ.get("SAPOTE_BLASTP_PLOT_DIR", os.path.join(ROOT, "blastp_plots"))
OUT = os.path.join(VGP, "crawl_plots")

# import load_fetches from the sibling recent-plot module (single source of truth for ledger parsing)
spec = importlib.util.spec_from_file_location("pcr", os.path.join(VGP, "plot_crawl_recent.py"))
pcr = importlib.util.module_from_spec(spec)
os.chdir(ROOT)  # load_fetches uses BR="Blastp RESULTS" relative to cwd
spec.loader.exec_module(pcr)


def cumulative(fetches):
    """-> (times, cum_total, cum_nr, cum_cl) as running sums by fetch time."""
    times, tot, nr, cl = [], [], [], []
    st = sn = sc = 0
    for t, n, ch, _ in fetches:          # already sorted by time
        st += n
        if ch == "ClusteredNR":
            sc += n
        else:
            sn += n
        times.append(t); tot.append(st); nr.append(sn); cl.append(sc)
    return times, tot, nr, cl


def slope_last(fetches, minutes):
    now = datetime.datetime.now()
    start = now - datetime.timedelta(minutes=minutes)
    got = sum(n for t, n, _, _ in fetches if t >= start)
    return got, got / minutes


def panel(ax, fetches, title, since_hours=None):
    if since_hours is not None:
        # re-zero the baseline: cumulative of proteins retrieved WITHIN the window (from 0),
        # so recent movement is visible instead of a flat line pinned at the all-time total.
        cutoff = datetime.datetime.now() - datetime.timedelta(hours=since_hours)
        fetches = [f for f in fetches if f[0] >= cutoff]
    times, tot, nr, cl = cumulative(fetches)
    if not times:
        ax.set_title(title + " — no data"); return
    ax.step(times, tot, where="post", color="#111", lw=2, label="all lanes (total)")
    ax.step(times, nr, where="post", color="#1f77b4", lw=1.2, label="nr", alpha=0.8)
    ax.step(times, cl, where="post", color="#ff7f0e", lw=1.2, label="ClusteredNR", alpha=0.8)
    ax.set_ylabel("cumulative query proteins retrieved")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, loc="upper left")
    for lbl in ax.get_xticklabels():
        lbl.set_rotation(30); lbl.set_ha("right")
    ax.set_title(title, fontsize=11)


def main():
    fetches = pcr.load_fetches()
    if not fetches:
        sys.exit("no fetched rows found")
    times, tot, nr, cl = cumulative(fetches)
    grand = tot[-1]
    lanes = sorted({f[3] for f in fetches})
    g60, r60 = slope_last(fetches, 60)
    g360, r360 = slope_last(fetches, 360)
    print(f'lanes: {len(lanes)}   fetched panels: {len(fetches)}', f'cumulative query proteins retrieved (all time): {grand:,}', f'  trailing 60 min : {g60:>5} proteins = {r60:.2f}/min', f'  trailing  6 h   : {g360:>5} proteins = {r360:.2f}/min   (1/min floor = 360)', sep="\n")
    status = "RISING" if r60 > 0.05 else "STALLED (flat tail)"
    print(f"  status: {status}")

    fig, axes = plt.subplots(2, 1, figsize=(13, 9))
    panel(axes[0], fetches, f"Full history — {grand:,} query proteins retrieved, all lanes pooled")
    panel(axes[1], fetches,
          f"Last 24 h — trailing 60 min = {g60} proteins ({r60:.2f}/min) · {status}",
          since_hours=24)
    fig.suptitle("BLASTp crawl — cumulative proteins retrieved (all lanes)", fontsize=13)
    fig.tight_layout()
    os.makedirs(OUT, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = [os.path.join(OUT, f"cumulative_{stamp}.png"),
             os.path.join(OUT, "cumulative_latest.png")]
    for p in paths:
        fig.savefig(p, dpi=130)
        print("wrote", p)
    return paths[-1]


if __name__ == "__main__":
    main()
