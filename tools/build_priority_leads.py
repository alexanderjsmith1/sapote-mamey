#!/usr/bin/env python3
"""build_priority_leads.py — highest-confidence lead shortlist across independent evidence axes.

Combines four orthogonal confidence signals already on the Lead_Board into one ranked view:
  - chemical verdict     Mode B CONFIRM (deep-dive chemistry held up)
  - regulator support    SARP coupling (pathway-specific activator) / DasR (chitin-responsive)
  - similarity anchor     a named KCB product
  - detection tier        Tier-1 marker lead
Because these axes are independent, agreement between them is strong evidence. The headline TIER_A set is
the intersection of Mode B CONFIRM and SARP support — chemistry and regulation agreeing on the same BGC.

Outputs (figure-data convention): a Priority_Leads workbook sheet, Priority_Leads.csv (editable source),
and Priority_Leads.md (grant/figure-ready table). DROP verdicts are excluded (they failed Mode B).

Usage: python tools/build_priority_leads.py --workbook <xlsx> --out-dir <dir>
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, os
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

from _wbio import atomic_save, atomic_open, atomic_write_text

# v9.7.151 (bunny-hop 60-file): scoring weights are TUNABLE not CALIBRATED.
# Same status as `fragment_concordance_scorer.py` — picked from working
# experience triaging the AS-series cohort, not derived from a measured
# precision/recall sweep. The relative magnitudes encode editorial intent:
#   • Mode B CONFIRM is the highest-value evidence (manually-judged real
#     biosynthetic capacity) → +3, the biggest single bump.
#   • SARP regulator co-occurrence is a strong-but-noisier signal → +2.
#   • Mode B DOWNGRADE and DasR are weak-but-non-zero (kept above zero so
#     a DOWNGRADE+DasR pair doesn't tie with a pure-noise row) → +0.5 each.
#   • KCB anchor / Tier-1 are coarse class-level signals → +1 each.
#   • The min(n, cap)*weight forms (regs, signals) are diversity bonuses,
#     capped so a row spamming regulator names can't dominate.
# Re-tune any of these if you observe systematic mis-ranking on a new
# cohort; do not assume the absolute numbers carry meaning beyond the
# ranking they produce.
_W_MODEB_CONFIRM   = 3.0
_W_MODEB_DOWNGRADE = 0.5
_W_SARP            = 2.0
_W_DASR            = 0.5
_W_KCB_ANCHOR      = 1.0
_W_TIER1           = 1.0
_REG_DIVERSITY_CAP = 4
_REG_DIVERSITY_W   = 0.2
_SIGNAL_CAP        = 6
_SIGNAL_W          = 0.15


def score(row):
    s=0.0; axes=[]
    mb=(row.get('ModeB_Status') or '').strip()
    if mb=='CONFIRM': s+=_W_MODEB_CONFIRM; axes.append('ModeB:CONFIRM')
    elif mb=='DOWNGRADE': s+=_W_MODEB_DOWNGRADE; axes.append('ModeB:DOWNGRADE')
    sarp=(row.get('SARP_support') or '').strip()=='SARP'
    if sarp: s+=_W_SARP; axes.append('SARP')
    regs=(row.get('Regulators') or '')
    if 'DasR' in regs: s+=_W_DASR; axes.append('DasR')
    nother=sum(1 for r in regs.split(';') if r.strip() and 'SARP' not in r and 'DasR' not in r)
    s+=min(nother,_REG_DIVERSITY_CAP)*_REG_DIVERSITY_W
    kcb=(row.get('KCB_anchor') or '').strip()
    if kcb and kcb.lower() not in ('','none','-'): s+=_W_KCB_ANCHOR; axes.append('KCB')
    if str(row.get('Tier') or '')=='1': s+=_W_TIER1; axes.append('T1')
    nsig=len([x for x in (row.get('signals') or '').split(',') if x.strip()])
    s+=min(nsig,_SIGNAL_CAP)*_SIGNAL_W
    return round(s,2), axes

def confidence_class(row, axes):
    mb=(row.get('ModeB_Status') or '').strip(); sarp='SARP' in axes
    if mb=='CONFIRM' and sarp: return 'A'   # chemistry + regulation agree
    if mb=='CONFIRM' or (sarp and 'T1' in axes): return 'B'
    if 'T1' in axes and ('KCB' in axes) and (sarp or 'DasR' in axes): return 'C'
    return ''

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--workbook', required=True); ap.add_argument('--out-dir', default='.')
    a=ap.parse_args()
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    wb=openpyxl.load_workbook(a.workbook)
    if 'Lead_Board' not in wb.sheetnames:
        import sys
        sys.exit("Lead_Board sheet missing — run tools/lead_board.py on this workbook first "
                 "(pipeline order: lead_board.py -> build_priority_leads.py).")
    lb=wb['Lead_Board']; hdr=[lb.cell(1,c).value for c in range(1,lb.max_column+1)]
    rows=[dict(zip(hdr,[c.value for c in r])) for r in lb.iter_rows(min_row=2)]
    pri=[]; allscores=[]
    for r in rows:
        if not r.get('strain'): continue
        dropped=(r.get('ModeB_Status') or '').strip()=='DROP'
        sc,axes=score(r); cc='' if dropped else confidence_class(r,axes)
        allscores.append({'strain':r['strain'],'BGC':r['BGC'],'score':sc,'confidence':cc,
                          'dropped':'DROP' if dropped else ''})
        if dropped: continue  # failed chemistry
        if not cc: continue  # only A/B/C make the shortlist
        pri.append({'strain':r['strain'],'BGC':r['BGC'],'confidence':cc,'score':sc,
                    'products':r.get('products',''),'tier':r.get('Tier',''),
                    'ModeB':(r.get('ModeB_Status') or ''),'ModeB_class':(r.get('ModeB_Class') or ''),
                    'regulators':(r.get('Regulators') or ''),'SARP':'SARP' if 'SARP' in axes else '',
                    'KCB_anchor':(r.get('KCB_anchor') or ''),'locator':r.get('locator',''),
                    'evidence':'+'.join(axes)})
    pri.sort(key=lambda x:({'A':0,'B':1,'C':2}[x['confidence']], -x['score']))
    # workbook sheet
    if 'Priority_Leads' in wb.sheetnames: del wb['Priority_Leads']
    ws=wb.create_sheet('Priority_Leads')
    cols=['confidence','score','strain','BGC','tier','products','ModeB','ModeB_class','SARP','regulators','KCB_anchor','evidence','locator']
    ws.append(cols)
    for c in range(1,len(cols)+1):
        cell=ws.cell(1,c); cell.font=Font(bold=True,color='FFFFFF'); cell.fill=PatternFill('solid',fgColor='2E5E7E')
    FILL={'A':PatternFill('solid',fgColor='C8E6C9'),'B':PatternFill('solid',fgColor='E6F4EA'),'C':PatternFill('solid',fgColor='F4FAF5')}
    for p in pri:
        ws.append([p[c] for c in cols])
        for c in range(1,len(cols)+1): ws.cell(ws.max_row,c).fill=FILL[p['confidence']]
    for col,w in zip('ABCDEFGHIJKLM',[11,7,9,7,5,30,11,28,6,28,26,26,26]): ws.column_dimensions[col].width=w
    ws.freeze_panes='A2'
    atomic_save(wb, a.workbook)
    # standalone CSV (editable source)
    os.makedirs(a.out_dir,exist_ok=True)
    # full score distribution (every evaluated lead) — feeds the contrast figure
    allscores.sort(key=lambda x:-x['score'])
    with atomic_open(os.path.join(a.out_dir,'Priority_Scores_All.csv'), newline='') as f:
        w=_SafeDictWriter(f,fieldnames=['rank','strain','BGC','score','confidence','dropped']); w.writeheader()
        for i,d in enumerate(allscores,1): w.writerow({'rank':i,**d})
    with atomic_open(os.path.join(a.out_dir,'Priority_Leads.csv'), newline='') as f:
        w=_SafeDictWriter(f,fieldnames=cols); w.writeheader()
        for p in pri: w.writerow({c:p[c] for c in cols})
    # grant/figure-ready markdown (TIER_A headline)
    A=[p for p in pri if p['confidence']=='A']
    md=['# Priority Leads — highest-confidence shortlist','',
        f'Ranked across four independent axes (Mode B chemistry · SARP/DasR regulation · KCB anchor · detection tier). '
        f'{len(pri)} leads make tiers A/B/C; **{len(A)} are TIER A** (Mode B CONFIRM *and* SARP-supported — chemistry and regulation agree).','',
        '## TIER A — chemistry + regulation agree','',
        '| Strain | BGC | Products | Mode B class | Regulators | KCB anchor |','|---|---|---|---|---|---|']
    for p in A:
        md.append(f"| {p['strain']} | {p['BGC']} | {p['products']} | {p['ModeB_class']} | {p['regulators']} | {p['KCB_anchor']} |")
    nB=sum(1 for p in pri if p['confidence']=='B'); nC=sum(1 for p in pri if p['confidence']=='C')
    md+=['', f'_TIER B: {nB} leads (CONFIRM or SARP+T1). TIER C: {nC} leads (T1 + KCB + regulator, no Mode B yet)._ '
         '_All evidence is candidate-level; KCB = similarity not identity; regulator coupling is preliminary._']
    atomic_write_text(os.path.join(a.out_dir,'Priority_Leads.md'), '\n'.join(md))
    emit(f"  Priority_Leads: {len(pri)} leads ({len(A)} TIER_A, "
          f"{sum(1 for p in pri if p['confidence']=='B')} B, {sum(1 for p in pri if p['confidence']=='C')} C) "
          f"-> sheet + Priority_Leads.csv + Priority_Leads.md")

if __name__=='__main__': main()
