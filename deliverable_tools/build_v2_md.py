#!/usr/bin/env python3
"""build_v2_md.py — detailed v2 markdown (+ optional docx) from roster_v2.json,
reproducing the AS-XXX_BGC_protein_roster_v2 format: class-family grouped, per-BGC
header, 8-col gene table (role, domains, nr hit %id, MIBiG compound %id).
Adds a ClusterBlast %id column when that channel is populated.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import json, glob, os, re, sys
import os
ROOT = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd())
RD=f"{ROOT}/sapote_deliverables/roster_v2"

def fam(p):
    p=(p or "").lower();pks=any(x in p for x in("pks","transat"));nrp=any(x in p for x in("nrps","nrp","napaa"));ripp=any(x in p for x in("ripp","lasso","lanthi","rre"))
    if pks and nrp:return"1 · PKS–NRPS hybrid"
    if pks and ripp:return"3 · PKS–RiPP hybrid"
    if pks:return"2 · PKS"
    if nrp:return"4 · NRPS"
    if ripp:return"5 · RiPP"
    return"6 · Other"
def kcb(k):
    if not k:return"—"
    p=[x.strip() for x in k.split("|")];return f"{p[1]} ({p[0].split('.')[0]})" if len(p)>1 and p[1] else p[0].split(".")[0]
def ns(n):
    m=re.match(r"(NODE_\d+)",n or "");return m.group(1) if m else (n or "?")
def tr(s,n):s=s or "";return s if len(s)<=n else s[:n-1]+"…"

def build(strain):
    d=json.load(open(f"{RD}/{strain}_roster_v2.json"))
    has_cb=any(g["channels"].get("clusterblast") for b in d["bgcs"] for g in b["genes"])
    bgcs=sorted([b for b in d["bgcs"] if b["genes"]],key=lambda b:(fam(b["products"]),int(re.sub(r"\D","",b["bgc_id"]) or 0)))
    L=[f"# {strain} — BGC protein roster (v2, detailed / multi-channel)","",
       "Per-gene view: genomic order, strand, length, **role**, **antiSMASH domains**, and best hit in each homology channel.",
       f"*{strain} · {len(bgcs)} BGCs · {sum(len(b['genes']) for b in bgcs)} genes · generated {d['generated']}*","",
       "**Channels:** `nr` = NCBI-nr BLASTp · `MIBiG` = KnownClusterBlast per-gene (compound + %id) · "
       +("`ClusterBlast` = antiSMASH general per-gene %id · " if has_cb else "")+
       "`Swiss-Prot` = not run.","",
       "> **Homology, not function.** Domains are antiSMASH capacity calls; channel hits are class-level leads. "
       "\"Capacity consistent with,\" never \"produces.\" A MIBiG compound name is a similarity anchor.",""]
    cur=None
    for b in bgcs:
        f=fam(b["products"])
        if f!=cur:cur=f;L+=["",f"## {f.split('· ',1)[1]}",""]
        L.append(f"### {strain} · {b['bgc_id']} · {ns(b['node'])} · {b.get('region','')}".rstrip())
        L.append(f"**Class:** {b['products'] or '?'} · **Boundary:** {b.get('boundary','?') or '?'} · "
                 f"**{b.get('length_kb','?') or '?'} kb** · **KCB:** {kcb(b['kcb_top'])} (score {b.get('kcb_score','')})")
        L.append("")
        hdr="| # | gene | ± | aa | role | domains | nr best hit (%id) | MIBiG · compound (%id) |"
        sep="|--:|---|:-:|--:|---|---|---|---|"
        if has_cb: hdr=hdr[:-1]+" ClusterBlast (%id) |"; sep=sep[:-1]+"---|"
        L+= [hdr,sep]
        for i,g in enumerate(b["genes"],1):
            nr=g["channels"]["nr"];mi=g["channels"]["mibig"];cb=g["channels"].get("clusterblast")
            nrs=f"{tr(nr['def'],36)} · {nr['pid']}%" if nr and nr.get('pid') is not None else "—"
            mis=f"{tr(mi.get('compound',''),22)} · {mi['pid']}%" if mi and mi.get('pid') is not None else "—"
            dom=", ".join(g["domains"][:3]) if g["domains"] else (g.get("smcog","") or "—")
            row=(f"| {g['order'] if g['order'] else i} | `{g['locus_tag']}` | {g['strand'] or '?'} | {g['aa'] or ''} | "
                 f"{g['role'] or '—'} | {tr(dom,26)} | {nrs} | {mis} |")
            if has_cb:
                cbs=f"{tr((cb.get('annotation','') or '').replace('_',' '),20)} · {cb['pid']}%" if cb and cb.get('pid') is not None else "—"
                row=row+f" {cbs} |"
            L.append(row)
        L.append("")
    out=f"{RD}/{strain}_BGC_protein_roster_v2.md"
    open(out,"w").write("\n".join(L))
    return out

if __name__=="__main__":
    strains=[os.path.basename(j)[:-len("_roster_v2.json")] for j in sorted(glob.glob(f"{RD}/*_roster_v2.json"))] if sys.argv[1:]==["--all"] else sys.argv[1:]
    for s in strains: emit("md:",os.path.basename(build(s)))
