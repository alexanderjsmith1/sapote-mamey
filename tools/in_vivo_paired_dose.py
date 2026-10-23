"""Promoted paired-dose plot with the original dose ordering and geometry."""
import csv, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools._figure_route_common import bind,output_dir,receipt,save,table,unique,number
from mamey.figure_theme import apply_theme
import argparse,json
p=argparse.ArgumentParser(description='Paired-dose in-vivo screening display; no target inferred')
p.add_argument('--data',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args()
raw=table(a.data,['isolate','genus_16s','dose','neg_log_cfu','in_bee_wasp_figure'])
selected=[r for r in raw if r['in_bee_wasp_figure']=='yes']
if not selected:raise ValueError('empty selected cohort')
for row in selected:number(row['neg_log_cfu'],-2.1,0.1)
for iso in dict.fromkeys(r['isolate'] for r in selected):
    group=[r for r in selected if r['isolate']==iso]
    if len(group)!=2 or {r['dose'] for r in group}!={'low','high'} or len({r['genus_16s'] for r in group})!=1:
        raise ValueError('each selected isolate needs one low and one high dose with consistent recorded genus')
bind([a.data,Path(__file__)])
out=output_dir(a.out)
HERE=Path(__file__).resolve().parent
apply_theme(plt,profile='manuscript')
plt.rcParams.update({"font.family": "Arial", "font.size": 8, "mathtext.fontset": "custom",
                     "mathtext.rm": "Arial:bold", "mathtext.it": "Arial:italic:bold", "mathtext.sf": "Arial:italic"})
INK = "#17212E"
GEN = {"Streptomyces": "#2E8B84", "Micromonospora": "#C0973F", "Actinomadura": "#4C78A8", "Streptosporangium": "#B07AA1"}
palette_path=HERE.parent/'mamey/data/genus_palette.json'
GEN=json.loads(palette_path.read_text())['default']
unknown={r['genus_16s'] for r in selected}-set(GEN)
if unknown:raise ValueError('genus absent from palette: '+str(sorted(unknown)))
YL = "Δ log CFU"
_raw=selected
rows = []
for iso in dict.fromkeys(r["isolate"] for r in _raw):
    d = {r["dose"]: float(r["neg_log_cfu"]) for r in _raw if r["isolate"] == iso}
    first = next(r for r in _raw if r["isolate"] == iso)
    rows.append({"isolate": iso, "genus_16s": first["genus_16s"], "low": d["low"], "high": d["high"], "v": (d["low"] + d["high"]) / 2})
s = sorted(rows, key=lambda r: r["v"], reverse=True)
xs = range(len(s))

def style(ax):
    for sp in ("top", "right"): ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"): ax.spines[sp].set_color("#9AA3AF"); ax.spines[sp].set_linewidth(0.6)
    ax.tick_params(colors=INK, width=0.6, length=2.5, labelsize=8)

fig = plt.figure(figsize=(3.4, 3.05))
ax = fig.add_axes([0.19, 0.36, 0.58, 0.61])      # left, bottom, width, height (fractions of the fixed canvas)
ax.axhline(0, color="#9AA3AF", lw=0.6)
for x, r in zip(xs, s):
    ax.plot([x, x], [r["low"], r["high"]], color=GEN[r["genus_16s"]], lw=1.0, zorder=2)
ax.scatter(xs, [r["low"] for r in s], s=34, facecolor="white", edgecolor=[GEN[r["genus_16s"]] for r in s], lw=1.2, zorder=3)
ax.scatter(xs, [r["high"] for r in s], s=34, c=[GEN[r["genus_16s"]] for r in s], edgecolor="white", lw=0.7, zorder=4)
ax.legend(handles=[Line2D([], [], marker="o", ls="", ms=5, mfc="white", mec="#6B7280", mew=1.2, label="low dose"),
                   Line2D([], [], marker="o", ls="", ms=5, mfc="#6B7280", mec="white", label="high dose")],
          loc="lower left", bbox_to_anchor=(1.02, 0.0), frameon=False, fontsize=8, borderaxespad=0, handletextpad=0.3)
ax.set_xticks(list(xs))
ax.set_xticklabels([rf"$\mathsf{{{r['genus_16s']}}}$ sp. {r['isolate']}" for r in s], rotation=45, ha="right", rotation_mode="anchor", fontsize=8)
ax.set_ylim(-2.1, 0.1); ax.set_yticks([0, -0.5, -1.0, -1.5, -2.0]);   # the original ticks (0.5 steps)
ax.set_xlim(-0.6, len(s) - 0.4); ax.set_ylabel(YL, fontsize=8, color=INK); style(ax)
save(fig,out/'in_vivo_paired_dose','in_vivo_paired_dose')
plt.close(fig)
receipt(out,'in_vivo_paired_dose',[a.data,palette_path,Path(__file__)],{'dose_values':'as recorded','target_organism':'not inferred'})
