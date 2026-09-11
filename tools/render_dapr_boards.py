#!/usr/bin/env python3
"""render_dapr_boards.py — render the DAPR antibacterial/antifungal boards and the
fragment-rescue landscape directly from workbook-derived figure-ready CSVs.

Why: the DAPR boards (C1/C2) and Fragment_Rescue_Tiers live in the master workbook; this tool
regenerates their figures from the exported tidy CSVs so the board figures never drift from the
workbook. Run `export_figure_ready.py` first to produce the CSVs.

Inputs (in --data dir, produced by export_figure_ready.py):
  c1_dapr_antibacterial.csv, c2_dapr_antifungal.csv, fragment_rescue_tiers.csv
Outputs (in --out dir): fig_dapr_antibacterial.png, fig_dapr_antifungal.png,
  fig_fragment_rescue_landscape.png

Usage: python tools/render_dapr_boards.py --data figure_ready --out figures
Dependency-light: matplotlib + stdlib. House style locked to FIGURE_CONVENTIONS.md.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import os, csv, argparse
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PRIMARY = "#2c6fbb"
TIER_COL = {"A": "#2a9d5a", "B": "#2c6fbb", "C": "#e0a030", "D": "#cc4444"}
TIER_LAB = {"A": "A: intact (no rescue)", "B": "B: high recovery upside",
            "C": "C: limited recovery", "D": "D: failed assembly"}
plt.rcParams.update({"font.family": "DejaVu Sans", "figure.facecolor": "white",
                     "savefig.dpi": 200, "savefig.bbox": "tight",
                     "axes.spines.top": False, "axes.spines.right": False})


def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _tier_from_score(s):
    return {"3": "HIGH", "2": "MED", "1": "WATCH"}.get(str(s).strip(), "")


def board_table(rows, title, note, out_png):
    headers = ["tier", "strain", "BGC (locator)", "class", "KCB nearest", "note"]
    widths = [0.07, 0.09, 0.18, 0.20, 0.18, 0.28]
    table = []
    for r in rows:
        table.append([_tier_from_score(r.get("AN_Score")), r.get("strain", ""),
                      r.get("BGC_ID", ""), r.get("Product_Class", ""),
                      (r.get("KCB_Provenance", "") or "").replace("KCB~", ""),
                      r.get("Activity_Ref", "") or r.get("Rationale", "")])
    fig, ax = plt.subplots(figsize=(14.5, 0.45 * len(table) + 1.5))
    ax.axis("off")
    t = ax.table(cellText=table, colLabels=headers, loc="center", cellLoc="left", colWidths=widths)
    t.auto_set_font_size(False); t.set_fontsize(8); t.scale(1, 1.35)
    for c in range(len(headers)):
        t[0, c].set_facecolor(PRIMARY); t[0, c].set_text_props(color="white", fontweight="bold")
    for ri in range(1, len(table) + 1):
        for c in range(len(headers)):
            t[ri, c].set_facecolor("#f2f6fb" if ri % 2 else "white")
    ax.set_title(title, fontsize=12, pad=8)
    if note:
        ax.text(0, -0.02, note, transform=ax.transAxes, fontsize=7.5, color="#666", style="italic")
    fig.savefig(out_png); plt.close(fig)


def fragment_landscape(rows, out_png):
    fig, ax = plt.subplots(figsize=(7.5, 5))
    for tg in ["A", "B", "C", "D"]:
        pts = [(float(r["Frag_Loss"]), float(r["EFLS_Pairs"]), float(r["RG_GMCI_HIGH"]))
               for r in rows if r.get("Tier") == tg]
        if pts:
            xs, ys, sz = zip(*pts)
            ax.scatter(xs, ys, s=[30 + v / 6 for v in sz], c=TIER_COL[tg], label=TIER_LAB[tg],
                       edgecolor="k", lw=.5, alpha=.85, zorder=3)
    ax.set_xlabel("Fragmentation loss (raw - corrected BGCs)")
    ax.set_ylabel("EFLS fragment-linkage candidate pairs")
    ax.set_title("Fragment-rescue landscape (point size = RG-GMCI HIGH pairs)")
    ax.grid(True, alpha=.25); ax.legend(fontsize=8, loc="upper left")
    fig.savefig(out_png); plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="figure_ready", help="dir with the DAPR/fragment CSVs")
    ap.add_argument("--out", default="figures", help="output dir for PNGs")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    abn = ("Cell-wall/membrane/ribosome/T2PKS classes. Cytotoxic-adjacent & siderophore hits routed out. "
           "Class-level hypotheses; bioactivity metadata is optional strain-level context.")
    afn = ("Two antifungal axes: polyene (ergosterol/membrane) + HSAF PTM-tetramate (sphingolipid). "
           "arylpolyene excluded. Class-level hypotheses; bioactivity metadata is optional strain-level context.")
    board_table(read_csv(os.path.join(a.data, "c1_dapr_antibacterial.csv")),
                "DAPR - Antibacterial board (Sapote judgment, reference-framework scored)",
                abn, os.path.join(a.out, "fig_dapr_antibacterial.png"))
    board_table(read_csv(os.path.join(a.data, "c2_dapr_antifungal.csv")),
                "DAPR - Antifungal board (Sapote judgment): polyenes + HSAF tetramate macrolactams",
                afn, os.path.join(a.out, "fig_dapr_antifungal.png"))
    fragment_landscape(read_csv(os.path.join(a.data, "fragment_rescue_tiers.csv")),
                       os.path.join(a.out, "fig_fragment_rescue_landscape.png"))
    emit("rendered fig_dapr_antibacterial / fig_dapr_antifungal / fig_fragment_rescue_landscape from", a.data)


if __name__ == "__main__":
    main()
