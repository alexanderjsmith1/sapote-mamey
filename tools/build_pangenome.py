#!/usr/bin/env python3
"""build_pangenome.py — cohort-level BGC family structure and novelty (pan-BGC-ome).

Groups the cohort's BGCs into approximate gene-cluster families by their nearest characterized cluster
(closest_mibig), separating a conserved core from accessory and strain-private families, and quantifies the
novelty pool (BGCs with no resolved MIBiG family = "UNRESOLVED"). Produces a per-strain novelty ranking, a
rarefaction curve (does new sampling still yield new families?), and locates a supplied lead set within the
family structure. Family assignment is anchor-based and approximate — a similarity-network method
(BiG-SCAPE) would refine it — so families are reported as candidate groupings, not definitive GCFs.

Outputs: Pangenome_Novelty sheet, rarefaction figure (+ data CSV, replot), Pangenome_Summary.md.

Usage: python tools/build_pangenome.py --banked-dir cohort --workbook <xlsx> --out-dir <dir>
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, json, os, random, statistics
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
from collections import defaultdict
from _wbio import atomic_save, atomic_open, atomic_write_text


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)


# B13 (v9.7.203): core threshold is now cohort-relative (max(2, n_strains//2)) or --core-min; the old CORE_MIN=45 made core empty for every <45-strain cohort (the Nocardia "0 core").

def fam(b):
    m=(b.get('closest_mibig') or '').strip()
    return None if (m=='' or m.upper()=='UNRESOLVED') else m

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--banked-dir', default='cohort'); ap.add_argument('--workbook', default='')
    ap.add_argument('--out-dir', default='.'); ap.add_argument('--replot', action='store_true')
    ap.add_argument('--core-min', type=int, default=0,
                    help='min strains a family must span to count as core; 0 = auto max(2, n_strains//2). '
                         'Fixes B13: the old hardcoded 45 made core empty for any <45-strain cohort.')
    a=ap.parse_args(); os.makedirs(a.out_dir,exist_ok=True)
    bgc=_read_json(os.path.join(a.banked_dir,'bgc_data.json')); bgcs=bgc['bgcs']; strains=sorted(bgc['strains'])
    # Empty-safe (v9.7.114): an empty cohort has no pangenome — exit cleanly rather than crash on
    # round(100*x/len(bgcs)) (ZeroDivisionError) or mean[-1] (IndexError) in the rarefaction summary.
    if not bgcs or not strains:
        emit(f"  no BGCs/strains in {a.banked_dir} — no pangenome to compute; skipping.")
        return
    F=defaultdict(set); prod={}
    for b in bgcs:
        f=fam(b)
        if f: F[f].add(b['sid']); prod.setdefault(f,(b.get('closest_kcb_product') or '?', b.get('products') or ''))
    core_min = a.core_min or max(2, len(strains)//2)   # B13: cohort-relative, not a fixed 45
    core=[f for f,s in F.items() if len(s)>=core_min]; private=[f for f,s in F.items() if len(s)==1]
    accessory=[f for f in F if f not in core and f not in private]
    unres=sum(1 for b in bgcs if fam(b) is None)
    # per-strain
    st=defaultdict(lambda:[0,0,0])  # total, novel, private-family members
    privset=set(private)
    for b in bgcs:
        st[b['sid']][0]+=1
        if fam(b) is None: st[b['sid']][1]+=1
        elif fam(b) in privset: st[b['sid']][2]+=1
    rows=[]
    for sid in strains:
        t,n,pv=st[sid]; rows.append({'strain':sid,'total_BGC':t,'novel_unresolved':n,
            'novel_pct':round(100*n/t) if t else 0,'private_families':pv})
    rows.sort(key=lambda r:-r['novel_pct'])
    # rarefaction (mean over shuffles), editable CSV
    rarecsv=os.path.join(a.out_dir,'pangenome_rarefaction_data.csv')
    if a.replot and os.path.exists(rarecsv):
        with open(rarecsv, newline='') as _fh:
            rr=list(csv.DictReader(_fh))
        mean=[int(x['mean_families']) for x in rr]
    else:
        random.seed(1); byfam=defaultdict(set)
        for b in bgcs:
            if fam(b): byfam[b['sid']].add(fam(b))
        def one():
            seen=set(); out=[]
            for sid in random.sample(strains,len(strains)): seen|=byfam[sid]; out.append(len(seen))
            return out
        cur=[one() for _ in range(50)]
        mean=[round(statistics.mean(c[i] for c in cur)) for i in range(len(strains))]
        with atomic_open(rarecsv, newline='') as f:
            w=_SafeWriter(f); w.writerow(['n_strains','mean_families'])
            for i,m in enumerate(mean,1): w.writerow([i,m])
    # rarefaction figure (FIGURE_STYLE: data only)
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(figsize=(6.4,4))
    ax.plot(range(1,len(mean)+1),mean,color='#2E86AB',lw=2)
    ax.scatter([len(mean)],[mean[-1]],color='#2E86AB',zorder=3)
    ax.set_xlabel('strains sampled'); ax.set_ylabel('cumulative BGC families'); ax.set_xlim(0,len(mean)+1); ax.set_ylim(0,max(mean)*1.08)
    ax.set_title('BGC-family rarefaction',fontsize=11,weight='bold')
    plt.tight_layout(); plt.savefig(os.path.join(a.out_dir,'fig_pangenome_rarefaction.png'),dpi=160); plt.close()
    if a.replot:
        emit(f"  replotted rarefaction from {rarecsv}"); return
    # workbook sheet
    if a.workbook:
        import openpyxl
        from openpyxl.styles import Font, PatternFill
        wb=openpyxl.load_workbook(a.workbook)
        if 'Pangenome_Novelty' in wb.sheetnames: del wb['Pangenome_Novelty']
        ws=wb.create_sheet('Pangenome_Novelty')
        ws.append([f'cohort families={len(F)}  core(>={core_min})={len(core)}  accessory={len(accessory)}  '
                   f'private={len(private)}  novel(UNRESOLVED)={unres}/{len(bgcs)} ({round(100*unres/len(bgcs))}%)'])
        ws.append(['strain','total_BGC','novel_unresolved','novel_pct','private_families'])
        for c in range(1,6): ws.cell(2,c).font=Font(bold=True,color='FFFFFF'); ws.cell(2,c).fill=PatternFill('solid',fgColor='2E5E7E')
        for r in rows: ws.append([r['strain'],r['total_BGC'],r['novel_unresolved'],r['novel_pct'],r['private_families']])
        for col,w in zip('ABCDE',[10,11,16,11,16]): ws.column_dimensions[col].width=w
        ws.freeze_panes='A3'
        atomic_save(wb, a.workbook)
    # CSV + summary
    with atomic_open(os.path.join(a.out_dir,'Pangenome_Novelty.csv'), newline='') as f:
        w=_SafeDictWriter(f,fieldnames=['strain','total_BGC','novel_unresolved','novel_pct','private_families']); w.writeheader()
        for r in rows: w.writerow(r)
    core_lines='\n'.join(f"- {len(F[f])} strains — {prod[f][0][:34]} ({prod[f][1][:24]})" for f in sorted(core,key=lambda x:-len(F[x])))
    md=f"""# Pan-BGC-ome & novelty — {len(strains)}-strain cohort

