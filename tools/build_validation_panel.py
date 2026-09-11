#!/usr/bin/env python3
"""build_validation_panel.py — corrected-vs-raw percentile scatter for the external-validation panel.

Data-only figure (FIGURE_STYLE): the only non-data line is the y=x identity reference. The reading lives in the
caption, not in arrows on the plot. Single source of truth is resources/validation_runs.csv — to log a new run,
append one row there and re-run (or --replot). Public type strains are labelled; the private symbiont is
de-identified to a single contrast point (no strain identity, methods-level assembly percentile only).

Usage:
  python tools/build_validation_panel.py --csv resources/validation_runs.csv --out-dir figures
  python tools/build_validation_panel.py --replot --csv figures/validation_panel_data.csv --out-dir figures
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, os, csv
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
from _wbio import atomic_open
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

GOOD_C = "#2E7D32"      # GOOD assembly (confirmed-tier green)
POOR_C = "#7F8C8D"      # VERY_POOR (candidate-novel grey)
LINE_C = "#B0B0B0"

def load(path):
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            r["raw_pct"] = float(r["raw_pct"]); r["corr_pct"] = float(r["corr_pct"])
            rows.append(r)
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="resources/validation_runs.csv")
    ap.add_argument("--out-dir", default="figures")
    ap.add_argument("--replot", action="store_true", help="re-render from an emitted data CSV (no recompute)")
    ap.add_argument("--numbered", action="store_true", help="numbered markers + side key (auto-engages > 8 strains)")
    ap.add_argument("--dpi", type=int, default=200)
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    rows = load(a.csv)
    if not rows:
        # Empty-safe (v9.7.114): no input rows means there is no panel to plot and no data to
        # emit — exit cleanly with a clear message rather than crashing on rows[0].keys().
        emit(f"  no validation rows in {a.csv} — nothing to plot; skipping panel.")
        return

    numbered = a.numbered or len(rows) > 8
    fig, ax = plt.subplots(figsize=(8.6, 6.0) if numbered else (6.4, 6.0))
    ax.plot([0, 100], [0, 100], "--", color=LINE_C, lw=1, zorder=1)          # y=x identity reference
    ax.text(92, 86, "no change", color=LINE_C, fontsize=8, rotation=45, ha="center", va="center")
    for i, r in enumerate(rows, 1):
        good = r["assembly_tier"] == "GOOD"
        c = GOOD_C if good else POOR_C
        ax.scatter(r["raw_pct"], r["corr_pct"], s=130, color=c, edgecolor="white", linewidth=1.2, zorder=3)
        if numbered:
            ax.annotate(str(i), (r["raw_pct"], r["corr_pct"]), ha="center", va="center",
                        fontsize=7, color="white", fontweight="bold", zorder=4)
        else:
            pos = r.get("label_pos","above") or "above"
            off = {"above":(0,11),"below":(0,-11),"left":(-13,0),"right":(13,0)}.get(pos,(0,11))
            ha  = {"above":"center","below":"center","left":"right","right":"left"}.get(pos,"center")
            va  = {"above":"bottom","below":"top","left":"center","right":"center"}.get(pos,"bottom")
            ax.annotate(f"{r.get('short') or r['strain']}\n({r['assembly_tier']}, {r['retention_pct']}% ret.)",
                        (r["raw_pct"], r["corr_pct"]), xytext=off, textcoords="offset points",
                        fontsize=7.2, ha=ha, va=va, color="#333")
    ax.set_xlim(0, 100); ax.set_ylim(0, 104)
    ax.set_xlabel("Raw BGC-count percentile (vs 96-strain panel)")
    ax.set_ylabel("Corrected BGC-count percentile")
    ax.set_title("External validation: raw vs corrected BGC-count percentile", fontsize=10)
    from matplotlib.lines import Line2D
    ax.legend(handles=[Line2D([0],[0],marker="o",color="w",markerfacecolor=GOOD_C,markersize=9,label="GOOD assembly"),
                       Line2D([0],[0],marker="o",color="w",markerfacecolor=POOR_C,markersize=9,label="POOR / VERY_POOR assembly")],
              loc="lower right", fontsize=7.5, frameon=False)
    if numbered:
        key = "\n".join(f"{i:>2} \u00b7 {r.get('short') or r['strain']} ({r['niche']}; {r['retention_pct']}%)"
                         for i, r in enumerate(rows, 1))
        ax.text(1.03, 0.5, key, transform=ax.transAxes, fontsize=7, va="center", ha="left", family="monospace")
    ax.grid(True, alpha=0.15)
    fig.tight_layout()
    if numbered: fig.subplots_adjust(right=0.70)
    png = os.path.join(a.out_dir, "validation_panel_corrected_vs_raw.png")
    fig.savefig(png, dpi=a.dpi); plt.close(fig)

    # emit the data CSV alongside (the --replot source / citable artifact)
    out_csv = os.path.join(a.out_dir, "validation_panel_data.csv")
    with atomic_open(out_csv, "w", newline="") as f:
        w = _SafeDictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    above = [r["strain"] for r in rows if r["corr_pct"] > r["raw_pct"]]
    below = [r["strain"] for r in rows if r["corr_pct"] < r["raw_pct"]]
    emit(f'  wrote {png} (+ {out_csv}) — {len(rows)} strains', f"  reading: points above the line gain percentile on correction (high retention): {', '.join(above)}; below the line lose it (fragmentation): {', '.join(below)}.", sep="\n")

if __name__ == "__main__":
    main()
