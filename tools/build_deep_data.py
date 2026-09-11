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
"""build_deep_data.py — bank the full per-BGC deep_data for strains ingested core-only.

The core ingest banks the inventory but not the deep per-BGC sections, so BGC_Scan_Profile,
BGC_Domain_Architecture and Gene_Domain_Hits only covered the 18 original strains. This extracts
those sections from each package's source_scans (already computed by Mamey) and merges them into
deep_data.json / gene_data.json for every strain with a package, leaving originals untouched.
"""
import json, glob, os, re, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mamey.deep_data import PROFILE_DOMAINS, TIER1_DOMAINS, extract_profiles as extract, extract_finer

def _atomic_dump(obj, path):
    """Write JSON crash-safely: .tmp + os.replace (mirrors ingest_package.atomic_dump)."""
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh)
    os.replace(tmp, str(path))

SID_RE=re.compile(r'SID\d+|AS-?\d+')

def extract_bounded_finer(sid, snap, evpath):
    """Thin wrapper kept for the cohort-bank workflow: load the evidence parse from a path and delegate
    to the SSOT extractor in mamey.deep_data (the run path passes the dict directly)."""
    try:
        e = _read_json(evpath) if evpath else {}
    except Exception:
        e = {}
    return extract_finer(sid, snap, e)

def json_mode_of(snap_path):
    """offline ('off') vs bounded — the 4 finer sheets (active_sites/substrates/ripp/class_pred)
    require bounded antiSMASH JSON; an offline run does not capture that data."""
    d=os.path.dirname(snap_path)
    ev=glob.glob(f'{d}/**/*AntiSMASH_Evidence_Parse.json', recursive=True)
    if not ev: return 'unknown'
    try: return _read_json(ev[0]).get('json_mode','unknown')
    except Exception: return 'unknown'

def find_snaps():
    # MAMEY_PACKAGES (os.pathsep-separated dirs, set by mamey_intake) searched first, then defaults.
    out={}
    env=[p for p in os.environ.get('MAMEY_PACKAGES','').split(os.pathsep) if p]
    for root in env:
        for sp in glob.glob(f'{root}/**/*Project_Memory_Snapshot.json', recursive=True):
            m=SID_RE.search(os.path.basename(sp))
            sid=m.group(0) if m else os.path.basename(os.path.dirname(sp))
            out.setdefault(sid, sp)
    for d in glob.glob('/tmp/*/SID*')+glob.glob('/tmp/mamey_SID*')+glob.glob('/mnt/user-data/uploads/SID*'):
        if d.endswith('.zip'): continue
        m=SID_RE.search(os.path.basename(d))
        if not m: continue
        snap=glob.glob(f'{d}/**/*Project_Memory_Snapshot.json', recursive=True)
        if snap: out.setdefault(m.group(0), snap[0])
    return out

def merge_section(records, new, sids_replaced):
    kept=[r for r in records if r.get('sid') not in sids_replaced]
    return kept + new

