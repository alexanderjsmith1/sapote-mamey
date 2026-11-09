#!/usr/bin/env python3
"""enrich_swissprot.py — fill the swissprot channel in roster_v2.json from the
already-computed local Swiss-Prot BLASTp results (no re-run needed).
Source: 'Local Blastp RESULTS (SwissProt)/<strain>/<BGC>/*_top10_local.csv', rank-1 per gene.
Homology-only; Swiss-Prot is a curated sanity channel (often sparse for actino BGC genes).
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, collections, csv, glob, json, os, re, html
import os
ROOT = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd())
SP=f"{ROOT}/Local Blastp RESULTS (SwissProt)"
RD=f"{ROOT}/sapote_deliverables/roster_v2"
import os as _os, sys as _sys  # bundle-root path guard (see tests/test_tool_front_doors.py)
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
_TOOLS_DIR = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "tools")
if _TOOLS_DIR not in _sys.path: _sys.path.insert(0, _TOOLS_DIR)
from _wbio import atomic_dump_json_owned as _atomic_write_json
try:  # cohort exclusions come from the governed SSOT, never hardcoded here
    from mamey.exclusions import raw_analysis_excluded
    EXCLUDE = raw_analysis_excluded()
except Exception as _exc:  # pragma: no cover - standalone use without mamey
    raise RuntimeError(
        "cohort exclusions are governed data and are not shipped in the code tier: "
        "install the mamey package, or set MAMEY_OFFICIAL_DATA to a directory "
        "containing exclusions.json"
    ) from _exc

def best_by_gene(strain, conflicts=None):
    """Rank-1 rows keyed by (bgc, gene). A key seen in two rank-1 rows is a hold: it is dropped from
    the map and recorded in `conflicts`, never overwritten by whichever row was read last."""
    out={}   # (bgc,gene)->row
    seen=collections.Counter()
    for f in sorted(glob.glob(f"{SP}/{strain}/*/*_top10_local.csv")):
        for r in csv.DictReader(open(f)):
            if r.get("hit_rank","1") not in ("1",""): continue
            key=(r["bgc_id"], r["gene"]); seen[key]+=1
            out.setdefault(key, r)
    dup=sorted(k for k,n in seen.items() if n>1)
    for k in dup: out.pop(k, None)
    if conflicts is not None: conflicts.extend(dup)
    return out

def enrich(strain):
    rp=f"{RD}/{strain}_roster_v2.json"
    if not os.path.exists(rp): return f"{strain}: no roster"
    conflicts=[]
    sp=best_by_gene(strain, conflicts)
    roster=json.load(open(rp)); n=0
    roster_keys=collections.Counter((b["bgc_id"], g["locus_tag"]) for b in roster["bgcs"] for g in b["genes"])
    roster_dup=sorted(k for k,c in roster_keys.items() if c>1)
    for b in roster["bgcs"]:
        for g in b["genes"]:
            if roster_keys[(b["bgc_id"], g["locus_tag"])]>1:
                continue   # two roster genes share this key: the join is ambiguous, hold it
            r=sp.get((b["bgc_id"], g["locus_tag"]))
            if r:
                try: pid=round(float(r.get("pct_identity")),1)
                except: pid=None
                g["channels"]["swissprot"]={"pid":pid,"def":html.unescape(r.get("subject_def","")),
                    "organism":r.get("subject_organism",""),"acc":r.get("subject_acc",""),
                    "coverage":r.get("query_coverage","")}
                if pid is not None: n+=1
    holds=[{"bgc_id":k[0],"locus_tag":k[1],"hold":"DUPLICATE_SWISSPROT_RANK1_KEY"} for k in conflicts]+\
          [{"bgc_id":k[0],"locus_tag":k[1],"hold":"DUPLICATE_ROSTER_GENE_KEY"} for k in roster_dup]
    if holds:
        roster.setdefault("join_holds",{})["swissprot"]=holds
    if n:
        roster["channels_present"]=sorted(set(roster.get("channels_present",[]))|{"swissprot"})
        roster.setdefault("channels_absent",{}).pop("swissprot",None)
    _atomic_write_json(roster, rp, owner_dir=RD, indent=1)
    tot=sum(len(b["genes"]) for b in roster["bgcs"])
    return f"{strain}: Swiss-Prot on {n}/{tot} genes" + (f"; {len(holds)} ambiguous key(s) held" if holds else "")

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--strain"); ap.add_argument("--all",action="store_true")
    a=ap.parse_args()
    strains=[os.path.basename(j)[:-len("_roster_v2.json")] for j in sorted(glob.glob(f"{RD}/*_roster_v2.json"))] if a.all else [a.strain]
    for s in strains:
        if s in EXCLUDE: continue
        emit(" ",enrich(s))
