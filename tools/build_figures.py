#!/usr/bin/env python3
"""build_figures.py — reproducible figure module for the Sapote-Mamey bundle.

Generates the cohort figures that don't already have a reproducible home (the normalization figures live in
build_normalization_matrix.py). Every figure follows two rules:
  - FIGURE_STYLE: data only — color, axes, numeric labels, neutral title; NO arrows/overlay callouts/
    interpretive titles. Interpretation goes in the captions file.
  - FIGURE_REPRODUCIBILITY: each figure ships with an editable source CSV and a --replot path, so a
    last-minute edit (e.g. a PI drops a strain/lead) is a CSV edit + regenerate, not a re-derivation.

Figures: chitinase_load, chitinase_normalization, chemistry_landscape, priority_leads_tierA.

Usage:
  python tools/build_figures.py --banked-dir cohort --workbook <xlsx> --out-dir figures      # compute+plot
  python tools/build_figures.py --out-dir figures --replot                                   # replot from edited CSVs
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
from collections import Counter, defaultdict
import sys as _sys, os as _os

PUBLICATION_RASTER_DPI = 300


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _wbio import atomic_write_text

# ---------- data extraction (writes one editable source CSV per figure) ----------
def data_chitinase(banked):
    bgc=_read_json(os.path.join(banked,'bgc_data.json')); chit=_read_json(os.path.join(banked,'chitinase.json'))
    strains=bgc['strains']; bgcs=bgc['bgcs']; bystrain=Counter(b['sid'] for b in bgcs)
    ecto=Counter(); napaa=Counter()
    for b in bgcs:
        p=(b.get('products') or '').lower()
        if 'ectoine' in p: ecto[b['sid']]+=1
        if 'napaa' in p: napaa[b['sid']]+=1
    rows=[]
    for sid,c in chit.items():
        if sid not in strains: continue
        g=strains[sid].get('organism','').split()[0] if strains[sid].get('organism') else 'unclassified'
        if g.lower() in ('not','unknown',''): g='unclassified'
        den=ecto.get(sid,0)+napaa.get(sid,0)
        rows.append({'strain':sid,'genus':g,'chitinase':c['chitinase'],'chitin_binding':c['chitin_binding'],
                     'total_BGC':bystrain[sid],'contigs':strains[sid].get('contigs',0),'ecto_napaa':den,
                     'chit_per_unit':round(c['chitinase']/den,3) if den>=1 else ''})
    return rows, ['strain','genus','chitinase','chitin_binding','total_BGC','contigs','ecto_napaa','chit_per_unit']

def data_chemistry(banked):
    bgc=_read_json(os.path.join(banked,'bgc_data.json')); markers=_read_json(os.path.join(banked,'bgc_markers.json'))
    bgcs=bgc['bgcs']; N=len(bgc['strains']); by_id={(b['sid'],b['bgc_id']):b for b in bgcs}
    gen=[];fl=[]
    for sid,bb in markers.items():
        for bid,m in bb.items():
            if any('ene' in x.lower() for x in m.get('cctt',[])) or 'enediyne' in [x.lower() for x in m.get('tigrfam',[])]:
                prods=(by_id.get((sid,bid),{}).get('products') or '')
                (fl if ('hglE' in prods or 'hglD' in prods) else gen).append((sid,bid))
    rows=[{'panel':'enediyne_stage','label':'raw signal','value':len(gen)+len(fl)},
          {'panel':'enediyne_stage','label':'hglE false (vetoed)','value':len(fl)},
          {'panel':'enediyne_stage','label':'candidate (no hglE)','value':len(gen)}]
    # 'Mode B confirmed' row removed: no bank source feeds it; the prior value:2 was fabricated (claim-safety).
    ms=defaultdict(set)
    for sid,bb in markers.items():
        for bid,m in bb.items():
            for x in m.get('cctt',[])+m.get('tigrfam',[]):
                for t in ['phosphonate','thiopeptide','lanthipeptide','lassopeptide','tetronate','ansamycin','indolocarbazole']:
                    if t in x.lower(): ms[t].add(sid)
    ms['enediyne (genuine)']={sid for sid,_ in gen}  # real genuine-candidate strains, not a placeholder
    for k,v in sorted(ms.items(),key=lambda x:len(x[1])):
        rows.append({'panel':'class_prevalence','label':k,'value':len(v)})
    return rows, ['panel','label','value']

def data_priority(workbook):
    import openpyxl
    wb=openpyxl.load_workbook(workbook, read_only=True)
    if 'Priority_Leads' not in wb.sheetnames: return [], ['confidence','strain','BGC','products','ModeB_class','SARP','DasR','KCB','tier']
    ws=wb['Priority_Leads']; hdr=[ws.cell(1,c).value for c in range(1,ws.max_column+1)]
    rows=[]
    for r in ws.iter_rows(min_row=2,values_only=True):
        d=dict(zip(hdr,r))
        if d.get('confidence')!='A': continue
        regs=d.get('regulators') or ''
        rows.append({'confidence':'A','strain':d['strain'],'BGC':d['BGC'],'products':(d.get('products') or '')[:30],
                     'ModeB_class':d.get('ModeB_class') or '','SARP':1 if 'SARP' in regs else 0,
                     'DasR':1 if 'DasR' in regs else 0,'KCB':1 if (d.get('KCB_anchor') or '').strip() else 0,
                     'tier':1 if str(d.get('tier'))=='1' else 0})
    return rows, ['confidence','strain','BGC','products','ModeB_class','SARP','DasR','KCB','tier']

# ---------- plots (FIGURE_STYLE-compliant) ----------
def plot_chitinase_load(rows, path):
    import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    rows=sorted(rows,key=lambda r:-int(r['chitinase']))
    sids=[r['strain'] for r in rows]; chit=[int(r['chitinase']) for r in rows]; cb=[int(r['chitin_binding']) for r in rows]
    colors=['#C0392B' if r['genus']!='Streptomyces' else '#2E86AB' for r in rows]
    x=np.arange(len(rows)); fig,ax=plt.subplots(figsize=(11,4.2))
    ax.bar(x,chit,color=colors,width=0.78); ax.bar(x,cb,bottom=chit,color='#A8D0E6',width=0.78)
    strep=[int(r['chitinase']) for r in rows if r['genus']=='Streptomyces']
    if strep: ax.axhline(np.mean(strep),ls='--',lw=1,color='#888')
    ax.set_xticks(x); ax.set_xticklabels(sids,rotation=90,fontsize=5.5); ax.set_ylabel('gene count'); ax.set_xlim(-0.6,len(rows)-0.4)
    ax.set_title('Chitinolytic gene complement per strain',fontsize=11,weight='bold')
    ax.legend(handles=[Patch(color='#2E86AB',label='chitinases (GH18/GH19)'),Patch(color='#A8D0E6',label='chitin-binding'),
              Patch(color='#C0392B',label='non-Streptomyces'),plt.Line2D([0],[0],ls='--',color='#888',label='Streptomyces mean')],
              loc='upper right',fontsize=8,frameon=False)
    plt.tight_layout(); plt.savefig(path,dpi=PUBLICATION_RASTER_DPI); plt.close()

def plot_chitinase_normalization(rows, path):
    import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    have=[r for r in rows if r['chit_per_unit'] not in ('',None)]
    lc=np.log10(np.array([max(int(r['contigs']),1) for r in rows],float)); ch=np.array([int(r['chitinase']) for r in rows],float)
    lc2=np.log10(np.array([max(int(r['contigs']),1) for r in have],float)); nv=np.array([float(r['chit_per_unit']) for r in have])
    fig,(a1,a2)=plt.subplots(1,2,figsize=(10,4.2),sharex=True)
    a1.scatter(lc,ch,s=26,color='#C0392B',alpha=0.75)
    if len(lc)>1: m,b=np.polyfit(lc,ch,1); xs=np.array([lc.min(),lc.max()]); a1.plot(xs,m*xs+b,color='#888',lw=1.2)
    a1.set_xlabel('log10 contig count'); a1.set_ylabel('raw chitinase count'); a1.set_title('Raw chitinase vs fragmentation',fontsize=10)
    a2.scatter(lc2,nv,s=26,color='#2E86AB',alpha=0.8)
    if len(lc2)>1: m2,b2=np.polyfit(lc2,nv,1); xs=np.array([lc2.min(),lc2.max()]); a2.plot(xs,m2*xs+b2,color='#888',lw=1.2)
    a2.set_xlabel('log10 contig count'); a2.set_ylabel('chitinase / (ecto+napaa)'); a2.set_title('Normalized chitinase vs fragmentation',fontsize=10)
    plt.tight_layout(); plt.savefig(path,dpi=PUBLICATION_RASTER_DPI); plt.close()

def plot_chemistry(rows, path):
    import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    ene=[r for r in rows if r['panel']=='enediyne_stage']; pre=[r for r in rows if r['panel']=='class_prevalence']
    fig,(a1,a2)=plt.subplots(1,2,figsize=(11,4.3))
    cols=['#999','#C0392B','#E59866','#27AE60']; vals=[int(r['value']) for r in ene]
    a1.bar(range(len(ene)),vals,color=cols[:len(ene)],width=0.7)
    for i,v in enumerate(vals): a1.text(i,v+0.3,str(v),ha='center',fontsize=9)
    a1.set_xticks(range(len(ene))); a1.set_xticklabels([r['label'] for r in ene],fontsize=8,rotation=12,ha='right')
    a1.set_ylabel('BGCs'); a1.set_title('Enediyne signal by veto stage',fontsize=10,weight='bold')
    y=np.arange(len(pre)); cnts=[int(r['value']) for r in pre]
    a2.barh(y,cnts,color='#2E86AB',height=0.7)
    for i,c in enumerate(cnts): a2.text(c+0.3,i,str(c),va='center',fontsize=8)
    a2.set_yticks(y); a2.set_yticklabels([r['label'] for r in pre],fontsize=8.5); a2.set_xlabel('strains carrying')
    a2.set_title('Specialist class prevalence',fontsize=10,weight='bold')
    plt.tight_layout(); plt.savefig(path,dpi=PUBLICATION_RASTER_DPI); plt.close()

def plot_priority(rows, path):
    import csv as _csv, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    if not rows:
        fig,ax=plt.subplots(figsize=(8,2)); ax.text(0.5,0.5,'no TIER_A leads',ha='center'); ax.axis('off')
        plt.savefig(path,dpi=PUBLICATION_RASTER_DPI); plt.close(); return
    # locate the full score distribution (ships beside the figure or in the parent outputs dir)
    out=os.path.dirname(path); dist=None
    for cand in (os.path.join(out,'Priority_Scores_All.csv'), os.path.join(os.path.dirname(out),'Priority_Scores_All.csv')):
        if os.path.exists(cand): dist=list(_csv.DictReader(open(cand))); break
    fig=plt.figure(figsize=(12, 0.62*len(rows)+2.2))
    gs=fig.add_gridspec(1,2,width_ratios=[1.0,1.15],wspace=0.55)
    # ---- Panel A: ranked field (the contrast) ----
    a0=fig.add_subplot(gs[0,0])
    if dist:
        COL={'A':'#C0392B','B':'#E59866','C':'#F4D03F','':'#CCCCCC'}
        ranks=[int(d['rank']) for d in dist]; scores=[float(d['score']) for d in dist]
        cls=[d.get('confidence','') or '' for d in dist]
        for cc in ['','C','B','A']:
            xs=[r for r,c in zip(ranks,cls) if c==cc]; ys=[s for s,c in zip(scores,cls) if c==cc]
            a0.scatter(xs,ys,s=(34 if cc=='A' else 10),color=COL[cc],
                       edgecolor=('black' if cc=='A' else 'none'),linewidth=0.5,zorder=(5 if cc=='A' else 2),
                       label={'A':'Class A (6)','B':'Class B','C':'Class C','':'below threshold'}[cc])
        a0.set_xscale('log'); a0.set_xlabel('lead rank (log scale)'); a0.set_ylabel('composite priority score')
        a0.set_title(f'Priority score across all {len(dist)} evaluated leads',fontsize=10,weight='bold')
        a0.annotate('6 leads rise to the top',xy=(3,scores[0]),xytext=(6,scores[0]-0.55),fontsize=8.5,color='#C0392B')
        a0.legend(loc='lower left',fontsize=7.5,frameon=False)
    else:
        a0.text(0.5,0.5,'score distribution unavailable\n(run build_priority_leads first)',ha='center',va='center',fontsize=9); a0.axis('off')
    # ---- Panel B: converging-evidence matrix (the why) ----
    a1=fig.add_subplot(gs[0,1])
    axes=['ModeB\nCONFIRM','SARP','DasR','KCB\nanchor','Tier-1']
    M=np.array([[1, int(r['SARP']), int(r['DasR']), int(r['KCB']), int(r['tier'])] for r in rows],float)
    labels=[f"{r['strain']} {r['BGC']}" for r in rows]
    a1.imshow(M,cmap='Greens',vmin=0,vmax=1.3,aspect='auto')
    a1.set_xticks(range(len(axes))); a1.set_xticklabels(axes,fontsize=8.5)
    a1.set_yticks(range(len(rows))); a1.set_yticklabels(labels,fontsize=8)
    for i in range(len(rows)):
        for j in range(len(axes)):
            a1.text(j,i,'✓' if M[i,j] else '·',ha='center',va='center',color=('#1B5E20' if M[i,j] else '#BBBBBB'),fontsize=11,weight='bold')
    for i,r in enumerate(rows): a1.text(len(axes)-0.42, i, '  '+(r['ModeB_class'] or ''), va='center', fontsize=7.5, color='#444')
    a1.set_title('Class A leads — converging evidence',fontsize=10,weight='bold')
    a1.set_xticks(np.arange(-.5,len(axes),1),minor=True); a1.set_yticks(np.arange(-.5,len(rows),1),minor=True)
    a1.grid(which='minor',color='white',linewidth=2); a1.tick_params(which='minor',length=0)
    plt.tight_layout(); plt.savefig(path,dpi=PUBLICATION_RASTER_DPI,bbox_inches='tight'); plt.close()

def _rescue_from_banks(banked):
    """Fallback: compute the Fragment_Rescue_Tiers rows directly from banks, so fig_contig_rescue works on any
    banked cohort with no derived-sheet prerequisite. Mirrors build_dapr_rescue_sheets.py: EFLS/linkage pairs
    from rggmci_full.json (n_pairs), Frag_Loss from edge_status (raw - corrected), megasynth proxied by large (>=80kb) PKS/NRPS
    loci (vs the FLBR scan), tier via the same rtier thresholds. n50 is not in the banks, so the 'A' (intact-backbone) tier — which
    requires n50 >= 1 Mb — cannot be assigned from banks; banked tiers are efls-driven (D/C/B)."""
    from collections import Counter, defaultdict
    bgc=_read_json(os.path.join(banked,'bgc_data.json'))
    rg=_read_json(os.path.join(banked,'rggmci_full.json')) if os.path.exists(os.path.join(banked,'rggmci_full.json')) else {}
    edge=defaultdict(Counter); mega=Counter()
    for b in bgc['bgcs']:
        sid=b['sid']; edge[sid][b.get('edge_status')]+=1
        if (b.get('length_kb') or 0)>=80 and any(k in str(b.get('products','')).lower() for k in ('pks','nrps')): mega[sid]+=1
    def rtier(n50, efls):                         # mirrors build_dapr_rescue_sheets.rtier
        if n50 and n50>=1_000_000: return 'A'
        if efls<20: return 'D'
        if efls>=600: return 'B'
        return 'C'
    out=[]
    for sid in edge:
        I=edge[sid]['Interior']; E=edge[sid]['Edge']; F=edge[sid]['Full-contig']; raw=I+E+F
        corrected=I+0.5*E+0.25*F; frag_loss=round(raw-corrected,2)
        efls=int((rg.get(sid,{}) or {}).get('n_pairs') or 0)
        out.append({'strain':sid,'efls':efls,'frag':frag_loss,'megasynth':int(mega.get(sid,0)),
                    'tier':rtier(0,efls),'is_classA':1 if rtier(0,efls)=='A' else 0})  # real tier rule, not a placeholder set
    return out

def data_rescue(workbook, banked_dir=None):
    import openpyxl
    headers=['strain','efls','frag','megasynth','tier','is_classA']
    if workbook and os.path.exists(workbook):
        wb=openpyxl.load_workbook(workbook, read_only=True)
        if 'Fragment_Rescue_Tiers' in wb.sheetnames:
            ws=wb['Fragment_Rescue_Tiers']; rows=list(ws.iter_rows(values_only=True)); h=list(rows[0]); ix={c:i for i,c in enumerate(h)}
            out=[]
            for r in rows[1:]:
                s=r[ix['strain']]
                if not s: continue
                out.append({'strain':s,'efls':r[ix['EFLS_Pairs']] or 0,'frag':r[ix['Frag_Loss']] or 0,
                            'megasynth':r[ix['FLBR_Megasynth']] or 0,'tier':r[ix['Tier']],
                            'is_classA':1 if str(r[ix['Tier']]).strip()=='A' else 0})  # from the real Tier column
            return out, headers
    # sheet absent -> compute from banks (decoupled fallback) instead of silently returning 0 rows
    if banked_dir:
        return _rescue_from_banks(banked_dir), headers
    return [], headers

def plot_rescue(rows, path):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    if not rows:
        fig,ax=plt.subplots(figsize=(8,2)); ax.text(0.5,0.5,'no rescue data',ha='center'); ax.axis('off'); plt.savefig(path,dpi=PUBLICATION_RASTER_DPI); plt.close(); return
    TCOL={'A':'#27AE60','B':'#E59866','C':'#C0392B','D':'#888888'}
    fig,ax=plt.subplots(figsize=(8,5.2))
    for t in ['D','A','C','B']:
        sub=[r for r in rows if r['tier']==t and int(r['is_classA'])==0]
        if sub: ax.scatter([float(r['efls']) for r in sub],[float(r['frag']) for r in sub],
                   s=[max(float(r['megasynth'])/4,8) for r in sub], c=TCOL.get(t,'#888'), alpha=0.55, edgecolor='none', label=f'Tier {t}')
    ca=[r for r in rows if int(r['is_classA'])==1]
    ax.scatter([float(r['efls']) for r in ca],[float(r['frag']) for r in ca],
               s=[max(float(r['megasynth'])/4,8) for r in ca], facecolor='none', edgecolor='#1A5276', linewidth=2.2, zorder=6, label='Class-A lead')
    for r in ca: ax.annotate(r['strain'],(float(r['efls']),float(r['frag'])),fontsize=7,xytext=(4,4),textcoords='offset points',color='#1A5276')
    ax.set_xlabel('edge-fragment linking signal (EFLS pairs)'); ax.set_ylabel('fragmentation loss (raw − corrected BGCs)')
    ax.set_title('Contig-rescue landscape (point size = megasynthase fragments)',fontsize=11,weight='bold')
    ax.legend(loc='upper left',fontsize=8,frameon=False)
    plt.tight_layout(); plt.savefig(path,dpi=PUBLICATION_RASTER_DPI); plt.close()


def data_saccharide_adjusted(banked):
    import json as _j
    from collections import defaultdict
    bgc=_j.load(open(os.path.join(banked,'bgc_data.json'))); strains=bgc['strains']; bgcs=bgc['bgcs']
    from mamey.figure_policy import is_pure_saccharide
    def pure(b): return is_pure_saccharide(b.get('products'))
    raw=defaultdict(int); adj=defaultdict(int)
    for b in bgcs:
        raw[b['sid']]+=1
        if not pure(b): adj[b['sid']]+=1
    rows=[{'strain':s,'raw_BGC':raw[s],'specialist_BGC':adj[s],'pure_saccharide':raw[s]-adj[s]} for s in sorted(strains)]
    return rows, ['strain','raw_BGC','specialist_BGC','pure_saccharide']

def plot_saccharide_adjusted(rows, path):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, numpy as np
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    rows=sorted(rows,key=lambda r:-int(r['raw_BGC']))
    sids=[r['strain'] for r in rows]; spec=[int(r['specialist_BGC']) for r in rows]; sac=[int(r['pure_saccharide']) for r in rows]
    x=np.arange(len(sids)); fig,ax=plt.subplots(figsize=(11,4.4))
    ax.bar(x,spec,color='#2E86AB',width=0.82,label='specialist BGCs (reported)')
    ax.bar(x,sac,bottom=spec,color='#D5C0A1',width=0.82,label='pure-saccharide (machinery, omitted)')
    ax.set_xticks(x); ax.set_xticklabels(sids,rotation=90,fontsize=4.5); ax.set_xlim(-0.6,len(sids)-0.4)
    ax.set_ylabel('BGC count'); ax.set_title('Per-strain BGCs: specialist vs omitted pure-saccharide',fontsize=11,weight='bold')
    ax.legend(loc='upper right',fontsize=8,frameon=False)
    plt.tight_layout(); plt.savefig(path,dpi=PUBLICATION_RASTER_DPI); plt.close()

FIGS={
 'fig_chitinase_load':        (lambda a: data_chitinase(a.banked_dir), plot_chitinase_load),
 'fig_chitinase_normalization':(lambda a: data_chitinase(a.banked_dir), plot_chitinase_normalization),
 'fig_chemistry_landscape':   (lambda a: data_chemistry(a.banked_dir), plot_chemistry),
 'fig_priority_leads_tierA':  (lambda a: data_priority(a.workbook), plot_priority),
 'fig_contig_rescue':         (lambda a: data_rescue(a.workbook, a.banked_dir), plot_rescue),
 'fig_saccharide_adjusted':   (lambda a: data_saccharide_adjusted(a.banked_dir), plot_saccharide_adjusted),
}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--banked-dir', default='cohort'); ap.add_argument('--workbook', default='')
    ap.add_argument('--out-dir', default='figures'); ap.add_argument('--replot', action='store_true')
    a=ap.parse_args(); os.makedirs(a.out_dir,exist_ok=True)
    for name,(extract,plot) in FIGS.items():
        csvp=os.path.join(a.out_dir,name+'_data.csv')
        if a.replot:
            if not os.path.exists(csvp): emit(f"  [skip] {name}: no {csvp}"); continue
            rows=list(csv.DictReader(open(csvp)))
        else:
            rows,fields=extract(a)
            with open(csvp,'w',newline='') as f:
                w=_SafeDictWriter(f,fieldnames=fields); w.writeheader()
                for r in rows: w.writerow(r)
        plot(rows, os.path.join(a.out_dir,name+'.png'))
        emit(f"  {name}: {len(rows)} rows -> {name}.png + {name}_data.csv")
    atomic_write_text(os.path.join(a.out_dir,'figures_recipe.md'), RECIPE)
    emit(f"  recipe -> {a.out_dir}/figures_recipe.md")

RECIPE='''# Sapote-Mamey figures — data & replot recipe

Each figure ships with an editable `*_data.csv` and is regenerable from it.

## Regenerate after an edit (e.g. a PI drops a strain or a lead)
1. Edit the figure's `*_data.csv` (delete a row to drop a point; edit a value).
2. `python tools/build_figures.py --out-dir <this-dir> --replot`
3. All figures regenerate from the edited CSVs — no recompute from the cohort.

Drop `--replot` to rebuild from the full cohort/workbook (picks up new strains/leads).

## Figures
- `fig_chitinase_load` — chitinolytic complement per strain (color = genus; non-Streptomyces in red).
- `fig_chitinase_normalization` — raw vs ecto+napaa-normalized chitinase against fragmentation.
- `fig_chemistry_landscape` — enediyne veto stages + specialist-class prevalence.
- `fig_priority_leads_tierA` — the TIER A shortlist as a converging-evidence matrix (Mode B / SARP / DasR /
  KCB / Tier-1). Edit `fig_priority_leads_tierA_data.csv` to add/remove a lead.

The BGC-class fragmentation ranking and normalization matrix live in `build_normalization_matrix.py`
(same conventions). Interpretation/callouts go in `Sapote_Figure_Captions.md`, not on the figures.
'''

if __name__=='__main__': main()