def main():
    # v9.7.274 (audit CONCERN): give a clear usage/one-line error instead of a raw traceback on
    # `--help` or a missing/bad banked dir.
    if any(a in ("-h", "--help") for a in sys.argv[1:]):
        emit("usage: build_deep_data.py [BANKED_DIR]\n"
              "  Banks full per-BGC deep_data for strains ingested core-only.\n"
              "  BANKED_DIR must contain deep_data.json, gene_data.json, bgc_data.json "
              "(defaults to the current directory).")
        return 0
    banked=sys.argv[1] if len(sys.argv)>1 else os.getcwd()
    # BC2-408: this tool's own docstring says its job is to "bank the full per-BGC deep_data for
    # strains ingested core-only" -- i.e. to ADD deep_data.json/gene_data.json enrichment to a bank
    # that only has the core ingest_package.py --merge outputs. The old guard demanded deep_data.json
    # already exist before it would run at all -- a bootstrapping bug that makes the tool refuse to
    # do its one job on the exact case it exists for: a genuinely fresh bank that has never had
    # deep_data.json. Verified live against this cycle's own real AS-XXX deliverable bank (produced
    # purely via `ingest_package.py --merge`, per its documented workflow): `error: banked dir ...
    # does not contain deep_data.json`, exit 2, before this fix. bgc_data.json is the tool's actual
    # hard prerequisite (read unconditionally below for `all_sids`); deep_data.json/gene_data.json
    # are the tool's OWN OUTPUTS being merged into, so a first run starts them from the same empty
    # shape tools/build_modeb_deepdive.py already uses for the identical missing-file case
    # (`deep=_read_json(_dp) if _op.exists(_dp) else {'bgc_profile':[]}`).
    bd=os.path.join(banked,'bgc_data.json')
    if not os.path.isdir(banked) or not os.path.exists(bd):
        emit(f"error: banked dir {banked!r} does not contain bgc_data.json "
              f"(the core ingest_package.py --merge output this tool enriches). "
              f"Run: ingest_package.py --merge first, then build_deep_data.py <banked_dir>", file=sys.stderr)
        return 2
    dd=os.path.join(banked,'deep_data.json')
    gd=os.path.join(banked,'gene_data.json')
    deep=_read_json(dd) if os.path.exists(dd) else {'bgc_profile':[],'domain_hits':[],'active_sites':[],'class_pred':[]}
    gene=_read_json(gd) if os.path.exists(gd) else {'domain_arch':[],'substrates':[],'ripp':[]}
    all_sids=set(_read_json(bd)['strains'].keys())
    snaps=find_snaps()
    P=[]; A=[]; H=[]; ACT=[]; CLS=[]; SUBS=[]; RIPP=[]; done=set()
    bounded=set(); offline=set()
    for sid,sp in snaps.items():
        if sid not in all_sids: continue
        try: s=_read_json(sp)
        except Exception: continue
        if 'source_scans' not in s: continue
        p,a,h=extract(sid,s); P+=p; A+=a; H+=h; done.add(sid)
        jm=json_mode_of(sp)
        (offline if jm=='off' else bounded if jm!='unknown' else offline).add(sid)
        if jm!='off':  # only bounded runs carry the finer-sheet data
            evp=glob.glob(f'{os.path.dirname(sp)}/**/*AntiSMASH_Evidence_Parse.json',recursive=True)
            act,cls,subs,ripp=extract_bounded_finer(sid, s, evp[0] if evp else None)
            ACT+=act; CLS+=cls; SUBS+=subs; RIPP+=ripp
    deep['bgc_profile']=merge_section(deep.get('bgc_profile',[]), P, done)
    deep['domain_hits']=merge_section(deep.get('domain_hits',[]), H, done)
    gene['domain_arch']=merge_section(gene.get('domain_arch',[]), A, done)
    # finer sections: only replace for the bounded strains we re-extracted (leave originals intact)
    bdone={sid for sid in bounded}
    if bdone:
        deep['active_sites']=merge_section(deep.get('active_sites',[]), ACT, bdone)
        deep['class_pred']=merge_section(deep.get('class_pred',[]), CLS, bdone)
        gene['substrates']=merge_section(gene.get('substrates',[]), SUBS, bdone)
        gene['ripp']=merge_section(gene.get('ripp',[]), RIPP, bdone)
    _atomic_dump(deep, os.path.join(banked,'deep_data.json'))
    _atomic_dump(gene, os.path.join(banked,'gene_data.json'))
    prof_sids={r['sid'] for r in deep['bgc_profile']}
    emit(f"deep_data banked for {len(done)} strains from packages", f"  bgc_profile now covers {len(prof_sids & all_sids)}/{len(all_sids)} strains ({len(deep['bgc_profile'])} records)", f"  domain_hits {len(deep['domain_hits'])} records | domain_arch {len(gene['domain_arch'])} records", f"  json-evidence: {len(bounded)} bounded, {len(offline)} offline", sep="\n")
    if offline:
        emit(f"  OFFLINE ({len(offline)} strains): substrates/active_sites/class_pred are GBK-recoverable "
              f"offline (antiSMASH writes them to region GBKs regardless of json mode) — run the GBK recovery; "
              f"only RiPP precursor cores genuinely need a BOUNDED run.")
    emit(f"  still missing: {sorted(all_sids - prof_sids)}")

if __name__=='__main__': sys.exit(main() or 0)
