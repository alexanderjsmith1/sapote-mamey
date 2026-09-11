#!/usr/bin/env python3
"""build_thesis_vignettes.py — worked thesis vignettes for the Class-A leads.

Each vignette pairs a lead's gene-by-gene Mode B deep dive (§1–§8, reused from build_modeb_deepdive) with its
size-context percentile (nucleotide content vs the cohort distribution for its class) and a pointer to the
relevant cause-effect map, framed as chapter prose. The point of a vignette is to show the framework working
end-to-end on one cluster: detection → architecture/substrates → why it's a lead → size evidence → the decision
path that produced the verdict.

Usage: python tools/build_thesis_vignettes.py --banked-dir cohort --out thesis_vignettes.md [--workbook M.xlsx]
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, os, json, sys


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wbio import atomic_write_text
import build_modeb_deepdive as mb

DEFAULT_LEADS=[('SID-XXX','BGC024'),('SID-XXX','BGC032'),('SID-XXX','BGC037'),('SID-XXX','BGC059'),('SID-XXX','BGC014'),('SID-XXX','BGC067')]
# which cause-effect map best illustrates each lead's decision path, keyed by REAL strain ID.
# FIXED v9.7.308 (audit path 2, sibling of the master_figure_atlas AS-XXX fix). This replaced a
# 3-entry dict literal whose keys were all the placeholder 'SID-XXX': Python keeps only the last
# duplicate key, so 2 of the 3 authored routes were dead and none ever fired (real strain IDs are
# never literally 'SID-XXX'). Behavior is unchanged — every real strain already resolved to
# DEFAULT_MAP via .get(sid, DEFAULT_MAP) — but the dead/misleading dict is gone and the route map
# is now collision-proof. Duplicate/placeholder keys are blocked by
# test_causemap_overrides_have_distinct_real_keys and tools/repo_health.py. The three authored
# (image, description) routes are preserved below as reference; assigning each to the real strain
# it was meant for is an editorial call, not a code guess.
_AUTHORED_CAUSEMAP_ROUTES_PENDING_MAPPING=[
    ('causemap_testcase.png','the full pipeline path — detection → fragment-rescue → marker veto → Mode B CONFIRM → SARP coupling → Class A'),
    ('causemap_development.png','how the priority-scoring rules converged'),
    ('causemap_rejections.png','the specificity gallery — the same framework that confirms also rejects 5/35'),
]
CAUSEMAP={}
DEFAULT_MAP=('causemap_enediyne.png','the discrimination logic — class support is demanded, look-alikes vetoed')

def size_context(sid,bid,bgcs):
    # percentile of this BGC's size within its antiSMASH primary class across the cohort
    def primary(b):
        cl=[p.strip().lower() for p in (b.get('products') or '').split(';') if p.strip()]
        for pref in ['transat-pks','t1pks','hr-t2pks','t2pks','nrps','terpene','ripp','siderophore']:
            if pref in cl: return pref
        return cl[0] if cl else 'other'
    tgt=next((b for b in bgcs if b['sid']==sid and bid in b.get('bgc_id','')),None)
    if not tgt: return None
    cls=primary(tgt); sz=tgt.get('length_kb') or 0
    dist=sorted([(b.get('length_kb') or 0) for b in bgcs if primary(b)==cls])
    med=dist[len(dist)//2] if dist else 0
    pct=round(100*sum(1 for x in dist if x<=sz)/len(dist)) if dist else 0
    return {'class':cls,'size':sz,'median':med,'pct':pct,'edge':tgt.get('edge_status',''),'anchor':tgt.get('closest_kcb_product','')}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--banked-dir', default='cohort'); ap.add_argument('--out', default='thesis_vignettes.md')
    ap.add_argument('--workbook', default=None); a=ap.parse_args()
    bgc=_read_json(os.path.join(a.banked_dir,'bgc_data.json')); bgcs=bgc['bgcs']; brec={(b['sid'],b['bgc_id']):b for b in bgcs}
    deep=_read_json(os.path.join(a.banked_dir,'deep_data.json')); prof={(p['sid'],p['bgc_id']):p for p in deep['bgc_profile']}
    gene=_read_json(os.path.join(a.banked_dir,'gene_data.json')); tfbs=gene.get('tfbs',{}); sub=gene.get('substrates',[])
    cpl=_read_json(os.path.join(a.banked_dir,'tfbs_coupling.json')) if os.path.exists(os.path.join(a.banked_dir,'tfbs_coupling.json')) else {}
    vmap={}
    vpath=os.path.join(a.banked_dir,'modeb_verdicts.csv')
    if os.path.exists(vpath):
        import csv
        for r in csv.DictReader(open(vpath)): vmap[(r['strain'],r['bgc'])]={'status':r['status'],'modeb_class':r.get('modeb_class',''),'note':r.get('note','')}
    rescue={}
    if a.workbook and os.path.exists(a.workbook):
        try:
            import openpyxl
            wb=openpyxl.load_workbook(a.workbook, read_only=True)
            if 'Fragment_Rescue_Tiers' in wb.sheetnames:
                rows=list(wb['Fragment_Rescue_Tiers'].iter_rows(values_only=True)); h=list(rows[0]); ix={c:i for i,c in enumerate(h)}
                for r in rows[1:]:
                    if r[ix['strain']]: rescue[r[ix['strain']]]={'contigs':r[ix['Contigs']],'frag':r[ix['Frag_Loss']],'tier':r[ix['Tier']]}
        except Exception: pass
    if not rescue:
        sc={}
        for b in bgcs: sc.setdefault(b['sid'],set()).add(b.get('contig'))
        for sid in sc: rescue[sid]={'contigs':len(sc[sid]),'frag':'?','tier':'?'}

    # v9.7.142 C5: choose real targets from modeb_verdicts.csv when available.
    # Older cuts emitted six SID-XXX placeholder vignettes on arbitrary single-strain cohorts,
    # which made a passing deliverable build contain stale/nonsense cards.
    leads=[k for k,v in vmap.items() if v.get('status')=='CONFIRM'] or list(vmap.keys())
    if not leads:
        leads=DEFAULT_LEADS
    missing=[x for x in leads if x not in brec]
    if missing and leads==DEFAULT_LEADS:
        sys.exit('build_thesis_vignettes: default SID placeholder targets are absent from this banked cohort; provide modeb_verdicts.csv with real strain/BGC targets.')
    leads=[x for x in leads if x in brec][:6]
    if not leads:
        sys.exit('build_thesis_vignettes: no vignette target matches banked bgc_data.json; refusing placeholder output.')

    out=[f"# Worked thesis vignettes — {len(leads)} real lead(s)\n",
         "*Each vignette runs the framework end-to-end on one cluster: the gene-by-gene Mode B deep dive (§1–§8), "
         "its size-context percentile (nucleotide content vs the cohort distribution for its class — the "
         "fragmentation-robust capacity measure), and the cause-effect map that traces how the verdict was reached. "
         "All statements are class-level and KCB-anchored; bioactivity metadata is optional strain-level context.*\n","---\n"]
    for i,(sid,bid) in enumerate(leads,1):
        sc=size_context(sid,bid,bgcs); v=vmap.get((sid,bid))
        cm=CAUSEMAP.get(sid,DEFAULT_MAP)
        out.append(f"\n## Vignette {i} — {sid}/{bid}  ·  {sc['anchor'] if sc else '?'}\n")
        # opening frame
        if sc:
            edge='— and it is edge-truncated, so its true extent is larger still' if sc['edge']=='Edge' else ''
            out.append(f"This cluster is one of the six leads that clear both chemistry (Mode B CONFIRM) and regulation "
                       f"(in-cluster SARP) filters. By nucleotide content it sits at the **{sc['pct']}th percentile** of "
                       f"the cohort's {sc['class']} clusters ({sc['size']:.0f} kb vs a class median of {sc['median']:.0f} kb){edge} "
                       f"— a substantial biosynthetic locus, not a fragmentation artefact (Fig. size-context, "
                       f"`fig_classA_size_context.png`).\n")
        # the dive
        out.append(mb.deepdive(sid,bid,brec,prof,deep['active_sites'],deep['class_pred'],tfbs,rescue,sub,cpl,v))
        # decision-path + chapter point
        out.append(f"\n**Decision path.** The route from raw detection to this verdict is traced in {cm[1]} "
                   f"(`{cm[0]}`). What the vignette illustrates for the chapter: a similarity anchor alone is never the "
                   f"claim — the lead earns its rank only when the gene-by-gene logic (§2–§3), the regulatory wiring (§6), "
                   f"the self-resistance signal (§7) and the size evidence all corroborate the class, and the framework "
                   f"is equally willing to withhold that rank when they do not.\n\n---\n")
    atomic_write_text(a.out,'\n'.join(out))
    emit(f"  wrote {len(leads)} thesis vignettes → {a.out}")

if __name__=='__main__': main()
