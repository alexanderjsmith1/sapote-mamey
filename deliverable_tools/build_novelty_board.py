#!/usr/bin/env python3
"""build_novelty_board.py — cross-strain novelty board: each strain's top v3 leads,
aggregated and ranked by CONFIRMED reference-dark core genes (nr hit <60%). Coverage
gaps (core nr-todo) are shown but never counted as novelty. Claim-safe: capacity/homology,
judgment deferred.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import glob, json, os, sys, importlib.util
import os
ROOT = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd()); RD=f"{ROOT}/sapote_deliverables/roster_v2"
spec=importlib.util.spec_from_file_location("bv3", f"{ROOT}/sapote_deliverables/tools/build_v3.py")
bv3=importlib.util.module_from_spec(spec); spec.loader.exec_module(bv3)

rows=[]
for j in sorted(glob.glob(f"{RD}/*_roster_v2.json")):
    d=json.load(open(j)); strain=d["strain"]
    bgcs=[b for b in d["bgcs"] if b["genes"]]
    for b in bgcs: b["_s"]=bv3.synth(b)
    ranked=sorted(bgcs,key=lambda b:-bv3.lead_score(b["_s"]))
    for b in ranked[:3]:
        s=b["_s"]
        rows.append({"strain":strain,"bgc":b["bgc_id"],"node":bv3.ns(b["node"]),
            "class":b["products"],"fam":bv3.fam(b["products"]),"core_dark":s["core_dark"],
            "core":s["core"],"core_todo":s["core_no_nr"],"nr_h":s["nr_h"],"n":s["n"],
            "no_mi":s["no_mi"],"nr_med":s["nr_med"],"dom":s["dom_comp"],"boundary":s["boundary"],
            "spec":s["specialised"],"coherent":s["coherent"],"score":round(bv3.lead_score(s),2)})

# rank: confirmed core-dark desc, then fraction, then score. Specialised only for headline.
rows.sort(key=lambda r:(-r["core_dark"], -(r["core_dark"]/max(1,r["core"])), -r["score"]))

def tr(s,n):s=s or "";return s if len(s)<=n else s[:n-1]+"…"
L=["# AS cohort — BGC novelty board (v3 leads)","",
   f"*Top 3 leads per strain across {len({r['strain'] for r in rows})} strains → {len(rows)} candidate BGCs, "
   "ranked by **confirmed reference-dark core** genes (nr best hit <60% id). Generated 2026-08-03.*","",
   "> **Capacity & homology only, judgment deferred.** A reference-dark core = a biosynthetic-core gene whose "
   "closest nr protein is <60% identical — a **novelty-leaning** signal, not a structure or activity claim. "
   "`core nr-todo` = core genes not yet nr-BLASTed (a coverage gap; run nr to resolve — NOT counted as novelty). "
   "Every count carries its denominator.","",
   "| # | strain | BGC · node | class | core dark (nr<60) | core nr-todo | nr cov | no-MIBiG | dominant MIBiG (×) | flags |",
   "|--:|---|---|---|:-:|:-:|--:|--:|---|---|"]
for i,r in enumerate(rows,1):
    fl=[]
    if not r["spec"]: fl.append("non-specialised")
    if r["boundary"] and r["boundary"].lower()!="interior": fl.append(r["boundary"])
    fl.append("coherent" if r["coherent"] else "mosaic")
    L.append(f"| {i} | {r['strain']} | {r['bgc']} · {r['node']} | {tr(r['class'],28)} | "
             f"**{r['core_dark']}/{r['core']}** | {r['core_todo']}/{r['core']} | {r['nr_h']}/{r['n']} | "
             f"{r['no_mi']}/{r['n']} | {tr(r['dom'][0],20)} (×{r['dom'][1]}) | {', '.join(fl)} |")
# headline: confirmed-dark, specialised, full-ish nr coverage
head=[r for r in rows if r["core_dark"]>=2 and r["spec"] and r["nr_h"]>=0.8*r["n"]]
L+=["","## Headline leads (≥2 confirmed core-dark, specialised class, ≥80% nr coverage)","",
    "These are the most defensible novelty candidates — divergent cores that are actually BLASTed, not coverage gaps.",""]
for r in head[:20]:
    L.append(f"- **{r['strain']} {r['bgc']}** ({bv3.fam(r['class'])}) — {r['core_dark']}/{r['core']} core genes <60% nr, "
             f"nr {r['nr_h']}/{r['n']}, dominant MIBiG anchor {tr(r['dom'][0],28)} (×{r['dom'][1]}); "
             f"{'coherent family' if r['coherent'] else 'mosaic'}.")
open(f"{ROOT}/sapote_deliverables/AS_cohort_novelty_board.md","w").write("\n".join(L))
# csv
import csv
try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
with open(f"{ROOT}/sapote_deliverables/AS_cohort_novelty_board.csv","w",newline="") as f:
    w=_SafeWriter(f); w.writerow(["rank","strain","bgc","node","class","family","core_dark_confirmed","core_total","core_nr_todo","nr_hits","genes","no_mibig","nr_median_pid","dominant_mibig","recurrence","boundary","specialised","coherent","lead_score"])
    for i,r in enumerate(rows,1):
        w.writerow([i,r["strain"],r["bgc"],r["node"],r["class"],r["fam"],r["core_dark"],r["core"],r["core_todo"],r["nr_h"],r["n"],r["no_mi"],r["nr_med"],r["dom"][0],r["dom"][1],r["boundary"],r["spec"],r["coherent"],r["score"]])
emit(f"novelty board: {len(rows)} leads, {len(head)} headline")
