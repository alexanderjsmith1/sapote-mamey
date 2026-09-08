#!/usr/bin/env python3
"""plot_usable_6h.py (VGP, 2026-08-21) — USABLE data returned over the last 6 hours, all lanes.

"Usable" = a fetched panel that came back with real hits (ledger note rows>0). Panels that returned
0 hits are shown separately (red) — they are genes with no significant match (possibly reference-dark,
possibly throttle-era artifacts; do NOT interpret without a re-query). Units are correct: proteins =
QUERY PROTEINS ('>' records in the fetched panel), via plot_crawl_recent.query_proteins().

Two panels, 15-min bins:
  * top    — usable query proteins / bin (green)
  * bottom — panels / bin: usable (blue) stacked with empty/0-hit (red)

Caveat the reader should keep in mind: a 6h window can include a stall period; the bars cluster in
whatever sub-window was actually crawling. Prints totals + the current (last-bin) rate.

Run: python3 "tools/blastp_monitoring/plot_usable_6h.py"
"""
import csv
import datetime
import glob
import importlib.util
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd())
VGP = os.environ.get("SAPOTE_BLASTP_PLOT_DIR", os.path.join(ROOT, "blastp_plots"))
BR = os.path.join(ROOT, "Blastp RESULTS")
OUT = os.path.join(VGP, "crawl_plots")
HOURS = 6
BINM = 15
ROWS_RE = re.compile(r"(\d+)\s*row")

os.chdir(ROOT)
spec = importlib.util.spec_from_file_location("pcr", os.path.join(VGP, "plot_crawl_recent.py"))
pcr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pcr)   # provides query_proteins()


def main():
    now = datetime.datetime.now()
    start = now - datetime.timedelta(hours=HOURS)
    recs = []
    for led in glob.glob(os.path.join(BR, "_NR_*RID*", "_ledger.csv")):
        try:
            R = list(csv.DictReader(open(led)))
        except Exception:
            continue
        for r in R:
            if r.get("status") != "fetched" or not r.get("fetch_iso"):
                continue
            try:
                t = datetime.datetime.strptime(r["fetch_iso"][:19], "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue
            if t < start:
                continue
            m = ROWS_RE.search(r.get("note", "") or "")
            rows = int(m.group(1)) if m else 0
            prot = pcr.query_proteins(os.path.basename(r.get("file", "")))
            recs.append((t, prot, rows > 0))

    nb = int(HOURS * 60 / BINM)
    edges = [start + datetime.timedelta(minutes=BINM * i) for i in range(nb + 1)]
    prot_bin = [0] * nb
    pan_bin = [0] * nb
    empty_bin = [0] * nb
    for t, prot, usable in recs:
        i = int((t - start).total_seconds() // (BINM * 60))
        if 0 <= i < nb:
            if usable:
                prot_bin[i] += prot
                pan_bin[i] += 1
            else:
                empty_bin[i] += 1
    xs = [edges[i] for i in range(nb)]
    w = BINM / 1440.0

    fig, ax = plt.subplots(2, 1, figsize=(14, 9))
    ax[0].bar(xs, prot_bin, w, align="edge", color="#2ca02c", label="usable query proteins")
    ax[0].set_title(f"Usable query proteins returned — last {HOURS}h, {BINM}-min bins "
                    f"({sum(prot_bin):,} total)", fontsize=11)
    ax[0].set_ylabel("query proteins / bin")
    ax[0].legend(fontsize=8, loc="upper left")
    ax[0].grid(alpha=.25, axis="y")
    ax[1].bar(xs, pan_bin, w, align="edge", color="#1f77b4", label="usable panels (hits)")
    ax[1].bar(xs, empty_bin, w, align="edge", bottom=pan_bin, color="#d62728",
              label="empty panels (0 hits)")
    ax[1].set_title(f"Panels returned — last {HOURS}h "
                    f"({sum(pan_bin)} usable, {sum(empty_bin)} empty)", fontsize=11)
    ax[1].set_ylabel("panels / bin")
    ax[1].legend(fontsize=8, loc="upper left")
    ax[1].grid(alpha=.25, axis="y")
    for a in ax:
        for lbl in a.get_xticklabels():
            lbl.set_rotation(30)
            lbl.set_ha("right")
        a.set_xlim(start, now)
    fig.suptitle(f"BLASTp — usable data returned, last {HOURS}h (all lanes, {now.strftime('%H:%M')})",
                 fontsize=13)
    fig.tight_layout()
    os.makedirs(OUT, exist_ok=True)
    stamp = now.strftime("%Y%m%d_%H%M%S")
    for p in (os.path.join(OUT, f"usable_6h_{stamp}.png"),
              os.path.join(OUT, "usable_6h_latest.png")):
        fig.savefig(p, dpi=130)
    total_p = sum(prot_bin)
    print(f'{HOURS}h usable: {total_p} query proteins across {sum(pan_bin)} panels; {sum(empty_bin)} empty panels', f'rate: {total_p / (HOURS * 60):.2f} usable proteins/min | last {BINM}-min bin: {prot_bin[-1]} proteins / {pan_bin[-1]} panels', sep="\n")
    print("wrote", os.path.join(OUT, "usable_6h_latest.png"))


if __name__ == "__main__":
    main()
