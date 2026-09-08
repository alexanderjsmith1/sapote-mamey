#!/usr/bin/env python3
"""enrich_swissprot.py — fill the swissprot channel in roster_v2.json from the
already-computed local Swiss-Prot BLASTp results (no re-run needed).
Source: 'Local Blastp RESULTS (SwissProt)/<strain>/<BGC>/*_top10_local.csv', rank-1 per gene.
Homology-only; Swiss-Prot is a curated sanity channel (often sparse for actino BGC genes).
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, glob, json, os, re, html
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

def best_by_gene(strain):
    out={}   # (bgc,gene)->row
    for f in glob.glob(f"{SP}/{strain}/*/*_top10_local.csv"):
        for r in csv.DictReader(open(f)):
            if r.get("hit_rank","1") not in ("1",""): continue
            out[(r["bgc_id"], r["gene"])]=r
    return out

def enrich(strain):
    rp=f"{RD}/{strain}_roster_v2.json"
    if not os.path.exists(rp): return f"{strain}: no roster"
    sp=best_by_gene(strain)
    roster=json.load(open(rp)); n=0
    for b in roster["bgcs"]:
        for g in b["genes"]:
            r=sp.get((b["bgc_id"], g["locus_tag"]))
            if r:
                try: pid=round(float(r.get("pct_identity")),1)
                except: pid=None
                g["channels"]["swissprot"]={"pid":pid,"def":html.unescape(r.get("subject_def","")),
                    "organism":r.get("subject_organism",""),"acc":r.get("subject_acc",""),
                    "coverage":r.get("query_coverage","")}
                if pid is not None: n+=1
    if n:
        roster["channels_present"]=sorted(set(roster.get("channels_present",[]))|{"swissprot"})
        roster.setdefault("channels_absent",{}).pop("swissprot",None)
    _atomic_write_json(roster, rp, owner_dir=RD, indent=1)
    tot=sum(len(b["genes"]) for b in roster["bgcs"])
    return f"{strain}: Swiss-Prot on {n}/{tot} genes"

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--strain"); ap.add_argument("--all",action="store_true")
    a=ap.parse_args()
    strains=[os.path.basename(j)[:-len("_roster_v2.json")] for j in sorted(glob.glob(f"{RD}/*_roster_v2.json"))] if a.all else [a.strain]
    for s in strains:
        if s in EXCLUDE: continue
        emit(" ",enrich(s))