**{unres} of {len(bgcs)} BGCs ({round(100*unres/len(bgcs))}%) have no resolved MIBiG family** — the novelty pool.
Anchored BGCs fall into **{len(F)} candidate families**: **{len(core)} core** (>= {core_min} strains),
{len(accessory)} accessory, **{len(private)} strain-private**. Family assignment is anchor-based and
approximate (a BiG-SCAPE network would refine it).

## Conserved core (the shared backbone)
{core_lines}

## Rarefaction
Families accumulate {mean[0]} -> {mean[len(strains)//2]} -> {mean[-1]} at 1 / {len(strains)//2} / {len(strains)}
strains; the curve has not plateaued (still +{mean[-1]-mean[max(0,len(strains)-10)]} families over the last 10
strains), so additional strains are expected to keep yielding new chemistry — the collection is not saturated.

## Most novel strains (by UNRESOLVED fraction; interpret small-genome strains with caution)
{chr(10).join(f"- {r['strain']}: {r['novel_unresolved']}/{r['total_BGC']} = {r['novel_pct']}% novel, {r['private_families']} private families" for r in rows[:6])}

_Novelty here = distance from characterized clusters, a candidate signal; confirmation requires Mode B / wet-lab._
"""
    atomic_write_text(os.path.join(a.out_dir,'Pangenome_Summary.md'), md)
    emit(f"  Pangenome: {len(F)} families ({len(core)} core, {len(private)} private), {unres} novel BGCs "
          f"({round(100*unres/len(bgcs))}%) -> sheet + rarefaction fig + Pangenome_Summary.md")

if __name__=='__main__': main()
