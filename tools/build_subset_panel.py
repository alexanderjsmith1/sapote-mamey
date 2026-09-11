#!/usr/bin/env python3
"""build_subset_panel.py — deterministic cross-cohort / cohort-subset panel (closes DLV-008; drives G2 & G6).

Filters the banked BGCs to a product tag and/or a strain set, joins verdict + SARP + edge + tier, writes a locus
CSV, and renders a grouped panel (one lane per genus, one chip per locus). The filter+join is fully reproducible;
this is the plotting wrapper that build_figures.py lacked.

Claim-safety: a tag panel groups loci that share the {TAG} machinery / antiSMASH E-signal — NOT one shared
compound (KCB anchors may differ); the caption states this. KCB anchors render with ~ (similarity, not ID).
Tiers use the standard palette. PRIVATE filename if any AS strain is in the subset.

Usage:
  python tools/build_subset_panel.py --banked-dir cohort --tag phenazine --out-dir figures
  python tools/build_subset_panel.py --banked-dir cohort --strain-set SID-XXX,SID-XXX --out-dir figures
  python tools/build_subset_panel.py --replot --csv figures/subset_phenazine_loci.csv --out-dir figures
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, os, json, csv, re
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
from matplotlib.patches import Patch

TIER={'Confirmed':'#2E7D32','Predicted-functional':'#2E86AB','KCB-anchored':'#E59866','Candidate-novel':'#7F8C8D'}

def genus(org): return (org or 'Unknown').split()[0] if org else 'Unknown'

def tier_of(b, verdict):
    anchor=(b.get('closest_kcb_product') or '').strip()
    dark=(not anchor) or anchor.upper()=='UNRESOLVED' or (b.get('closest_mibig') or '').strip().upper() in ('','UNRESOLVED')
    if verdict=='CONFIRM': return 'Confirmed'
    if dark: return 'Candidate-novel'
    return 'KCB-anchored'

def build_rows(banked, tag, strain_set):
    bgc=_read_json(os.path.join(banked,'bgc_data.json'))
    from mamey.figure_policy import omit_saccharides
    bgc['bgcs']=omit_saccharides(bgc['bgcs'])  # figure policy: pure-saccharide regions never plotted
    org={s['sid']:s.get('organism','') for s in _read_json(os.path.join(banked,'strains.json'))}
    vmap={}
    vp=os.path.join(banked,'modeb_verdicts.csv')
    if os.path.exists(vp):
        for r in csv.DictReader(open(vp)): vmap[(r['strain'],r['bgc'])]=r['status']
    cpl=_read_json(os.path.join(banked,'tfbs_coupling.json')) if os.path.exists(os.path.join(banked,'tfbs_coupling.json')) else {}
    rows=[]
    for b in bgc['bgcs']:
        prods=(b.get('products') or '').lower()
        if tag and tag.lower() not in prods: continue
        if strain_set and b['sid'] not in strain_set: continue
        v=vmap.get((b['sid'],b['bgc_id']),'[EG]')
        sarp = 'y' if 'SARP' in (cpl.get(b['sid'],{}).get(b['bgc_id'],[]) if isinstance(cpl.get(b['sid']),dict) else []) else 'n'
        rows.append({'sid':b['sid'],'region':b.get('region',b.get('bgc_id','')),'genus':genus(org.get(b['sid'],'')),
                     'class':(b.get('products') or '').split(';')[0],'kcb':b.get('closest_kcb_product') or 'UNRESOLVED',
                     'kb':b.get('length_kb') or 0,'edge':b.get('edge_status') or '?','sarp':sarp,
                     'verdict':v if v in ('CONFIRM','DROP','DOWNGRADE') else '[EG]','tier':tier_of(b, v)})
    return rows

def plot(rows, title, claim, out):
    genera=sorted(set(r['genus'] for r in rows))
    ylane={g:i for i,g in enumerate(genera)}
    fig_h=max(3, 0.5*len(genera)+2)
    fig,ax=plt.subplots(figsize=(11,fig_h))
    for r in rows:
        y=ylane[r['genus']]+ ( (hash(r['sid']+r['region'])%9)-4)*0.045  # jitter within lane
        ax.scatter(r['kb'], y, s=70, color=TIER[r['tier']], edgecolor='white', linewidth=0.6, zorder=3)
    ax.set_yticks(range(len(genera))); ax.set_yticklabels(genera, fontsize=9)
    ax.set_xlabel('cluster size (kb)'); ax.set_ylim(-0.6, len(genera)-0.4)
    ax.set_title(title, fontsize=12, pad=10)
    ax.grid(axis='x', alpha=0.25)
    leg=[Patch(facecolor=c, label=t) for t,c in TIER.items()]
    ax.legend(handles=leg, fontsize=8, loc='upper right', framealpha=0.9, title='confidence tier')
    fig.text(0.5, -0.02/fig_h, claim, ha='center', fontsize=8, color='#555', wrap=True)
    plt.tight_layout(); plt.savefig(out, dpi=150, bbox_inches='tight'); plt.close()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--banked-dir', default='cohort'); ap.add_argument('--out-dir', default='figures')
    ap.add_argument('--tag', default=None); ap.add_argument('--strain-set', default=None)
    ap.add_argument('--replot', action='store_true'); ap.add_argument('--csv', default=None)
    a=ap.parse_args(); os.makedirs(a.out_dir, exist_ok=True)
    sset=set(a.strain_set.split(',')) if a.strain_set else None
    if a.replot and a.csv:
        label=re.sub(r'^subset_|_loci$','', os.path.splitext(os.path.basename(a.csv))[0])
    else:
        label = a.tag or (a.strain_set.replace(',','_') if a.strain_set else 'subset')
    safe=re.sub(r'[^A-Za-z0-9_]+','_',label)
    csvp=a.csv or os.path.join(a.out_dir, f'subset_{safe}_loci.csv')
    if a.replot and os.path.exists(csvp):
        rows=list(csv.DictReader(open(csvp)))
        for r in rows: r['kb']=float(r['kb'] or 0)
    else:
        rows=build_rows(a.banked_dir, a.tag, sset)
        if not rows: emit(f"  no loci match (tag={a.tag}, strains={a.strain_set})"); return
        with open(csvp,'w',newline='') as f:
            w=_SafeDictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    is_as=any(r['sid'].upper().startswith('AS') for r in rows)
    title=f"{'Product tag '+a.tag if a.tag else 'Strain-set'} panel · {len(rows)} loci across {len(set(r['genus'] for r in rows))} genera"
    claim=(f"Shared thread is the {a.tag} machinery / antiSMASH E-signal, NOT one shared compound — KCB anchors may differ. "
if a.tag else "KCB anchors are similarity, not identification. ") + "Bioactivity metadata is optional strain-level context; verdicts [EG] offline."
    out=os.path.join(a.out_dir, f"fig_subset_{safe}{'_PRIVATE' if is_as else ''}.png")
    plot(rows, title, claim, out)
    emit(f"  wrote {out} (+ {csvp}) — {len(rows)} loci{' [PRIVATE: AS present]' if is_as else ''}")

if __name__=='__main__': main()
