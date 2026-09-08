#!/usr/bin/env python3
"""build_panel_figure.py — compose a labelled multi-panel figure from existing single-panel PNGs.

For main-text "landscape" figures and supplementary panels: arranges N existing figure PNGs into a grid with
panel letters (A, B, C, ...). Because each input figure is itself reproducible (ships its own *_data.csv +
replot), the composite inherits reproducibility — edit a panel's CSV, replot it, then recompose. The panel
set is given as an editable manifest, so adding/removing/reordering panels is a one-line change.

Usage:
  python tools/build_panel_figure.py --in-dir figures --out figures/fig_cohort_landscape.png \
      --panels fig_genome_size_vs_bgc,fig_chitinase_load,fig_chemistry_landscape,\
fig_chitinase_normalization,fig_pangenome_rarefaction,fig_novelty_vs_fragmentation --cols 3 --title "Cohort landscape"
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, math, os, sys

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--in-dir', default='figures'); ap.add_argument('--out', required=True)
    ap.add_argument('--panels', required=True, help='comma-separated figure basenames (no .png)')
    ap.add_argument('--cols', type=int, default=3); ap.add_argument('--title', default='')
    a=ap.parse_args()
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, matplotlib.image as mpimg
    names=[p.strip() for p in a.panels.split(',') if p.strip()]
    paths=[os.path.join(a.in_dir,n+'.png') for n in names]
    missing=[p for p in paths if not os.path.exists(p)]
    if missing:
        # v9.7.151 (bunny-hop 60-file): fail loudly instead of silent
        # success. A composite figure can't be built without its inputs;
        # returning exit 0 on missing panels hid the error in upstream
        # batch pipelines.
        emit('  missing panels:', missing, file=sys.stderr)
        sys.exit(1)
    cols=a.cols; rows=math.ceil(len(paths)/cols)
    fig,axes=plt.subplots(rows,cols,figsize=(cols*4.6, rows*3.4))
    axes=axes.flatten() if hasattr(axes,'flatten') else [axes]
    for i,ax in enumerate(axes):
        if i<len(paths):
            ax.imshow(mpimg.imread(paths[i])); ax.axis('off')
            ax.text(-0.02,1.02,chr(65+i),transform=ax.transAxes,fontsize=16,fontweight='bold',va='top',ha='right',family='DejaVu Sans')
        else: ax.axis('off')
    if a.title: fig.suptitle(a.title,fontsize=14,fontweight='bold',y=0.998)
    plt.tight_layout()
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    plt.savefig(a.out,dpi=150,bbox_inches='tight'); plt.close()
    # write an editable manifest beside the output (records the panel set + order)
    with open(os.path.splitext(a.out)[0]+'_panels.txt','w') as f:
        f.write('\n'.join(names)+'\n')
    emit(f"  {os.path.basename(a.out)}: {len(paths)} panels ({rows}x{cols}) + _panels.txt manifest")

if __name__=='__main__': main()
