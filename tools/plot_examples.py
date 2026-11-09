#!/usr/bin/env python3
"""plot_examples.py — reference figures built ONLY from the figure_ready/ tidy CSVs.
Proves the export is plot-ready and gives downstream users a starting recipe.
Usage: python tools/plot_examples.py <figure_ready_dir> [--out-dir DIR]
The three PNGs go to --out-dir (default: the figure_ready folder). An existing PNG is refused, never
replaced (exit 2); use a fresh --out-dir to redraw.
Deps: matplotlib (stdlib csv). No seaborn/pandas required.
"""


def main(argv=None):
    import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
    from _console import emit  # noqa: E402
    import sys, os, csv, math
    from collections import defaultdict
    # -h/--help only; the positional use is unchanged, and extra words are ignored as before.
    import argparse
    ap = argparse.ArgumentParser(prog='plot_examples.py', description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('figure_ready_dir', nargs='?', default='figure_ready',
                    help='folder written by tools/export_figure_ready.py (default: figure_ready)')
    ap.add_argument('--out-dir', default=None,
                    help='folder for the three PNGs (default: the figure_ready folder); existing PNGs are refused')
    ns = ap.parse_known_args(sys.argv[1:] if argv is None else argv)[0]
    d = ns.figure_ready_dir
    out_dir = ns.out_dir or d
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    def load(name):
        with open(os.path.join(d,name)) as f: return list(csv.DictReader(f))

    names = ('fig1_fragmentation_gradient.png', 'fig2_class_prevalence.png', 'fig3_class_by_strain_heatmap.png')
    targets = [os.path.join(out_dir, n) for n in names]
    existing = [t for t in targets if os.path.lexists(t)]
    if existing:
        sys.stderr.write('OUTPUT_REFUSED: will not replace existing figure(s): ' + ', '.join(existing)
                         + '; use a fresh --out-dir\n')
        return 2
    os.makedirs(out_dir, exist_ok=True)

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
        pts=[(float(r['n50']),float(r['fragmentation_loss'])) for r in ss
             if r['assembly_tier']==grade and r['n50'] not in ('',None) and r['fragmentation_loss'] not in ('',None)]
        if pts:
            xs,ys=zip(*pts); ax.scatter(xs,ys,s=60,c=col.get(grade,'#888'),label=grade,edgecolor='k',linewidth=.5,zorder=3)
    ax.set_xscale('log'); ax.set_xlabel('Assembly N50 (bp, log scale)'); ax.set_ylabel('BGC count lost to correction\n(raw − corrected)')
    n_plotted=sum(1 for r in ss if r['n50'] not in ('',None) and r['fragmentation_loss'] not in ('',None))
    ax.set_title('Fragmentation-loss gradient (n=%d of %d isolates)'%(n_plotted,len(ss))); ax.grid(True,alpha=.3,zorder=0); ax.legend(title='Assembly')
    fig.tight_layout(); fig.savefig(targets[0],dpi=300); plt.close(fig)

    # ---- Fig 2: class prevalence (top 16), banded ----
    cp=sorted(load('class_prevalence.csv'),key=lambda r:-int(r['n_strains']))[:16]
    bandcol={'CORE':'#244','COMMON':'#48a','ACCESSORY':'#9bd','UNIQUE':'#ddd'}
    fig,ax=plt.subplots(figsize=(7,5))
    names=[r['product_class'] for r in cp][::-1]; vals=[int(r['n_strains']) for r in cp][::-1]
    cols=[bandcol.get(r['band'],'#bbb') for r in cp][::-1]
    ax.barh(names,vals,color=cols,edgecolor='k',linewidth=.4)
    ax.set_xlabel('Isolates carrying class (of %d)'%len(ss)); ax.set_title('Product-class prevalence across the cohort')
    import matplotlib.patches as mp
    ax.legend(handles=[mp.Patch(color=c,label=b) for b,c in bandcol.items()],fontsize=8,title='band')
    fig.tight_layout(); fig.savefig(targets[1],dpi=300); plt.close(fig)

    # ---- Fig 3: class x strain heatmap (n_bgcs) ----
    cbs=load('class_by_strain.csv')
    sids=[r['strain'] for r in ss]  # keep strain order from summary (corrected-rank); the exporter keys by 'strain'
    classes=[r['product_class'] for r in sorted(load('class_prevalence.csv'),key=lambda r:-int(r['n_strains']))[:20]]
    M=defaultdict(dict)
    for r in cbs: M[r['product_class']][r['strain']]=int(r['n_bgcs'])
    # class_by_strain.csv lists only nonzero strain x class counts. For a strain that has class rows,
    # an absent class is a counted zero. A strain with no rows at all was not recorded in this table:
    # its column is masked (grey), not drawn as zeros.
    recorded={r['strain'] for r in cbs}
    import numpy as np
    grid=np.ma.masked_array([[M.get(c,{}).get(s,0) for s in sids] for c in classes],
                            mask=[[s not in recorded for s in sids] for c in classes])
    n_unrecorded=sum(1 for s in sids if s not in recorded)
    cmap=matplotlib.colormaps['viridis'].copy(); cmap.set_bad('#d9d9d9')
    fig,ax=plt.subplots(figsize=(9,6))
    im=ax.imshow(grid,aspect='auto',cmap=cmap)
    ax.set_xticks(range(len(sids))); ax.set_xticklabels(sids,rotation=90,fontsize=7)
    ax.set_yticks(range(len(classes))); ax.set_yticklabels(classes,fontsize=8)
    ax.set_title('BGCs per product class x isolate (top 20 classes)'
                 + ('; grey = %d isolate(s) not in class_by_strain.csv' % n_unrecorded if n_unrecorded else ''))
    fig.colorbar(im,ax=ax,label='n_BGCs',shrink=.7)
    fig.tight_layout(); fig.savefig(targets[2],dpi=300); plt.close(fig)
    emit('wrote fig1_fragmentation_gradient.png, fig2_class_prevalence.png, fig3_class_by_strain_heatmap.png ->', out_dir
         + (f'\n  heatmap: {n_unrecorded} isolate(s) have no class_by_strain rows; shown grey, not as zero' if n_unrecorded else ''))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
