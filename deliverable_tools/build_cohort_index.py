#!/usr/bin/env python3
"""build_cohort_index.py — cohort index (md + html landing) over all roster_v2 JSONs."""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import json, glob, os, re
import os


# v9.7.417 IMPORT SAFETY. Everything below this line used to run at MODULE IMPORT: this file
# has no `__main__` guard and its top level is a script, so `import build_cohort_index`
# wrote real deliverables into $SAPOTE_WORKSPACE_ROOT as a side effect. Any tree-walking
# tool that imports rather than parses would have triggered it. The body below is UNCHANGED
# and only indented under the guard, so running this file as a script behaves exactly as
# before, and importing it now does nothing. Checked by AST equality against the pre-patch
# body, statement for statement, and by importing the module and asserting no file appears.
if __name__ == "__main__":   # v9.7.417 import safety — see tests/test_tools_import_safe_v97250.py
    ROOT = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd())
    RD=f"{ROOT}/sapote_deliverables/roster_v2"; WD=f"{ROOT}/sapote_deliverables/widgets"
    rows=[]
    for j in sorted(glob.glob(f"{RD}/*_roster_v2.json"), key=lambda p:int(re.sub(r"\D","",os.path.basename(p)) or 0)):
        d=json.load(open(j)); s=d["strain"]
        genes=[g for b in d["bgcs"] for g in b["genes"]]; ng=len(genes)
        cov=lambda ch: sum(1 for g in genes if g["channels"].get(ch))
        rows.append({"s":s,"bgcs":len(d["bgcs"]),"genes":ng,"nr":cov("nr"),"mibig":cov("mibig"),
                     "cb":cov("clusterblast"),"sp":cov("swissprot"),
                     "present":",".join(d.get("channels_present",[]))})
    tot=lambda k: sum(r[k] for r in rows)
    # markdown
    L=["# AS cohort — v2 roster / widget index","",
       f"*{len(rows)} strains · {tot('genes')} genes · generated 2026-08-03. Per-gene multi-channel rosters + interactive widgets.*","",
       "Channel coverage = genes with a best hit in that channel (numerator); denominator = total genes in the strain's rostered BGCs. Empty = channel not run.","",
       "| strain | BGCs | genes | nr | MIBiG | ClusterBlast | Swiss-Prot | widget | data |",
       "|---|--:|--:|--:|--:|--:|--:|---|---|"]
    for r in rows:
        wl=f"[widget](widgets/{r['s']}_BGC_widget.html)"
        dl=f"[json](roster_v2/{r['s']}_roster_v2.json)"
        L.append(f"| {r['s']} | {r['bgcs']} | {r['genes']} | {r['nr']} | {r['mibig']} | {r['cb']} | {r['sp']} | {wl} | {dl} |")
    L+= ["",f"**Totals:** nr {tot('nr')} · MIBiG {tot('mibig')} · ClusterBlast {tot('cb')} · Swiss-Prot {tot('sp')} (of {tot('genes')} genes).","",
       "> Homology, not function. Every channel %id is a class-level lead; empty channels are untested, not biological absence."]
    open(f"{ROOT}/sapote_deliverables/AS_cohort_roster_index.md","w").write("\n".join(L))
    # html landing
    cards="".join(f'<a class="c" href="{r["s"]}_BGC_widget.html"><b>{r["s"]}</b><span>{r["bgcs"]} BGCs · {r["genes"]} genes</span>'
    f'<span class="m">nr {r["nr"]} · MIBiG {r["mibig"]} · CB {r["cb"]}</span></a>' for r in rows)
    html=f'''<!doctype html><meta charset="utf-8"><title>AS cohort widgets</title>
<style>body{{background:#0e0f12;color:#e7e9ee;font:14px -apple-system,sans-serif;margin:0;padding:22px}}
h1{{font-size:16px}}.g{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px;margin-top:16px}}
a.c{{display:flex;flex-direction:column;gap:4px;background:#16181d;border:1px solid #262a31;border-radius:10px;padding:12px 14px;text-decoration:none;color:#e7e9ee}}
a.c:hover{{border-color:#5b8def}}a.c span{{color:#8b91a0;font-size:12px}}a.c .m{{color:#6fbf73;font-size:11px}}</style>
<h1>AS cohort — per-BGC gene widgets (v2)</h1><div style="color:#8b91a0;font-size:12px">{len(rows)} strains · {tot("genes")} genes · homology-only, judgment deferred</div>
<div class="g">{cards}</div>'''
    open(f"{WD}/index.html","w").write(html)
    emit(f"index: {len(rows)} strains, {tot('genes')} genes", f"  AS_cohort_roster_index.md + widgets/index.html", sep="\n")
