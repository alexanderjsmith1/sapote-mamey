#!/usr/bin/env python3
"""enrich_clusterblast.py — add the general antiSMASH ClusterBlast channel to a
strain's roster_v2.json, parsed from its antiSMASH JSON. Best perc_ident per gene
across all general-clusterblast rankings. Reader-side, homology-only.

Usage: python enrich_clusterblast.py --strain AS-XXX [--rosterdir DIR]
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, json, glob, os, re, zipfile, io, sys
import os

ROOT = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd())
_TOOLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
if _TOOLS_DIR not in sys.path: sys.path.insert(0, _TOOLS_DIR)
from _wbio import atomic_dump_json_owned as _atomic_write_json

def find_json(strain):
    for z in glob.glob(f"{ROOT}/strain_data/{strain}/antiSMASH/*.zip") + \
             glob.glob(f"{ROOT}/**/{strain}.zip", recursive=True):
        try:
            zf = zipfile.ZipFile(z)
            names = [n for n in zf.namelist() if n.endswith(".json") and strain in n]
            if names: return zf, names[0]
        except Exception: continue
    return None, None

def locus_from_query(q):
    # "input|c1|2-4766|+|ctg1_1|" -> ctg1_1
    parts = q.split("|")
    for p in parts:
        if re.match(r"ctg\d+_\d+$", p): return p
    return None

def clusterblast_by_gene(data):
    best = {}   # locus_tag -> dict
    for rec in data.get("records", []):
        cb = rec.get("modules", {}).get("antismash.modules.clusterblast")
        if not cb: continue
        gen = cb.get("general", {})
        for res in gen.get("results", []):
            for ref, score in res.get("ranking", []):
                for pr in score.get("pairings", []):
                    if not (isinstance(pr, list) and len(pr) >= 3): continue
                    q, _, hit = pr[0], pr[1], pr[2]
                    lt = locus_from_query(q)
                    if not lt: continue
                    try: pid = float(hit.get("perc_ident"))
                    except Exception: continue
                    cur = best.get(lt)
                    if cur is None or pid > cur["pid"]:
                        best[lt] = {"pid": round(pid,1),
                            "coverage": round(float(hit.get("perc_coverage",0)),1),
                            "subject_gene": hit.get("name",""),
                            "annotation": hit.get("annotation","") or "",
                            "genecluster": hit.get("genecluster","")}
    return best

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--strain", required=True)
    ap.add_argument("--rosterdir", default=f"{ROOT}/sapote_deliverables/roster_v2")
    a = ap.parse_args()
    rp = f"{a.rosterdir}/{a.strain}_roster_v2.json"
    if not os.path.exists(rp): emit(f"no roster: {rp}"); return
    zf, name = find_json(a.strain)
    if not zf: emit(f"{a.strain}: no antiSMASH json found"); return
    data = json.load(io.TextIOWrapper(zf.open(name), encoding="utf-8"))
    cbg = clusterblast_by_gene(data)
    roster = json.load(open(rp))
    n = 0
    for b in roster["bgcs"]:
        for g in b["genes"]:
            hit = cbg.get(g["locus_tag"])
            if hit:
                g["channels"]["clusterblast"] = hit; n += 1
    roster["channels_present"] = sorted(set(roster.get("channels_present", [])) | {"clusterblast"})
    roster.setdefault("channels_absent", {}).pop("clusterblast_general", None)
    _atomic_write_json(roster, rp, owner_dir=a.rosterdir, indent=1)
    tot = sum(len(b["genes"]) for b in roster["bgcs"])
    emit(f"{a.strain}: general ClusterBlast added for {n}/{tot} genes ({len(cbg)} genes hit in JSON)")

if __name__ == "__main__": main()
