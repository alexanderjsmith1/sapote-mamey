#!/usr/bin/env python3
"""plot_examples.py — reference figures built ONLY from the figure_ready/ tidy CSVs.
Proves the export is plot-ready and gives downstream users a starting recipe.
Usage: python tools/plot_examples.py <figure_ready_dir>
Deps: matplotlib (stdlib csv). No seaborn/pandas required.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import sys, os, csv, math
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

d=sys.argv[1] if len(sys.argv)>1 else 'figure_ready'
def load(name):
    with open(os.path.join(d,name)) as f: return list(csv.DictReader(f))

# ---- Fig 1: fragmentation-loss gradient (the Application Note figure) ----
ss=load('strain_summary.csv')
col={'GOOD':'#2a7','MODERATE':'#e0a030','MOD':'#e0a030','POOR':'#c44'}
order={'GOOD':0,'MODERATE':1,'MOD':1,'POOR':2}
# v9.7.371 fix: was r['assembly_grade'] -- the real header this file's own docstring claims to
# read (tools/export_figure_ready.py's actual writer, strain_summary.csv) is "assembly_tier", not
# "assembly_grade" (that name only survives in a stale data-dictionary comment in the writer file,
# export_figure_ready.py, itself corrected in a companion patch this session). Running this script
# against a real figure_ready/ dir as documented ("Usage: python tools/plot_examples.py
# <figure_ready_dir>") raised KeyError: 'assembly_grade' before Fig 1 was even drawn.
grades=sorted({r['assembly_tier'] for r in ss}, key=lambda gx:order.get(gx,9))
fig,ax=plt.subplots(figsize=(7,4.4))
for grade in grades:
    pts=[(float(r['n50']),float(r['fragmentation_loss'])) for r in ss if r['assembly_tier']==grade]
    if pts:
        xs,ys=zip(*pts); ax.scatter(xs,ys,s=60,c=col.get(grade,'#888'),label=grade,edgecolor='k',linewidth=.5,zorder=3)
ax.set_xscale('log'); ax.set_xlabel('Assembly N50 (bp, log scale)'); ax.set_ylabel('BGC count lost to correction\n(raw − corrected)')
ax.set_title('Fragmentation-loss gradient (n=%d strains)'%len(ss)); ax.grid(True,alpha=.3,zorder=0); ax.legend(title='Assembly')
fig.tight_layout(); fig.savefig(os.path.join(d,'fig1_fragmentation_gradient.png'),dpi=150); plt.close(fig)

# ---- Fig 2: class prevalence (top 16), banded ----
cp=sorted(load('class_prevalence.csv'),key=lambda r:-int(r['n_strains']))[:16]
bandcol={'CORE':'#244','COMMON':'#48a','ACCESSORY':'#9bd','UNIQUE':'#ddd'}
fig,ax=plt.subplots(figsize=(7,5))
names=[r['product_class'] for r in cp][::-1]; vals=[int(r['n_strains']) for r in cp][::-1]
cols=[bandcol.get(r['band'],'#bbb') for r in cp][::-1]
ax.barh(names,vals,color=cols,edgecolor='k',linewidth=.4)
ax.set_xlabel('Strains carrying class (of %d)'%len(ss)); ax.set_title('Product-class prevalence across the cohort')
import matplotlib.patches as mp
ax.legend(handles=[mp.Patch(color=c,label=b) for b,c in bandcol.items()],fontsize=8,title='band')
fig.tight_layout(); fig.savefig(os.path.join(d,'fig2_class_prevalence.png'),dpi=150); plt.close(fig)

# ---- Fig 3: class x strain heatmap (n_bgcs) ----
cbs=load('class_by_strain.csv')
sids=[r['sid'] for r in ss]  # keep strain order from summary (corrected-rank)
classes=[r['product_class'] for r in sorted(load('class_prevalence.csv'),key=lambda r:-int(r['n_strains']))[:20]]
M=defaultdict(dict)
for r in cbs: M[r['product_class']][r['sid']]=int(r['n_bgcs'])
grid=[[M.get(c,{}).get(s,0) for s in sids] for c in classes]
fig,ax=plt.subplots(figsize=(9,6))
im=ax.imshow(grid,aspect='auto',cmap='viridis')
ax.set_xticks(range(len(sids))); ax.set_xticklabels(sids,rotation=90,fontsize=7)
ax.set_yticks(range(len(classes))); ax.set_yticklabels(classes,fontsize=8)
ax.set_title('BGCs per product class x strain (top 20 classes)')
fig.colorbar(im,ax=ax,label='n_BGCs',shrink=.7)
fig.tight_layout(); fig.savefig(os.path.join(d,'fig3_class_by_strain_heatmap.png'),dpi=150); plt.close(fig)
emit('wrote fig1_fragmentation_gradient.png, fig2_class_prevalence.png, fig3_class_by_strain_heatmap.png ->',d)
