import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import os


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        _d = _json.load(_fh)
    # v9.7.400: a Project_Memory_Snapshot may be an alias STUB pointing at manifest.json
    # (the pre-.400 snapshot duplicated the whole manifest; see mamey/snapshot_alias.py).
    if (isinstance(_d, dict) and _d.get("alias_of") and "source_scans" not in _d
            and "Project_Memory_Snapshot" in os.path.basename(str(_path))):
        _mp = os.path.join(os.path.dirname(str(_path)) or ".", str(_d["alias_of"]))
        if os.path.isfile(_mp):
            with open(_mp, encoding=encoding) as _fh:
                return _json.load(_fh)
    return _d

#!/usr/bin/env python3
"""build_bgc_markers.py — bank per-BGC class-definitive markers for ALL strains.

The core ingest banks the inventory but not per-BGC CCTT/TIGRFAM coupling, so the Lead_Board
could only see markers for the 18 original strains (via deep_data.bgc_profile). That made
antiSMASH-mislabeled cryptic leads invisible — e.g. SID-XXX's genuine enediyne, banked as a plain
'T1PKS', whose ene_KS only shows in the per-BGC CCTT/TIGR03828 signal.

This tool extracts per-BGC CCTT cassettes (snapshot source_scans.cctt.bgc_coupling) and the full
TIGRFAM panel incl. TIGR03828 enediyne (evidence gbk_pfam_hits, mapped by contig) from every
available package, falls back to deep_data.bgc_profile for strains without a package, and writes a
uniform bgc_markers.json the Lead_Board reads for all strains.
"""
import json, glob, os, re, sys
from collections import defaultdict

def _diagnostic_tigrfam_ids():
    """The TIGRFAM accessions this tool should count, sourced from the engine's
    DIAGNOSTIC_TIGRFAM so the fallback path can't re-collapse to a stale 4-ID panel.

    BC2-398: this was exactly that stale-4-ID panel — the sibling tools/ingest_package.py's own
    `_diagnostic_tigrfam_ids()` already carries this same warning and the full 13-ID fallback
    (fixed there for "the v9.6.15 tigr8 fix; this was its second instance"), but this file's copy
    was never updated to match, silently missing all 9 of the v9.6.15-tigr8 diagnostic-combination
    markers (enduracididine, F420-embedded polyketide, FxLD lanthipeptide, glyco T2PKS, NAPAA)
    whenever the primary `mamey` import is unavailable.
    """
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from mamey.antismash_evidence import DIAGNOSTIC_TIGRFAM
        return list(DIAGNOSTIC_TIGRFAM)
    except Exception:
        # fallback — keep in sync with mamey/antismash_evidence.DIAGNOSTIC_TIGRFAM
        return ['TIGR01454', 'TIGR03604', 'TIGR03828', 'TIGR04186',
                'TIGR04462', 'TIGR04460', 'TIGR03550', 'TIGR03551', 'TIGR03620',
                'TIGR04363', 'TIGR04364', 'TIGR01181', 'TIGR02353']
_TIGR_NAMES={'TIGR01454':'ansamycin','TIGR03604':'thiopeptide','TIGR03828':'enediyne','TIGR04186':'nucleoside',
             'TIGR04462':'enduracididine','TIGR04460':'enduracididine','TIGR03550':'F420_polyketide',
             'TIGR03551':'F420_polyketide','TIGR03620':'F420_polyketide','TIGR04363':'lanthipeptide_FxLD',
             'TIGR04364':'lanthipeptide_FxLD','TIGR01181':'glyco_T2PKS','TIGR02353':'NAPAA_marker'}
TIGR={acc:_TIGR_NAMES.get(acc, acc) for acc in _diagnostic_tigrfam_ids()}

