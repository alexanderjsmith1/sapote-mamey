#!/usr/bin/env python3
"""build_overview_figures.py — two cohort-level overview figures for Sapote–Mamey.

(1) Spider/radar — chemical-defense profile: % of cohort strains carrying each BGC class.
(2) Venn — evidence convergence: KCB-anchored (A) ∩ regulator-bearing (B) ∩ self-resistance (C) over all BGCs;
    the triple overlap is the best-supported core, of which the 6 Class-A leads are the chemistry-CONFIRM subset.

Data-only figures (FIGURE_STYLE): no interpretive arrows/callouts; reading goes in the caption. Each ships its
source CSV and supports --replot. matplotlib_venn is not required — the Venn is drawn directly.

Usage: python tools/build_overview_figures.py --banked-dir cohort --out-dir figures [--replot]
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, os, json, csv, math
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import matplotlib; matplotlib.use('Agg')


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)

import matplotlib.pyplot as plt
from matplotlib.patches import Circle

RADAR_AXES=[('Terpene','terpene'),('PKS','pks'),('RiPP','ripp'),('NRPS','nrps'),('T1PKS','t1pks'),
 ('Siderophore','siderophore'),('Ectoine','ectoine'),('Halogenated','halogenated'),('T2PKS','t2pks'),
 ('Butyrolactone','butyrolactone'),('Lanthipeptide','lanthipeptide'),('NRP-metallophore','nrp-metallophore'),
 ('HCN','hydrogen-cyanide'),('Lassopeptide','lassopeptide')]

def compute(banked):
    bgc=_read_json(os.path.join(banked,'bgc_data.json')); strains=bgc['strains']; bgcs=bgc['bgcs']
    from mamey.figure_policy import omit_saccharides
    bgcs=omit_saccharides(bgcs)  # figure policy: pure-saccharide regions never plotted (text-only)
    deep=_read_json(os.path.join(banked,'deep_data.json')); prof={(p['sid'],p['bgc_id']):p for p in deep['bgc_profile']}
    N=len(strains)
    if N == 0:
        # Empty-safe (v9.7.114): no strains means no radar percentages — round(100*x/N) would divide
        # by zero. Raise a clear error the caller handles, rather than a bare ZeroDivisionError.
        raise ValueError("build_overview_figures: cohort has 0 strains — nothing to plot.")
    radar=[]
    for lab,k in RADAR_AXES:
        s=set(b['sid'] for b in bgcs if k in (b.get('products') or '').lower())
        radar.append((lab,round(100*len(s)/N)))
    def dark(b): return (b.get('closest_mibig') or '').strip().upper() in ('','UNRESOLVED')
    A=set();B=set();C=set()
    for b in bgcs:
        kk=(b['sid'],b['bgc_id']); p=prof.get(kk,{})
        if not dark(b): A.add(kk)
        if (p.get('Regulator') or 0)>0: B.add(kk)
        if (p.get('resistance_tier') or '').startswith(('T1','T2')): C.add(kk)
    venn={'A_only':len(A-B-C),'B_only':len(B-A-C),'C_only':len(C-A-B),'AB':len((A&B)-C),
          'AC':len((A&C)-B),'BC':len((B&C)-A),'ABC':len(A&B&C),'A':len(A),'B':len(B),'C':len(C),'N':len(bgcs)}
    return radar, venn, N

def radar_fig(radar, N, out):
    labels=[x[0] for x in radar]; vals=[x[1] for x in radar]
    ang=[n/len(labels)*2*math.pi for n in range(len(labels))]; ang+=ang[:1]; v=vals+vals[:1]
    fig=plt.figure(figsize=(8,8)); ax=plt.subplot(111,polar=True)
    ax.set_theta_offset(math.pi/2); ax.set_theta_direction(-1)
    ax.set_xticks(ang[:-1]); ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylim(0,100); ax.set_yticks([20,40,60,80,100]); ax.set_yticklabels(['20','40','60','80','100%'],fontsize=8,color='#888')
    ax.plot(ang,v,color='#2E5E7E',linewidth=2); ax.fill(ang,v,color='#2E86AB',alpha=0.25)
    for a_,val in zip(ang[:-1],vals): ax.annotate(f"{val}",(a_,val),fontsize=8,ha='center',va='center',color='#1a1a2e')
    ax.set_title(f"Sapote–Mamey cohort chemical-defense profile\n(% of {N} strains carrying each BGC class)",fontsize=12,pad=22)
    plt.tight_layout(); plt.savefig(out,dpi=150,bbox_inches='tight'); plt.close()

def venn_fig(vn, out):
    fig,ax=plt.subplots(figsize=(8.5,7.5)); ax.set_xlim(-2,2); ax.set_ylim(-2,2); ax.axis('off'); ax.set_aspect('equal')
    cols=['#2E86AB','#E59866','#2E7D32']; r=0.95
    cen={'A':(-0.42,0.32),'B':(0.42,0.32),'C':(0.0,-0.42)}
    for k,col in zip(['A','B','C'],cols):
        ax.add_patch(Circle(cen[k],r,facecolor=col,alpha=0.32,edgecolor=col,linewidth=1.5))
    pos={'A_only':(-1.05,0.62),'B_only':(1.05,0.62),'C_only':(0.0,-1.18),'AB':(0.0,0.78),
         'AC':(-0.72,-0.42),'BC':(0.72,-0.42),'ABC':(0.0,-0.02)}
    for k,(x,y) in pos.items():
        big = k=='ABC'
        ax.text(x,y,f"{vn[k]:,}",ha='center',va='center',
                fontsize=15 if big else 12, fontweight='bold' if big else 'normal',
                color='#1a1a2e')
    ax.text(-1.15,1.32,f"A · KCB-anchored\n(named family)  n={vn['A']:,}",fontsize=10,color=cols[0],fontweight='bold',ha='left')
    ax.text(1.15,1.32,f"B · regulator-bearing\nn={vn['B']:,}",fontsize=10,color=cols[1],fontweight='bold',ha='right')
    ax.text(0.0,-1.62,f"C · self-resistance (T1/T2)  n={vn['C']:,}",fontsize=10,color=cols[2],fontweight='bold',ha='center')
    ax.set_title(f"Sapote–Mamey evidence convergence across {vn['N']:,} BGCs\n"
                 f"triple overlap (n={vn['ABC']}) = best-supported core; the 6 Class-A leads are its chemistry-CONFIRM subset",
                 fontsize=11.5,pad=10)
    plt.tight_layout(); plt.savefig(out,dpi=150,bbox_inches='tight'); plt.close()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--banked-dir',default='cohort'); ap.add_argument('--out-dir',default='figures'); ap.add_argument('--replot',action='store_true')
    a=ap.parse_args(); os.makedirs(a.out_dir,exist_ok=True)
    rcsv=os.path.join(a.out_dir,'fig_cohort_radar_data.csv'); vcsv=os.path.join(a.out_dir,'fig_convergence_venn_data.csv')
    if a.replot and os.path.exists(rcsv) and os.path.exists(vcsv):
        radar=[(r['class'],int(r['pct_strains'])) for r in csv.DictReader(open(rcsv))]
        vn={r['region']:int(r['n_bgcs']) for r in csv.DictReader(open(vcsv))}
        # v9.7.115: derive cohort size from the persisted N_strains row. A pre-v9.7.115 CSV lacks it;
        # rather than silently claim a hardcoded 59, fail loudly so a stale figure can't be minted.
        if 'N_strains' not in vn:
            raise SystemExit(f"  {vcsv} predates v9.7.115 (no N_strains row) — regenerate (drop --replot) "
                             "so the cohort size is recorded, then replot.")
        N=vn.pop('N_strains')
        vn['N']=vn.get('N',sum(vn[k] for k in ['A_only','B_only','C_only','AB','AC','BC','ABC']))
    else:
        try:
            radar,vn,N=compute(a.banked_dir)
        except ValueError as e:
            emit(f"  {e}"); return
        with open(rcsv,'w',newline='') as f:
            w=_SafeWriter(f); w.writerow(['class','pct_strains']); [w.writerow([l,v]) for l,v in radar]
        with open(vcsv,'w',newline='') as f:
            w=_SafeWriter(f); w.writerow(['region','n_bgcs']); [w.writerow([k,vn[k]]) for k in ['A','B','C','A_only','B_only','C_only','AB','AC','BC','ABC','N']]
            w.writerow(['N_strains', N])  # v9.7.115: persist cohort size so --replot uses real N, not a hardcoded fallback
    radar_fig(radar,N,os.path.join(a.out_dir,'fig_cohort_radar.png'))
    venn_fig(vn,os.path.join(a.out_dir,'fig_convergence_venn.png'))
    emit(f"  wrote fig_cohort_radar.png + fig_convergence_venn.png (+ CSVs) → {a.out_dir}")

if __name__=='__main__': main()
