#!/usr/bin/env python3
"""build_lead_tiers.py — re-derive lead tiers with self-protection as an orthogonal second axis.

Current dossier rule: Class-A = CONFIRM ∩ in-cluster-SARP (precision filter). That benches CONFIRMED,
bioactivity-relevant pathways whose only deficit is a pathway-specific activator. `resistance_tier` is already
computed in bgc_profile but unused in the score. This tool folds it in as a SECOND independent axis:

    proposed Class-A = CONFIRM ∩ (in-cluster-SARP  OR  T1 source-derived self-protection)

so a confirmed pathway with strong self-protection (diagnostic of a genuine, expressed cluster) is promoted on
orthogonal evidence even without SARP. Emits the recall table with current vs proposed tier so the two travel
together. SARP is read from tfbs_coupling.json (per-BGC), NOT the strain-level palindrome count.

Usage: python tools/build_lead_tiers.py --banked-dir cohort --out ChemistryFirst_Recall.csv
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


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)



def _is_nucleoside(mc, note, anchor):
    t=(mc+' '+note+' '+(anchor or '')).lower()
    return ('nucleoside' in t) or ('t43-nuc' in t)

_AXIS_TABLE=None
def _load_axis_table():
    global _AXIS_TABLE
    if _AXIS_TABLE is None:
        here=os.path.dirname(os.path.abspath(__file__))
        path=os.path.join(here,'..','resources','bioactivity_axes.json')
        try: _AXIS_TABLE=_read_json(path)
        except Exception: _AXIS_TABLE={'axes_in_priority_order':[],'default_axis':'antibacterial (general)'}
    return _AXIS_TABLE

def axis(mc, note, anchor='', chitin_context=False):
    """Deterministic chemistry -> bioactivity axis via resources/bioactivity_axes.json. Matches
    modeb_class + note + KCB anchor against strings antiSMASH actually emits. The nucleoside->antifungal
    link (nikkomycin/polyoxin chitin-synthase inhibitors) is GATED on chitin_context, because a bare
    'nucleoside' anchor has no compound name to match and not every nucleoside is antifungal."""
    t=(mc+' '+note+' '+(anchor or '')).lower()
    tbl=_load_axis_table()
    for entry in tbl.get('axes_in_priority_order',[]):
        if any(k in t for k in entry['keywords']): return entry['axis']
    if ('nucleoside' in t or 't43-nuc' in t):
        return 'antifungal (Candida)' if chitin_context else 'nucleoside-antibiotic candidate (axis uncertain)'
    return tbl.get('default_axis','antibacterial (general)')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--banked-dir', default='cohort'); ap.add_argument('--out', default='ChemistryFirst_Recall.csv')
    ap.add_argument('--bioactivity', default=None, help='filter to one axis, e.g. antifungal (substring match)')
    a=ap.parse_args()
    bgc=_read_json(os.path.join(a.banked_dir,'bgc_data.json')); brec={(b['sid'],b['bgc_id']):b for b in bgc['bgcs']}
    # H4: per-strain chitin context for nucleoside→antifungal axis gate.
    # cgad_active stored in bgc_data.json strains metadata (H4 fix in _emit_bgc_bank).
    cgad_by_sid={sid: bool(meta.get('cgad_active')) for sid,meta in (bgc.get('strains') or {}).items()}
    # BC2-408: deep_data.json is a SEPARATE tool's output (tools/build_deep_data.py, per the
    # AUDIT_374 comment in tools/build_master.py's own _read_json_or() fix for this identical gap)
    # -- ingest_package.py --merge never writes it, so a freshly-banked cohort (the common case:
    # verified live against this cycle's own AS-XXX deliverable bank) does not have it yet. This
    # was an unconditional _read_json() with no existence check -- a hard FileNotFoundError,
    # before this tool's own v9.7.114 "empty-safe write" design (below) ever gets a chance to run.
    # Mirrors build_master.py's already-established fallback for the same file.
    _dd_path = os.path.join(a.banked_dir,'deep_data.json')
    deep=_read_json(_dd_path) if os.path.exists(_dd_path) else {'bgc_profile':[]}
    prof={(p['sid'],p['bgc_id']):p for p in deep['bgc_profile']}
    cpl=_read_json(os.path.join(a.banked_dir,'tfbs_coupling.json'))
    # A2: per-BGC resistance coupling lifted on ingest (resistance_coupling.json). OR genuine
    # self-protection families into the self-protection axis so target-directed leads promote even
    # when deep_data resistance_tier is empty (the case for externally-ingested strains). Provenance:
    # engine annotation/keyword method (HMMER confirmation still recommended) — see _coupling_provenance.json.
    _rcp=os.path.join(a.banked_dir,'resistance_coupling.json')
    rescpl=_read_json(_rcp) if os.path.exists(_rcp) else {}
    _SELFPROT_FAMS={'self_resistance_general','self_resistance','target_redundancy','duplicated_target'}
    # assembly-QC gate: FLAG strains are held, never promoted (behavioural contract)
    held=set()
    qcp=os.path.join(a.banked_dir,'assembly_qc.json')
    if os.path.exists(qcp):
        # B3 (v9.7.212): fail CLOSED. Contract above is "FLAG strains are held, never promoted." The old
        # `try: ... except Exception: pass` left `held` empty on any parse failure (truncated write, schema
        # drift, bad encoding), silently PROMOTING strains that must be held — a claim-safety contract
        # violation with no visible signal. A corrupt QC hold-set must stop the run, not pass quietly.
        try:
            with open(qcp, encoding="utf-8") as _fh:
                held=set(json.load(_fh).get('held_qc',[]))
        except Exception as _e:
            raise SystemExit(f"[build_lead_tiers] assembly_qc.json exists but failed to parse ({_e}); "
                             f"refusing to run — a corrupt QC hold-set would silently promote held strains. "
                             f"Fix or remove {qcp}.")
    rows=[]
    # BC2-408: modeb_verdicts.csv is written per-PACKAGE (mamey/cli.py's _write_package, gold mode)
    # but no tool in this codebase -- not ingest_package.py, not tools/build_deep_data.py, not
    # tools/build_master.py -- ever merges those per-strain rows into a cohort-level
    # <banked_dir>/modeb_verdicts.csv. Every sibling consumer of this same file
    # (tools/generate_bgc_atlas.py, tools/build_thesis_vignettes.py, tools/build_subset_panel.py,
    # tools/lead_board.py) already guards this exact read with `if os.path.exists(...)`; this was
    # the one tool with a bare, unguarded open() -- a hard FileNotFoundError on every freshly-banked
    # cohort (verified live against this cycle's own AS-XXX deliverable bank), reached BEFORE this
    # tool's own v9.7.114 "empty-safe write" design (a cohort with zero CONFIRMs writes a valid
    # header-only CSV) ever gets a chance to run. The cohort-level merge gap itself is a separate,
    # larger, out-of-scope-for-this-card structural question (which tool should own writing
    # <banked_dir>/modeb_verdicts.csv, and when) -- flagged, not decided, here.
    _mv_path = os.path.join(a.banked_dir,"modeb_verdicts.csv")
    _mv_rows = list(csv.DictReader(open(_mv_path, encoding="utf-8"))) if os.path.exists(_mv_path) else []
    for r in _mv_rows:
        if r['status']!='CONFIRM': continue
        sid,bid=r['strain'],r['bgc']; b=brec.get((sid,bid),{}); p=prof.get((sid,bid),{})
        _cgad = cgad_by_sid.get(sid, False)  # H4: genome-level chitin context
        if sid in held:
            rows.append({'sid':sid,'bgc':bid,'modeb_class':r['modeb_class'],'bioactivity_axis':axis(r['modeb_class'],r['note'],b.get('closest_kcb_product',''),chitin_context=_cgad),
                'in_cluster_SARP':'-','self_protection_T1':'-','current_tier':'HOLD-QC','proposed_tier':'HOLD-QC',
                'PROMOTED_by_selfprotection':'','resistance_tier':'held: assembly QC','edge':b.get('edge_status'),'kb':b.get('length_kb'),'priority_floor':('high' if _is_nucleoside(r['modeb_class'],r['note'],b.get('closest_kcb_product','')) else '')})
            continue
        sarp = 'SARP' in (cpl.get(sid,{}).get(bid,[]) if isinstance(cpl.get(sid),dict) else [])
        rt=(p.get('resistance_tier') or '')
        _resfams=[str(x).lower() for x in (rescpl.get(sid,{}).get(bid,[]) if isinstance(rescpl.get(sid),dict) else [])]
        selfprot = rt.startswith('T1_DIAGNOSTIC_SELF_PROTECTION') or any(f in _SELFPROT_FAMS for f in _resfams)
        current = 'A' if sarp else 'B'                                  # CONFIRM ∩ SARP
        proposed = 'A' if (sarp or selfprot) else 'B'                   # CONFIRM ∩ (SARP ∨ self-protection)
        promoted = (current=='B' and proposed=='A')
        nucl=_is_nucleoside(r['modeb_class'],r['note'],b.get('closest_kcb_product',''))
        rows.append({'sid':sid,'bgc':bid,'modeb_class':r['modeb_class'],'bioactivity_axis':axis(r['modeb_class'],r['note'],b.get('closest_kcb_product',''),chitin_context=_cgad),
            'in_cluster_SARP':'Y' if sarp else 'n','self_protection_T1':'Y' if selfprot else 'n',
            'current_tier':current,'proposed_tier':proposed,'PROMOTED_by_selfprotection':'YES' if promoted else '',
            'resistance_tier':rt[:34],'edge':b.get('edge_status'),'kb':b.get('length_kb'),
            'priority_floor':'high' if nucl else ''})
    if a.bioactivity:
        # never-drop: chemistry-relevant leads are partitioned, not removed (kept for transparency)
        rows=[x for x in rows if a.bioactivity.lower() in x['bioactivity_axis'].lower()]
    order={'antifungal (Candida)':0,'anticancer':1,'anti-MRSA / anti-Gram-positive':2,'anti-MRSA':2,'antiparasitic':3}
    # nucleoside priority floor sorts to the top regardless of tier; then tier, then axis
    rows.sort(key=lambda x:(x.get('priority_floor')!='high', x['proposed_tier']!='A' or x['PROMOTED_by_selfprotection']!='YES', order.get(x['bioactivity_axis'],9)))
    # Empty-safe write (v9.7.114): a cohort with zero CONFIRMs must write a valid header-only CSV,
    # not crash on rows[0].keys(). Fieldnames are fixed by the row schema above.
    _FIELDS = ['sid','bgc','modeb_class','bioactivity_axis','in_cluster_SARP','self_protection_T1',
               'current_tier','proposed_tier','PROMOTED_by_selfprotection','resistance_tier',
               'edge','kb','priority_floor']
    fieldnames = list(rows[0].keys()) if rows else _FIELDS
    _tmp = a.out + '.tmp'
    with open(_tmp,'w',newline='') as f:
        w=_SafeDictWriter(f, fieldnames=fieldnames); w.writeheader(); w.writerows(rows)
    os.replace(_tmp, a.out)
    nA=sum(1 for x in rows if x['current_tier']=='A'); nP=sum(1 for x in rows if x['proposed_tier']=='A')
    promo=[x for x in rows if x['PROMOTED_by_selfprotection']=='YES']
    emit(f"  wrote {a.out} — {len(rows)} CONFIRMs; current Class-A={nA}, proposed Class-A={nP} (+{len(promo)} via self-protection)")
    for x in promo: emit(f"    PROMOTED: {x['sid']}/{x['bgc']} — {x['bioactivity_axis']} ({x['modeb_class']})")

if __name__=='__main__': main()
