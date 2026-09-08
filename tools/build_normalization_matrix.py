#!/usr/bin/env python3
"""build_normalization_matrix.py — fragmentation-robustness of BGC-class counts across a cohort.

Regenerates two analyses from any cohort:
  (1) class-sensitivity ranking  — corr( raw class count , log10 contig count ) per BGC class
  (2) normalization matrix       — |corr( class/denominator , fragmentation )| for every class x denominator

WHY: raw counts of large modular classes (NRPS, NRPS-like) inflate with assembly fragmentation; compact
classes are robust; a couple deflate. This tool re-checks, as the strain set grows, which classes have
become trustworthy and which still need the closed-genome caveat, and which normalizer best stabilizes each.

FIGURE-DATA PACKAGING (every figure ships with its data + a replot path):
  - normalization_per_strain.csv   the EDITABLE source: one row per strain (contigs + class counts +
                                   denominators). Remove a strain row here (e.g. a PI drop) and re-run
                                   with --replot to regenerate everything WITHOUT that strain.
  - normalization_class_ranking.csv   derived data behind fig_class_fragmentation.png
  - normalization_matrix.csv          derived data behind fig_normalization_matrix.png
  - fig_class_fragmentation.png, fig_normalization_matrix.png   (FIGURE_STYLE-compliant: no overlays)
  - normalization_recipe.md           what each figure shows + how to add/remove data and replot

Usage:
  python tools/build_normalization_matrix.py --banked-dir cohort --out-dir .            # full compute
  python tools/build_normalization_matrix.py --out-dir . --replot                       # replot from edited CSV
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, json, os
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import numpy as np
import sys as _sys, os as _os


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _wbio import atomic_write_text, atomic_open

CLASSES=['NRPS','NRPS-like','T1PKS','T2PKS','T3PKS','transAT-PKS','terpene','lanthipeptide','lassopeptide',
         'RiPP-like','thiopeptide','siderophore','NRP-metallophore','ectoine','betalactone','arylpolyene',
         'butyrolactone','melanin','phosphonate','indole','saccharide','amglyccycl']
DEN_CLASSES={'ecto+napaa':['ectoine','napaa'],'terpene':['terpene'],'halogenase':['halogenated','halogenase']}

def compute_per_strain(banked):
    from collections import Counter, defaultdict
    bgc=_read_json(os.path.join(banked,'bgc_data.json')); strains=bgc['strains']; bgcs=bgc['bgcs']
    ccount=defaultdict(Counter); den=defaultdict(Counter)
    for b in bgcs:
        sid=b['sid']; p=(b.get('products') or '').lower()
        for c in CLASSES:
            if c.lower() in p: ccount[c][sid]+=1
        for dn,toks in DEN_CLASSES.items():
            if any(t in p for t in toks): den[dn][sid]+=1
    rows=[]
    for sid,s in strains.items():
        r={'sid':sid,'organism':s.get('organism',''),'contigs':s.get('contigs',0),
           'genome_Mbp':round(s.get('genome_bp',0)/1e6,3),'raw_BGC':s.get('raw_bgcs',0),
           'corrected_BGC':s.get('corrected_bgcs',0)}
        for c in CLASSES: r[f'cls_{c}']=ccount[c].get(sid,0)
        for dn in DEN_CLASSES: r[f'den_{dn}']=den[dn].get(sid,0)
        rows.append(r)
    return rows

def derive(rows):
    """from per-strain rows -> class ranking + normalization matrix. Operates only on rows present in the
    CSV, so deleting a strain row propagates to every output."""
    sids=[r['sid'] for r in rows]
    lc=np.log10(np.array([max(int(r['contigs']),1) for r in rows],float))
    DEN={'raw_BGC':np.array([float(r['raw_BGC']) for r in rows]),
         'corrected_BGC':np.array([float(r['corrected_BGC']) for r in rows]),
         'genome_Mbp':np.array([float(r['genome_Mbp']) for r in rows]),
         'ecto+napaa':np.array([float(r['den_ecto+napaa']) for r in rows]),
         'terpene':np.array([float(r['den_terpene']) for r in rows]),
         'halogenase':np.array([float(r['den_halogenase']) for r in rows])}
    ranking=[]; matrix=[]
    for c in CLASSES:
        v=np.array([float(r[f'cls_{c}']) for r in rows])
        if v.sum()<5: continue
        rr=float(np.corrcoef(v,lc)[0,1]) if v.std()>0 else 0.0
        regime=('inflates' if rr>0.3 else 'deflates' if rr<-0.2 else 'robust' if abs(rr)<0.15 else 'mild')
        ranking.append({'class':c,'n_total':int(v.sum()),'corr_fragmentation':round(rr,3),'regime':regime})
        row={'class':c,'raw':round(rr,3)}
        for dn,dv in DEN.items():
            mask=dv>=1
            if mask.sum()<10 or v[mask].std()==0: row[dn]=''
            else:
                ratio=v[mask]/dv[mask]
                row[dn]=round(abs(float(np.corrcoef(ratio,lc[mask])[0,1])),3) if ratio.std()>0 and lc[mask].std()>0 else ''
        matrix.append(row)
    ranking.sort(key=lambda x:x['corr_fragmentation'])
    matrix.sort(key=lambda x:-abs(x['raw']))
    return ranking, matrix, list(DEN)

def plot(ranking, matrix, dens, out):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap; from matplotlib.patches import Patch
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    # fig A: class-sensitivity ranking (data only, neutral title, numeric labels)
    order=ranking; vals=[r['corr_fragmentation'] for r in order]; names=[r['class'] for r in order]
    col=lambda r:'#C0392B' if r>0.3 else ('#7D3C98' if r<-0.2 else ('#2E86AB' if abs(r)<0.15 else '#E59866'))
    fig,ax=plt.subplots(figsize=(7.5,6)); y=np.arange(len(order))
    ax.barh(y,vals,color=[col(v) for v in vals],height=0.72)
    for i,v in enumerate(vals): ax.text(v+(0.01 if v>=0 else -0.01),i,f'{v:+.2f}',va='center',ha='left' if v>=0 else 'right',fontsize=7)
    ax.axvline(0,color='#333',lw=0.8); ax.set_yticks(y); ax.set_yticklabels(names,fontsize=8.5)
    ax.set_xlabel('corr( raw class count , log10 contig count )'); ax.set_xlim(-0.6,0.6)
    ax.set_title('BGC-class count sensitivity to assembly fragmentation',fontsize=11,weight='bold')
    ax.legend(handles=[Patch(color='#C0392B',label='inflates'),Patch(color='#E59866',label='mild'),
              Patch(color='#2E86AB',label='robust'),Patch(color='#7D3C98',label='deflates')],loc='lower right',fontsize=7.5,frameon=False)
    plt.tight_layout(); plt.savefig(os.path.join(out,'fig_class_fragmentation.png'),dpi=160); plt.close()
    # fig B: normalization matrix heatmap (numeric cell labels = data)
    Mat=np.array([[ (m[d] if m[d]!='' else np.nan) for d in dens] for m in matrix],float)
    cmap=LinearSegmentedColormap.from_list('rob',['#1B7837','#F7F7C8','#C0392B'])
    fig,ax=plt.subplots(figsize=(7.5,7)); im=ax.imshow(Mat,cmap=cmap,vmin=0,vmax=0.5,aspect='auto')
    ax.set_xticks(range(len(dens))); ax.set_xticklabels(dens,rotation=35,ha='right',fontsize=8.5)
    ax.set_yticks(range(len(matrix))); ax.set_yticklabels([m['class'] for m in matrix],fontsize=8.5)
    for i in range(len(matrix)):
        for j in range(len(dens)):
            if not np.isnan(Mat[i,j]): ax.text(j,i,f'{Mat[i,j]:.2f}',ha='center',va='center',fontsize=6.5,color='white' if Mat[i,j]>0.32 else '#222')
    cb=plt.colorbar(im,ax=ax,fraction=0.046,pad=0.04); cb.set_label('|corr( class/denominator , fragmentation )|',fontsize=8)
    ax.set_xlabel('normalization denominator'); ax.set_title('Fragmentation-robustness of each class ÷ denominator',fontsize=10,weight='bold')
    plt.tight_layout(); plt.savefig(os.path.join(out,'fig_normalization_matrix.png'),dpi=160); plt.close()

def write_csv(path, rows, fields):
    with atomic_open(path,'w',newline='') as f:
        w=_SafeDictWriter(f,fieldnames=fields); w.writeheader()
        for r in rows: w.writerow(r)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--banked-dir', default='cohort'); ap.add_argument('--out-dir', default='.')
    ap.add_argument('--replot', action='store_true', help='skip compute; regenerate ranking+matrix+figures from the (possibly edited) per-strain CSV')
    a=ap.parse_args(); out=a.out_dir; os.makedirs(out,exist_ok=True)
    ps_path=os.path.join(out,'normalization_per_strain.csv')
    if a.replot:
        rows=list(csv.DictReader(open(ps_path)))
        emit(f"[replot] {len(rows)} strains from {ps_path} (edits respected)")
    else:
        rows=compute_per_strain(a.banked_dir)
        fields=['sid','organism','contigs','genome_Mbp','raw_BGC','corrected_BGC']+[f'cls_{c}' for c in CLASSES]+[f'den_{d}' for d in DEN_CLASSES]
        write_csv(ps_path, rows, fields); emit(f"[compute] {len(rows)} strains -> {ps_path}")
    ranking, matrix, dens = derive(rows)
    write_csv(os.path.join(out,'normalization_class_ranking.csv'), ranking, ['class','n_total','corr_fragmentation','regime'])
    write_csv(os.path.join(out,'normalization_matrix.csv'), matrix, ['class','raw']+dens)
    plot(ranking, matrix, dens, out)
    atomic_write_text(os.path.join(out,'normalization_recipe.md'), RECIPE.format(n=len(rows),dens=', '.join(dens)))
    emit(f"  ranking ({len(ranking)} classes) + matrix + 2 figures + recipe written to {out}")

RECIPE='''# Normalization figures — data & replot recipe

Generated from a {n}-strain cohort. Two figures, each fully regenerable from the CSVs below.

## Files
- `normalization_per_strain.csv` — **the editable source**. One row per strain: contig count, per-class BGC
  counts (`cls_*`), and denominator counts (`den_*`). Everything else derives from this.
- `normalization_class_ranking.csv` — data behind **fig_class_fragmentation.png** (one row per class:
  total count, corr with fragmentation, regime).
- `normalization_matrix.csv` — data behind **fig_normalization_matrix.png** (class x denominator -> |corr of
  the normalized ratio with fragmentation|; lower = more fragmentation-robust).

## What the figures show
- **fig_class_fragmentation.png**: how each BGC class's raw count tracks assembly fragmentation. Positive =
  inflated by fragmentation (large modular classes split across contigs); near zero = robust; negative =
  under-counted in fragmented assemblies (needs complete clusters to detect).
- **fig_normalization_matrix.png**: for each class, which denominator best removes the fragmentation signal.
  Denominators tested: {dens}.

## Add / remove data, then replot (e.g. a last-minute PI drop)
1. Edit `normalization_per_strain.csv` — delete a strain's row to drop it, or paste a new row to add one.
2. Re-run: `python tools/build_normalization_matrix.py --out-dir <this-dir> --replot`
3. The ranking, matrix, and both figures regenerate from the edited CSV — no recompute from the cohort,
   so a removed strain disappears from every output consistently.

To rebuild from the full cohort instead (picking up new strains banked since), drop `--replot`.

## Figure-style note
Figures carry data only (color, axes, numeric labels, neutral titles). All interpretation lives in
`Sapote_Figure_Captions.md` and any presentation-time overlays you add in PowerPoint/BioRender.
'''

if __name__=='__main__': main()
