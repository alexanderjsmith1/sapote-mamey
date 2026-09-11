#!/usr/bin/env python3
"""plot_crawl_recent.py (VGP, 2026-08-20) — "what is landing RIGHT NOW", across ALL lanes.

Why this exists: the Wave-1 plot shows only the eight Wave-1 ledgers, so a whole-crawl question cannot
be answered from it. This one discovers EVERY `_NR_*RID*/_ledger.csv` under `Blastp RESULTS/`, so no
lane is invisible.

Measured all-lane throughput (2026-08-20): trailing 7 days 6,661 query proteins = 0.66/min; last 24 h
1,168 = 0.81/min. Alex's standing benchmark is ~1 protein/min, so the crawl sits slightly BELOW floor —
which is what justifies adding runner lanes.

Two panels, both by fetch time:
  * last 6 hours, 15-minute bins
  * last 1 hour, 5-minute bins
Bars are stacked by channel (nr vs ClusteredNR) so a stalled channel is obvious at a glance.

Run: Tools/bin/python3 plot_crawl_recent.py            (matplotlib lives in Tools/bin)
"""
import csv
import datetime
import glob
import os
import re
import sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BR = "Blastp RESULTS"
OUT = os.environ.get("SAPOTE_BLASTP_PLOT_DIR", "crawl_plots")
ROWS_RE = re.compile(r"(\d+)\s*row")

# UNITS WARNING (VGP 2026-08-20): the ledger `note` field's "N rows" is the number of BLAST HITS
# RETURNED for a panel (up to 250 subject matches), NOT the number of query proteins crawled. Summing
# it and calling the result "proteins" overstated throughput ~9x and produced a 7-day total larger than
# the entire gene universe. Throughput is measured in QUERY PROTEINS = the '>' records in the panel
# .faa that was fetched (mean ~11.3 per panel).
_SEQ_CACHE: dict[str, int] = {}
_PANEL_INDEX: dict[str, str] | None = None


def _index_panels() -> dict[str, str]:
    """basename -> path, built with ONE walk of the query roots.

    A recursive glob per panel is O(panels x tree) and took minutes over ~2,700 fetched panels;
    indexing once is O(tree) and takes seconds.
    """
    idx: dict[str, str] = {}
    for root_dir in glob.glob(os.path.join(BR, "_QUERIES*")):
        for root, _dirs, files in os.walk(root_dir):
            for f in files:
                if f.endswith(".faa") and f not in idx:
                    idx[f] = os.path.join(root, f)
    return idx


def query_proteins(panel_basename: str) -> int:
    """Number of query proteins in a fetched panel — the real throughput unit."""
    global _PANEL_INDEX
    if panel_basename in _SEQ_CACHE:
        return _SEQ_CACHE[panel_basename]
    if _PANEL_INDEX is None:
        _PANEL_INDEX = _index_panels()
    n = 0
    path = _PANEL_INDEX.get(panel_basename)
    if path:
        try:
            n = sum(1 for line in open(path) if line.startswith(">"))
        except Exception:
            n = 0
    _SEQ_CACHE[panel_basename] = n
    return n


def channel_of(ledger_base: str) -> str:
    """ClusteredNR ledgers carry CLUSTER in the base name; everything else is full nr."""
    return "ClusteredNR" if "CLUSTER" in ledger_base.upper() else "nr"


def load_fetches():
    """-> list of (fetch_time, n_proteins, channel, lane). Every lane, not a subset."""
    out = []
    for led in glob.glob(os.path.join(BR, "_NR_*RID*", "_ledger.csv")):
        lane = os.path.basename(os.path.dirname(led))
        ch = channel_of(lane)
        try:
            rdr = csv.DictReader(open(led))
        except Exception:
            continue
        for r in rdr:
            if r.get("status") != "fetched" or not r.get("fetch_iso"):
                continue
            # count QUERY PROTEINS, not returned hit rows (see UNITS WARNING above)
            n = query_proteins(os.path.basename(r.get("file", "")))
            try:
                t = datetime.datetime.strptime(r["fetch_iso"][:19], "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue
            out.append((t, n, ch, lane))
    out.sort()
    return out


def panel(ax, fetches, hours, bin_minutes, title):
    now = datetime.datetime.now()
    start = now - datetime.timedelta(hours=hours)
    sel = [f for f in fetches if f[0] >= start]
    nbins = int(hours * 60 / bin_minutes)
    edges = [start + datetime.timedelta(minutes=bin_minutes * i) for i in range(nbins + 1)]
    series = {"nr": [0] * nbins, "ClusteredNR": [0] * nbins}
    for t, n, ch, _ in sel:
        idx = int((t - start).total_seconds() // (bin_minutes * 60))
        if 0 <= idx < nbins:
            series.setdefault(ch, [0] * nbins)[idx] += n
    xs = [edges[i] for i in range(nbins)]
    width = bin_minutes / (24 * 60)
    bottom = [0] * nbins
    colors = {"nr": "#1f77b4", "ClusteredNR": "#ff7f0e"}
    for ch in ("nr", "ClusteredNR"):
        vals = series.get(ch, [0] * nbins)
        ax.bar(xs, vals, width=width, bottom=bottom, label=ch, color=colors[ch], align="edge")
        bottom = [b + v for b, v in zip(bottom, vals)]
    total = sum(n for _, n, _, _ in sel)
    rate = total / (hours * 60.0)
    ax.set_title(f"{title}\n{total:,} query proteins · {rate:.2f}/min · {len(sel)} panels fetched",
                 fontsize=11)
    ax.set_ylabel("query proteins crawled")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(alpha=0.25, axis="y")
    # benchmark line: Alex's 1 protein/minute floor, scaled to the bin
    ax.axhline(bin_minutes, color="crimson", ls="--", lw=1,
               label=f"1/min floor ({bin_minutes}/bin)")
    ax.legend(fontsize=8, loc="upper left")
    for lbl in ax.get_xticklabels():
        lbl.set_rotation(30)
        lbl.set_ha("right")
    return total, rate


def main():
    fetches = load_fetches()
    if not fetches:
        sys.exit("no fetched rows found")
    lanes = sorted({f[3] for f in fetches})
    print(f"lanes discovered: {len(lanes)}")
    for ln in lanes:
        n = sum(1 for f in fetches if f[3] == ln)
        print(f"  {ln:34s} {n:>5} fetched panels")

    fig, axes = plt.subplots(2, 1, figsize=(13, 9))
    t6, r6 = panel(axes[0], fetches, 6, 15, "Last 6 hours (15-min bins) — ALL lanes")
    t1, r1 = panel(axes[1], fetches, 1, 5, "Last 1 hour (5-min bins) — ALL lanes")
    fig.suptitle("BLASTp crawl — recent throughput across every ledger", fontsize=13)
    fig.tight_layout()
    os.makedirs(OUT, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for p in (os.path.join(OUT, f"recent_6h_1h_{stamp}.png"),
              os.path.join(OUT, "recent_6h_1h_latest.png")):
        fig.savefig(p, dpi=130)
        print("wrote", p)
    print(f'\nlast 6 h: {t6:,} proteins = {r6:.2f}/min', f'last 1 h: {t1:,} proteins = {r1:.2f}/min', '(1 protein/min floor = 60/hour = 360 per 6 h)', sep="\n")


if __name__ == "__main__":
    main()
