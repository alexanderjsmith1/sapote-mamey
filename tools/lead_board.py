#!/usr/bin/env python3
"""lead_board.py — the per-strain ranked Lead Board (single source of truth).

For fragmented assemblies the honest per-strain output is a SHORT ranked board of interpretable
leads, not a deep dive of every region. A lead is a BGC carrying a class-definitive signal — a
specialized/cryptic product class, a cryptic CCTT/TIGRFAM marker (which overrides edge status,
per Mamey spec), or a complete (interior) cluster of a real biosynthetic class.

GUARD (from SID-XXX Mode B feedback): bare carbohydrate-storage clusters (saccharide/fatty_acid/
other only, no class-definitive signal) are primary-metabolism suspects — they inflate the interior
lead count and must NOT be counted as leads. They are listed separately with a verify flag.

Used by build (Lead_Board sheet) and by the Mamey output mode (per-strain board). Reads banked JSON.
Usage: python tools/lead_board.py --workbook <wb.xlsx> [--banked-dir cohort] [--queue out.csv]
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, json, os, csv
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

from _wbio import atomic_save, atomic_open


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)

# specialized / cryptic class-definitive product classes (a marker overrides edge status)
HIGH = {'phosphonate','nucleoside','lanthipeptide','lanthipeptide-class-i','lanthipeptide-class-ii',
        'lanthipeptide-class-iii','lanthipeptide-class-iv','lanthipeptide-class-v','lassopeptide',
        'thioamide-NRP','thioamitides','thiopeptide','enediyne','tetronate','spirotetronate',
        'indolocarbazole','CDPS','cyclodipeptide','aminocyclitol','betalactone','RRE-containing',
        'azole-containing-RiPP','LAP','sactipeptide','lipolanthine','glycocin','NI-siderophore',
        'NRP-metallophore','aminopolycarboxylic-acid','hglE-KS','ladderane','azoxy'}
# real biosynthetic classes that make a *complete* (interior) cluster a lead
COMPLETE_OK = {'NRPS','NRPS-like','T1PKS','T2PKS','T3PKS','PKS','PKS-like','transAT-PKS','hglE-KS',
               'RiPP','RiPP-like','RRE-containing','terpene'} | HIGH
# carbohydrate-storage / housekeeping classes — primary-metabolism suspects when alone
PRIMMET = {'saccharide','fatty_acid','other','NAPAA','melanin','butyrolactone','ectoine','betalactone'}
# cryptic CCTT cassette markers (from deep_data.bgc_profile.cctt_triggers, original strains)
def cctt_markers(s):
    if not s: return []
    out=[]
    for tok in str(s).split(','):
        tok=tok.strip()
        if tok.startswith('T43-'):
            name=tok.split('_',1)[-1] if '_' in tok else tok
            out.append(name)
    return out


def rescue_lookup(rggmci):
    """(sid,bgc) -> rescue summary from GEOMETRY-BEARING RG-GMCI pairs only. The engine labels ~40k
    pairs HIGH_RG_GMCI_RESCUE, but the pooled-rescue experiment showed most are relatedness noise;
    good_geometry_references>0 is the high-precision signal that a fragment is genuinely a split
    cluster. We surface that, not the optimistic label, so rescue (not class) drives the next step."""
    from collections import defaultdict as _dd
    out=_dd(lambda: {'geom':0,'partner':None,'best':-1})
    for sid,d in (rggmci or {}).items():
        if not isinstance(d,dict): continue
        for p in d.get('ranked_pairs',[]):
            if (p.get('good_geometry_references',0) or 0)<=0: continue
            score=p.get('rggmci_score',0) or 0
            for me,other in ((p.get('bgc_a'),p.get('bgc_b')),(p.get('bgc_b'),p.get('bgc_a'))):
                if not me: continue
                e=out[(sid,me)]; e['geom']+=1
                if score>e['best']: e['best']=score; e['partner']=other
    return out

def build_board(bgc_data, deep_data, tigr, bgc_markers=None, rescue=None):
    bgcs=bgc_data['bgcs']
    bgc_markers=bgc_markers or {}
    rescue=rescue or {}
    # per-BGC markers (CCTT + TIGRFAM panel) banked uniformly for ALL strains; falls back to
    # bgc_profile for the original strains. KCB compound anchor = flagged hypothesis, not confirmed.
    KCB_ANCHOR={'lidamycin':'enediyne','c-1027':'enediyne','calicheamicin':'enediyne','dynemicin':'enediyne',
                'neocarzinostatin':'enediyne','maduropeptin':'enediyne','esperamicin':'enediyne',
                'rifamycin':'ansamycin','naphthomycin':'ansamycin','thiostrepton':'thiopeptide','nosiheptide':'thiopeptide'}
    cctt_fallback={(r['sid'],r['bgc_id']): r.get('cctt_triggers') for r in deep_data.get('bgc_profile',[])}
    boards={}
    for b in bgcs:
        sid=b['sid']; prods=[p for p in (b.get('products') or '').split(';') if p]
        pset=set(prods)
        hi=sorted(pset & HIGH)                       # specialized product classes
        # per-BGC banked markers (CCTT + TIGRFAM), uniform across all strains
        mk=(bgc_markers.get(sid,{}) or {}).get(b['bgc_id'],{}) if bgc_markers else {}
        cm=list(mk.get('cctt',[])) + list(mk.get('tigrfam',[]))
        if not cm:                                   # fallback to bgc_profile for originals
            cm=cctt_markers(cctt_fallback.get((sid,b['bgc_id'])))
        # KCB compound anchor (flagged hypothesis ? — cheap recall insurance, e.g. lidamycin->enediyne)
        kcb=(b.get('closest_kcb_product') or '').strip().lower()
        kcb_hint=KCB_ANCHOR.get(kcb)
        interior = b.get('edge_status')=='Interior'
        primmet = bool(pset) and pset <= PRIMMET     # only housekeeping classes
        # VETO (related-family over-call guard): enediyne ene_KS cross-reacts with the
        # hglE/hglD glycolipid ketosynthase (project PREV-001). If hglE-KS is present,
        # the enediyne call is not trustworthy -> drop it. Third related-family veto, with
        # the glycogen/trehalose->T1/NUC and APH-sugar-kinase guards.
        veto=''
        if any('hglE' in p or 'hglD' in p for p in pset):
            hi=[h for h in hi if h!='enediyne']
            cm=[m for m in cm if not m.upper().startswith('ENE') and m!='enediyne']
            if kcb_hint=='enediyne': kcb_hint=None
            veto='ENE_veto_hglE'
        cm=sorted(set(cm))
        signals = hi + [f"~{m}" for m in cm if m.split('_')[0] not in {x.split('-')[0] for x in hi}]
        if kcb_hint and kcb_hint not in hi and kcb_hint not in cm:
            signals.append(f"?{kcb_hint}(KCB:{kcb})")
        tier=None
        if hi or cm:                                  # Tier-1: class-definitive marker (edge-agnostic)
            tier=1
        elif kcb_hint:                                # Tier-1?: KCB compound anchor only (hypothesis)
            tier=1
        elif interior and (pset & COMPLETE_OK) and not primmet:  # Tier-2: complete real cluster
            tier=2; signals=['interior:'+';'.join(sorted(pset & COMPLETE_OK))[:30]]
        # GUARD: bare carbohydrate-storage cluster is not a lead
        if primmet and not (hi or cm or kcb_hint):
            tier=None; flag='PRIMMET?'
        else:
            flag=veto
        if tier:
            # RG-GMCI rescue context: only for fragment leads (edge/full-contig), geometry-bearing pairs.
            # For a fragment with a genuine geometry rescue, reassembly should precede any class claim.
            rinfo=''; rflag=''
            if interior is False and b.get('edge_status')!='Interior':
                rc=rescue.get((sid,b['bgc_id']))
                if rc and rc['geom']>0:
                    rinfo=f"geom:{rc['geom']}" + (f"->{rc['partner']}" if rc['partner'] else '')
                    rflag='RESCUE_FIRST'
            boards.setdefault(sid,[]).append({
                'bgc':b['bgc_id'],'products':';'.join(prods)[:40],'length_kb':b.get('length_kb'),
                'edge':b.get('edge_status'),'tier':tier,'signals':', '.join(signals)[:48],
                'kcb_anchor':(b.get('closest_kcb_product') or '')[:30],
                'rescue':rinfo,
                'locator':f"{b.get('contig')}:{b.get('region')}",
                'flag':' '.join(x for x in (flag,rflag) if x)})
    # rank. For VERY_POOR strains, RESCUE_FIRST fragment leads bubble to the top — reassembly should
    # precede compound-class claims on a fragmented genome. Better-assembled strains keep the
    # marker-driven order (tier, #signals, length).
    strains=bgc_data.get('strains',{})
    def very_poor(sid):
        s=strains.get(sid,{}); raw=s.get('raw_bgcs',0); intr=(s.get('edge_dist') or {}).get('Interior',0)
        return bool(raw) and intr/raw < 0.05
    for sid in boards:
        if very_poor(sid):
            boards[sid].sort(key=lambda x:(0 if 'RESCUE_FIRST' in x['flag'] else 1, x['tier'], -x['signals'].count(',')-1, -(x['length_kb'] or 0)))
        else:
            boards[sid].sort(key=lambda x:(x['tier'], -x['signals'].count(',')-1, -(x['length_kb'] or 0)))
    return boards


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--workbook'); ap.add_argument('--banked-dir', default='cohort')
    ap.add_argument('--queue', help='also write a flat Mode-B queue CSV')
    a=ap.parse_args()
    # v9.7.173: tolerate optional banked stores that ingest_package does not create — notably
    # deep_data.json, read only for the CCTT fallback (deep_data.get('bgc_profile', [])). A
    # missing store returns {} instead of crashing the whole lead board with FileNotFoundError.
    def bd(f):
        p = os.path.join(a.banked_dir, f)
        if not os.path.exists(p):
            return {}
        with open(p) as fh:
            return json.load(fh)
    try: markers=bd('bgc_markers.json')
    except Exception: markers={}
    try: resc=rescue_lookup(bd('rggmci_full.json'))
    except Exception: resc={}
    boards=build_board(bd('bgc_data.json'), bd('deep_data.json'), bd('tigrfam.json'), markers, resc)
    sizes={s:len(v) for s,v in boards.items()}
    nrescue=sum(1 for v in boards.values() for L in v if 'RESCUE_FIRST' in L['flag'])
    if sizes:
        emit(f"Lead boards built for {len(boards)} strains; board sizes {min(sizes.values())}–{max(sizes.values())}, median {sorted(sizes.values())[len(sizes)//2]}; RESCUE_FIRST fragment leads: {nrescue}")
    else:
        # v9.7.141: fail-closed deliverable/workbook dry-runs exposed a valid edge case:
        # a tiny or housekeeping-only cohort can have zero BGCs that qualify for the
        # Lead_Board. That is an empty result, not a crash. Still write the sheet/header
        # below so downstream workbook/schema gates see that the phase ran.
        emit("Lead boards built for 0 strains; no qualifying leads (empty Lead_Board will be written)")
    if a.workbook:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
        wb=openpyxl.load_workbook(a.workbook)
        if 'Lead_Board' in wb.sheetnames: del wb['Lead_Board']
        ws=wb.create_sheet('Lead_Board')
        hdr=['strain','rank','BGC','Tier','products','length_kb','edge','signals','KCB_anchor','rescue','locator','flag']
        ws.append(hdr)
        for c in range(1,len(hdr)+1):
            cell=ws.cell(1,c); cell.font=Font(bold=True,color='FFFFFF'); cell.fill=PatternFill('solid',fgColor='2E5E7E')
        for sid in sorted(boards):
            for i,L in enumerate(boards[sid],1):
                ws.append([sid,i,L['bgc'],L['tier'],L['products'],L['length_kb'],L['edge'],L['signals'],L['kcb_anchor'],L.get('rescue',''),L['locator'],L['flag']])
        for col,w in zip('ABCDEFGHIJKL',[10,5,9,5,34,9,12,42,30,16,28,16]): ws.column_dimensions[col].width=w
        # Fold Mode B verdicts (cohort/modeb_verdicts.csv) onto the board if present, so confirm/
        # downgrade/drop status survives every rebuild instead of needing manual re-application.
        vpath=os.path.join(a.banked_dir,'modeb_verdicts.csv')
        if os.path.exists(vpath):
            V={(r['strain'],r['bgc']):(r['status'],r['modeb_class'],r['note']) for r in csv.DictReader(open(vpath))}
            base=len(hdr); COLOR={'CONFIRM':'E6F4EA','DROP':'FDE7E7','DOWNGRADE':'FFF4E5'}
            for i,name in enumerate(['ModeB_Status','ModeB_Class','ModeB_Note']):
                cell=ws.cell(1,base+1+i,name); cell.font=Font(bold=True,color='FFFFFF'); cell.fill=PatternFill('solid',fgColor='2E5E7E')
            nv=0
            for r in range(2,ws.max_row+1):
                k=(ws.cell(r,1).value, ws.cell(r,3).value)
                if k in V:
                    nv+=1; st,cls,note=V[k]
                    for i,val in enumerate((st,cls,note)):
                        cc=ws.cell(r,base+1+i,val)
                        if COLOR.get(st): cc.fill=PatternFill('solid',fgColor=COLOR[st])
            for i,w in enumerate([16,32,46]): ws.column_dimensions[openpyxl.utils.get_column_letter(base+1+i)].width=w
            emit(f"  Mode B verdicts folded: {nv} rows")
        # Fold per-BGC regulator coupling (cohort/tfbs_coupling.json) — candidate evidence that a lead is an
        # actively-regulated pathway. SARP coupling (pathway-specific activator) is the strongest signal;
        # DasR (chitin/GlcNAc-responsive) ties to the chitinolytic ecology. Preliminary, confirm before MS.
        cpath=os.path.join(a.banked_dir,'tfbs_coupling.json')
        if os.path.exists(cpath):
            COUP=_read_json(cpath); base=ws.max_column
            for i,name in enumerate(['Regulators','SARP_support']):
                cell=ws.cell(1,base+1+i,name); cell.font=Font(bold=True,color='FFFFFF'); cell.fill=PatternFill('solid',fgColor='2E5E7E')
            nc=0; ns=0
            for r in range(2,ws.max_row+1):
                sid=ws.cell(r,1).value; bid=ws.cell(r,3).value
                regs=(COUP.get(sid,{}) or {}).get(bid)
                if regs:
                    nc+=1; ws.cell(r,base+1,'; '.join(regs))
                    if any('SARP' in x for x in regs):
                        ns+=1; cell=ws.cell(r,base+2,'SARP'); 
                        for c in range(1,base+3): ws.cell(r,c).fill=PatternFill('solid',fgColor='E8F0FE')
            ws.column_dimensions[openpyxl.utils.get_column_letter(base+1)].width=30
            ws.column_dimensions[openpyxl.utils.get_column_letter(base+2)].width=13
            emit(f"  Regulator coupling folded: {nc} leads ({ns} SARP-supported)")
        ws.freeze_panes='A2'
        atomic_save(wb, a.workbook); emit(f"  Lead_Board sheet written: {sum(len(v) for v in boards.values())} total leads")
    if a.queue:
        with atomic_open(a.queue, newline='') as f:
            w=_SafeWriter(f); w.writerow(['strain','rank','BGC','Tier','products','length_kb','edge','signals','rescue','locator','flag'])
            for sid in sorted(boards):
                for i,L in enumerate(boards[sid],1):
                    w.writerow([sid,i,L['bgc'],L['tier'],L['products'],L['length_kb'],L['edge'],L['signals'],L.get('rescue',''),L['locator'],L['flag']])
        emit(f"  Mode-B queue CSV: {a.queue}")


if __name__=='__main__':
    main()