def find_packages():
    """sid -> (snapshot_path, evidence_path). MAMEY_PACKAGES (os.pathsep dirs, set by mamey_intake)
    searched first, then the default staged/upload locations. Matches SID and AS- strains."""
    SID_RE=re.compile(r'SID\d+|AS-?\d+')
    pkgs={}
    def add(sid, snap, ev):
        if snap and sid not in pkgs: pkgs[sid]=(snap, ev)
    for root in [p for p in os.environ.get('MAMEY_PACKAGES','').split(os.pathsep) if p]:
        for sp in glob.glob(f'{root}/**/*Project_Memory_Snapshot.json', recursive=True):
            d=os.path.dirname(sp); m=SID_RE.search(os.path.basename(sp))
            sid=m.group(0) if m else os.path.basename(d)
            ev=glob.glob(f'{d}/**/*AntiSMASH_Evidence_Parse.json', recursive=True)
            add(sid, sp, ev[0] if ev else None)
    for d in glob.glob('/tmp/*/SID*')+glob.glob('/tmp/mamey_SID*')+glob.glob('/mnt/user-data/uploads/SID*'):
        if d.endswith('.zip'): continue
        sid_m=SID_RE.search(os.path.basename(d))
        if not sid_m: continue
        snap=glob.glob(f'{d}/**/*Project_Memory_Snapshot.json', recursive=True)
        ev=glob.glob(f'{d}/**/*AntiSMASH_Evidence_Parse.json', recursive=True)
        if snap: add(sid_m.group(0), snap[0], ev[0] if ev else None)
    return pkgs

def tigr_by_bgc(evpath, snap):
    if not evpath: return {}
    g=_read_json(evpath).get('gbk_pfam_hits',{})
    by_contig=defaultdict(list)
    for b in snap['bgcs']: by_contig[b['contig']].append(b['bgc_id'])
    out=defaultdict(set)
    for rk,hits in (g.items() if isinstance(g,dict) else []):
        contig=rk.rsplit('_c',1)[0]  # antiSMASH region keys are {contig}_cNNN; contig names containing '_c' would mis-split
        found=set()
        for h in (hits if isinstance(hits,list) else []):
            hs=json.dumps(h)
            for t,name in TIGR.items():
                if t in hs: found.add(name)
        if found:
            for bid in by_contig.get(contig,[]): out[bid]|=found
    return out

def main():
    banked_dir=sys.argv[1] if len(sys.argv)>1 else os.getcwd()
    bgc=_read_json(os.path.join(banked_dir,'bgc_data.json'))
    deep=_read_json(os.path.join(banked_dir,'deep_data.json'))
    all_sids=set(bgc['strains'].keys())
    pkgs=find_packages()
    markers=defaultdict(dict)   # sid -> bgc_id -> {cctt:[], tigrfam:[]}
    from_pkg=set(); from_profile=set()
    # 1) packages (recent + any uploaded original)
    for sid,(snp,evp) in pkgs.items():
        if sid not in all_sids: continue
        snap=_read_json(snp)
        cctt=snap['source_scans'].get('cctt',{}).get('bgc_coupling',{}) or {}
        tigr=tigr_by_bgc(evp, snap)
        for b in snap['bgcs']:
            bid=b['bgc_id']
            cc=[m.split('_',1)[-1] if '_' in m else m for m in cctt.get(bid,[])]
            tg=sorted(tigr.get(bid,set()))
            if cc or tg: markers[sid][bid]={'cctt':cc,'tigrfam':tg}
        from_pkg.add(sid)
    # 2) fallback: deep_data.bgc_profile for original strains without a package
    for r in deep.get('bgc_profile',[]):
        sid=r['sid']
        if sid in from_pkg: continue
        trig=r.get('cctt_triggers')
        if trig:
            cc=[t.split('_',1)[-1] if '_' in t else t for t in str(trig).split(',') if t.strip().startswith('T43-')]
            if cc:
                markers[sid].setdefault(r['bgc_id'],{'cctt':[],'tigrfam':[]})['cctt']=cc
                from_profile.add(sid)
    _out = os.path.join(banked_dir, 'bgc_markers.json')
    _tmp = _out + '.tmp'
    with open(_tmp, 'w') as fh:
        json.dump(markers, fh)
    os.replace(_tmp, _out)
    covered=set(markers.keys())
    emit(f"bgc_markers.json: {len(covered)}/{len(all_sids)} strains have per-BGC markers", f"  from packages: {len(from_pkg)} | from bgc_profile fallback: {len(from_profile)}", f"  strains with NO markers: {sorted(all_sids-covered)}", sep="\n")
    # enediyne sanity
    ene=[(s,b) for s,bb in markers.items() for b,m in bb.items() if 'enediyne' in m['cctt'] or 'enediyne' in m['tigrfam']]
    emit(f"  enediyne-marked BGCs cohort-wide: {len(ene)} (incl SID-XXX: {[b for s,b in ene if s=='SID-XXX']})")

if __name__=='__main__': main()
