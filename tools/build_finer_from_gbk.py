#!/usr/bin/env python3
"""build_finer_from_gbk.py — recover 3 of the 4 finer sheets from antiSMASH region GBKs, offline.

antiSMASH writes A-domain/PKS substrate predictions, KR active-site/stereochemistry calls, and protocluster
product+category into the region GBKs *regardless of JSON mode*. This tool extracts them directly, so every
offline strain can populate Gene_NRPS_PKS_Substrates, Gene_Active_Sites, and BGC_Class_Predictions without a
bounded re-run (only Gene_RiPP_Cores genuinely needs the region JSON). Generalizes the manual GBK recovery
the runner chat did for 17 strains.

Self-contained GBK parser (no Biopython dependency). Records are written in the banked schema with
provenance='GBK-offline', merged into deep_data.json / gene_data.json for the given strains.

Usage:
  python tools/build_finer_from_gbk.py --gbk-dir <dir-of-region-gbks> --sid SIDxxxx --banked-dir cohort
  python tools/build_finer_from_gbk.py --package <package-dir> --banked-dir cohort   # auto-find SID + GBKs
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wbio import atomic_dump_json


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)


# substrate-prediction methods vs active-site calls (antiSMASH /specificity qualifier prefixes)
SUBSTRATE_METHODS=['consensus','PKS signature','Minowa','Stachelhaus','NRPSpredictor','SANDPUMA','prediction',
                   'substrate consensus','PrediCAT','pHMM']
ACTIVE_SITE_KEYS=['KR activity','KR stereochemistry','active site','catalytic','NRPS/PKS Domain']

def parse_gbk(path):
    """Yield (feature_type, location_start, qualifiers_dict_of_lists) for each feature in a GBK."""
    txt=open(path, errors='replace').read()
    # split into the FEATURES block
    m=re.search(r'\nFEATURES\s+Location/Qualifiers\n(.*?)(?:\nORIGIN|\n//)', txt, re.S)
    if not m: return
    block=m.group(1)
    # feature header lines start with 5 spaces + type; qualifier lines start with 21 spaces
    feat=None; ftype=None; loc=None; quals=None
    for line in block.split('\n'):
        fh=re.match(r'^ {5}(\S+)\s+(\S.*)$', line)
        if fh:
            if ftype: yield ftype, loc, quals
            ftype=fh.group(1); loc=fh.group(2); quals={}
            continue
        qh=re.match(r'^ {21}/(\w+)=(.*)$', line)
        if qh and quals is not None:
            k=qh.group(1); v=qh.group(2).strip().strip('"')
            quals.setdefault(k,[]).append(v)
        elif quals is not None and line.startswith(' '*22) and quals:
            # continuation of the previous qualifier value
            last=list(quals)[-1]; quals[last][-1]=(quals[last][-1]+line.strip().strip('"'))
    if ftype: yield ftype, loc, quals

def extract(sid, acc, contig, region_label, path):
    subs=[]; act=[]; cls=[]
    region_products=[]; region_category=None
    for ftype, loc, q in parse_gbk(path):
        if ftype in ('region','protocluster','cand_cluster'):
            for p in q.get('product',[]): region_products.append(p)
            if q.get('category'): region_category=q['category'][0]
        elif ftype=='aSDomain':
            locus=(q.get('locus_tag') or q.get('domain_id') or [''])[0]
            dom=(q.get('aSDomain') or [''])[0]
            for spec in q.get('specificity',[]):
                key=spec.split(':',1)[0].strip()
                val=spec.split(':',1)[1].strip() if ':' in spec else spec
                if any(k.lower() in key.lower() for k in ACTIVE_SITE_KEYS):
                    act.append({'sid':sid,'contig':contig,'locus':locus,'domain_id':dom,
                                'active_site_calls':spec.strip(),'provenance':'GBK-offline'})
                elif any(k.lower() in key.lower() for k in SUBSTRATE_METHODS):
                    subs.append({'sid':sid,'contig':contig,'locus':locus,'domain_id':dom,
                                 'field':key,'substrate':val,'provenance':'GBK-offline'})
    if region_products:
        cls.append({'sid':sid,'contig':contig,'module':region_category or '','protocluster':region_label,
                    'predicted_products':';'.join(dict.fromkeys(region_products)),'provenance':'GBK-offline'})
    return subs, act, cls

def find_gbks(d):
    g=glob.glob(os.path.join(d,'**','*region*.gbk'),recursive=True)
    return g or glob.glob(os.path.join(d,'**','*.region*.gbk'),recursive=True) or glob.glob(os.path.join(d,'**','*.gbk'),recursive=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--gbk-dir'); ap.add_argument('--package'); ap.add_argument('--sid')
    ap.add_argument('--banked-dir', default='cohort'); ap.add_argument('--dry-run', action='store_true')
    a=ap.parse_args()
    src=a.gbk_dir or a.package
    if not src: ap.error('provide --gbk-dir or --package')
    sid=a.sid
    if not sid:
        m=re.search(r'(SID\d+|AS-\d+)', src)
        sid=m.group(1) if m else None
    if not sid: ap.error('could not infer --sid; pass it explicitly')
    gbks=find_gbks(src)
    if not gbks: emit(f'  no region GBKs under {src}'); return
    SUBS=[]; ACT=[]; CLS=[]
    for gb in gbks:
        base=os.path.basename(gb)
        rm=re.search(r'region0*(\d+)', base); region=f"region{int(rm.group(1)):03d}" if rm else 'region001'
        # contig from the LOCUS line
        first=open(gb,errors='replace').readline()
        cm=re.match(r'LOCUS\s+(\S+)', first); contig=cm.group(1) if cm else base
        acc=re.match(r'([A-Z]{2,6})', contig)
        s,ac,c=extract(sid, acc.group(1) if acc else '', contig, region, gb)
        SUBS+=s; ACT+=ac; CLS+=c
    emit(f"  {sid}: {len(gbks)} region GBKs -> {len(SUBS)} substrate, {len(ACT)} active-site, {len(CLS)} class records")
    if a.dry_run:
        for r in (SUBS[:2]+ACT[:2]+CLS[:2]): emit("   ", r)
        return
    # merge into banked (replace this sid's GBK-derived finer records)
    deep=_read_json(os.path.join(a.banked_dir,'deep_data.json')); gene=_read_json(os.path.join(a.banked_dir,'gene_data.json'))
    def merge(existing, new, sid):
        kept=[r for r in existing if r.get('sid')!=sid or r.get('provenance')=='bounded-json']  # keep bounded data
        for r in kept: r.setdefault('provenance','bounded-json')
        return kept+new
    gene['substrates']=merge(gene.get('substrates',[]), SUBS, sid)
    deep['active_sites']=merge(deep.get('active_sites',[]), ACT, sid)
    deep['class_pred']=merge(deep.get('class_pred',[]), CLS, sid)
    # v9.7.371 fix: was bare open(...,'w') -- the sibling tool that writes these SAME two banked
    # cohort files (build_deep_data.py, same directory, same purpose) already implements its own
    # _atomic_dump() (tmp+os.replace) for exactly this write; this tool wrote the shared cohort
    # bank non-atomically, so a crash mid-write here could corrupt the file every other cohort tool
    # (build_lead_tiers.py, build_modeb_deepdive.py, build_gcf_tags.py, ...) reads from.
    atomic_dump_json(deep, os.path.join(a.banked_dir,'deep_data.json'))
    atomic_dump_json(gene, os.path.join(a.banked_dir,'gene_data.json'))
    emit(f"  banked (provenance=GBK-offline). Rebuild the workbook to fill the 3 finer sheets for {sid}.", f"  NOTE: Gene_RiPP_Cores still needs the region JSON / bounded run — GBKs don't carry precursor cores.", sep="\n")

if __name__=='__main__': main()
