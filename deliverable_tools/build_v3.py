#!/usr/bin/env python3
"""build_v3.py — v3 BGC protein roster: per-BGC synthesis headers (with denominators),
reference-dark novelty flagging, 4-channel gene tables, and a novelty-first lead-ranking
front table. Reads roster_v2.json (nr/MIBiG/ClusterBlast/Swiss-Prot).
Claim-safe: homology & capacity only; predicted != measured; judgment deferred.
Implements Amber's v3 suggestions (2026-08-03).
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, glob, json, os, re, statistics as st
import os
ROOT = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd())
RD=f"{ROOT}/sapote_deliverables/roster_v2"

def fam(p):
    p=(p or "").lower();pks=any(x in p for x in("pks","transat"));nrp=any(x in p for x in("nrps","nrp","napaa"));ripp=any(x in p for x in("ripp","lasso","lanthi","rre"))
    if pks and nrp:return"PKS–NRPS hybrid"
    if pks and ripp:return"PKS–RiPP hybrid"
    if pks:return"PKS"
    if nrp:return"NRPS"
    if ripp:return"RiPP"
    return"Other"
def kcb(k):
    if not k:return"—"
    p=[x.strip() for x in k.split("|")];return f"{p[1]} ({p[0].split('.')[0]})" if len(p)>1 and p[1] else p[0].split(".")[0]
def ns(n):
    m=re.match(r"(NODE_\d+)",n or "");return m.group(1) if m else (n or "?")
def tr(s,n):s=s or "";return s if len(s)<=n else s[:n-1]+"…"
def med(xs):xs=[x for x in xs if x is not None];return round(st.median(xs),1) if xs else None
def is_core(g):return "core" in (g.get("role_group") or "").lower() or re.search(r"module|ripp",(g.get("role") or ""),re.I)
def is_specialised(prod):
    p=(prod or "").lower()
    if any(x in p for x in("pks","nrps","nrp","ripp","lasso","lanthi","transat","napaa","siderophore","nrp-metallophore")):return True
    if re.fullmatch(r"[\s;]*((saccharide|terpene|betalactone|other|butyrolactone|ectoine|melanin|hserlactone)[\s;]*)+",p):return False
    return True

def synth(b):
    G=b["genes"];n=len(G)
    def ch(k):return [g["channels"][k] for g in G if g["channels"].get(k)]
    nr=[c["pid"] for c in ch("nr") if c.get("pid") is not None]
    mi=[c["pid"] for c in ch("mibig") if c.get("pid") is not None]
    cb=[c["pid"] for c in ch("clusterblast") if c.get("pid") is not None]
    sp=[c["pid"] for c in ch("swissprot") if c.get("pid") is not None]
    dark=[g for g in G if (g["channels"].get("nr") and g["channels"]["nr"].get("pid") is not None and g["channels"]["nr"]["pid"]<60)]
    no_nr=[g for g in G if not g["channels"].get("nr")]
    no_mi=[g for g in G if not g["channels"].get("mibig")]
    core=[g for g in G if is_core(g)]
    core_dark=[g for g in core if g["channels"].get("nr") and g["channels"]["nr"].get("pid") is not None and g["channels"]["nr"]["pid"]<60]
    core_no_nr=[g for g in core if not g["channels"].get("nr")]
    comps=[c["compound"] for c in ch("mibig") if c.get("compound")]
    dom_comp=("—",0)
    if comps:
        from collections import Counter; mc=Counter(comps).most_common(1)[0]; dom_comp=(mc[0],mc[1])
    coherent = comps and dom_comp[1] >= 0.6*len(comps)
    return {"n":n,"nr_h":len(nr),"nr_med":med(nr),"mi_h":len(mi),"mi_med":med(mi),
            "cb_h":len(cb),"sp_h":len(sp),"dark":len(dark),"no_nr":len(no_nr),"no_mi":len(no_mi),
            "core":len(core),"core_dark":len(core_dark),"core_no_nr":len(core_no_nr),"dom_comp":dom_comp,"coherent":bool(coherent),
            "specialised":is_specialised(b["products"]),"boundary":b.get("boundary","")}

def lead_score(s):
    # confirmed reference-dark core weighs most; no-nr core is a COVERAGE gap, not novelty
    return (s["core_dark"]*3) + (s["core"] and s["core_dark"]/max(1,s["core"]))*2 + \
           (s["no_mi"]/max(1,s["n"])) + (1 if s["specialised"] else -1) + (s["dark"]/max(1,s["n"]))

def build(strain):
    d=json.load(open(f"{RD}/{strain}_roster_v2.json"))
    bgcs=[b for b in d["bgcs"] if b["genes"]]
    for b in bgcs: b["_s"]=synth(b)
    present=d.get("channels_present",[])
    has={k:any(g["channels"].get(k) for b in bgcs for g in b["genes"]) for k in("nr","swissprot","mibig","clusterblast")}
    # lead ranking
    ranked=sorted(bgcs,key=lambda b:-lead_score(b["_s"]))
    L=[f"# {strain} — BGC protein roster (v3)","",
       "Per-BGC **synthesis** + per-gene 4-channel detail + **reference-dark** novelty flags, novelty-first.",
       f"*{strain} · {len(bgcs)} BGCs · {sum(b['_s']['n'] for b in bgcs)} genes · channels: "
       f"{', '.join(k for k in ('nr','swissprot','mibig','clusterblast') if has[k])} · generated {d['generated']}*","",
       "> **Homology & capacity only.** Every %id is a class-level lead — \"capacity consistent with,\" never "
       "\"produces\"; predicted ≠ measured; judgment deferred. `◄dark` = nr %id < 60 (reference-dark, novelty-leaning). "
       "MIBiG compound names & cross-channel agreement are similarity anchors, not independent confirmation.","",
       "## Lead ranking (novelty-first)","",
       "Ranked by **confirmed** core reference-dark genes (nr hit <60%), no-MIBiG fraction, and specialised class. "
       "`core nr-todo` = core genes not yet nr-BLASTed (a coverage gap, NOT evidence of novelty — run nr to resolve). "
       "Saccharide/terpene-only/other are marked non-specialised (flagged with denominator, not arbitrarily down-weighted).","",
       "| rank | BGC | class | core dark (nr<60) | core nr-todo | nr cov | med nr%id | no-MIBiG | dominant MIBiG (recurrence) | note |",
       "|--:|---|---|:-:|:-:|--:|--:|--:|---|---|"]
    for i,b in enumerate(ranked,1):
        s=b["_s"];fl=[]
        if s["core_dark"]: fl.append(f"**{s['core_dark']} confirmed core-dark**")
        if s["core_no_nr"]: fl.append(f"{s['core_no_nr']} core nr-todo")
        if not s["specialised"]: fl.append("non-specialised")
        if s["boundary"] and s["boundary"].lower()!="interior": fl.append(s["boundary"])
        if s["coherent"]: fl.append("coherent")
        elif s["mi_h"]: fl.append("mosaic")
        L.append(f"| {i} | {b['bgc_id']} | {tr(b['products'],26)} | {s['core_dark']}/{s['core']} | "
                 f"{s['core_no_nr']}/{s['core']} | {s['nr_h']}/{s['n']} | {s['nr_med'] if s['nr_med'] is not None else '—'} | {s['no_mi']}/{s['n']} | "
                 f"{tr(s['dom_comp'][0],20)} (×{s['dom_comp'][1]}) | {', '.join(fl) or '—'} |")
    # per-BGC blocks grouped by class family, but ordered by lead rank within
    L+=["","---","","## Per-BGC detail",""]
    cols=["#","gene","±","aa","role","domains"]
    if has["nr"]:cols.append("nr %id")
    if has["swissprot"]:cols.append("SwissProt %id")
    if has["mibig"]:cols.append("MIBiG · compound %id")
    if has["clusterblast"]:cols.append("CB %id")
    cols.append("flag")
    hdr="| "+" | ".join(cols)+" |"
    sep="|"+"|".join(["--:" if c in("#","aa") else ":-:" if c=="±" else "---" for c in cols])+"|"
    for b in ranked:
        s=b["_s"]
        L.append(f"### {strain} · {b['bgc_id']} · {ns(b['node'])} · {b.get('region','')} · {fam(b['products'])}".rstrip())
        L.append(f"**Class:** {b['products'] or '?'} · **Boundary:** {s['boundary'] or '?'} · **{b.get('length_kb','?') or '?'} kb** · **KCB:** {kcb(b['kcb_top'])}")
        # synthesis line with denominators
        syn=(f"**Synthesis —** {s['n']} genes · nr hit {s['nr_h']}/{s['n']}"
             f"{f' (med {s['nr_med']}%)' if s['nr_med'] is not None else ''} · "
             f"MIBiG {s['mi_h']}/{s['n']}{f' (med {s['mi_med']}%)' if s['mi_med'] is not None else ''} · "
             f"ClusterBlast {s['cb_h']}/{s['n']} · SwissProt {s['sp_h']}/{s['n']} · "
             f"reference-dark (nr<60) {s['dark']}/{s['nr_h'] or 0} · no-nr {s['no_nr']}/{s['n']} · "
             f"**core ref-dark (nr<60) {s['core_dark']}/{s['core']}** · core nr-todo {s['core_no_nr']}/{s['core']} · "
             f"dominant MIBiG {tr(s['dom_comp'][0],24)} ×{s['dom_comp'][1]} · {'coherent family' if s['coherent'] else ('mosaic' if s['mi_h'] else 'no MIBiG')}")
        L+= ["",syn,"",hdr,sep]
        for i,g in enumerate(b["genes"],1):
            nr=g["channels"].get("nr");sp=g["channels"].get("swissprot");mi=g["channels"].get("mibig");cb=g["channels"].get("clusterblast")
            row=[str(g["order"] or i),f"`{g['locus_tag']}`",g["strand"] or "?",str(g["aa"] or ""),
                 g["role"] or "—",tr((", ".join(g["domains"][:3]) if g["domains"] else (g.get("smcog","") or "—")),24)]
            if has["nr"]:row.append(f"{tr(nr['def'],30)} · {nr['pid']}%" if nr and nr.get('pid') is not None else "—")
            if has["swissprot"]:row.append(f"{tr(sp['def'].replace('RecName: Full=','') if sp else '',22)} · {sp['pid']}%" if sp and sp.get('pid') is not None else "—")
            if has["mibig"]:row.append(f"{tr(mi.get('compound',''),18)} · {mi['pid']}%" if mi and mi.get('pid') is not None else "—")
            if has["clusterblast"]:row.append(f"{cb['pid']}%" if cb and cb.get('pid') is not None else "—")
            flag=[]
            if nr and nr.get('pid') is not None and nr['pid']<60: flag.append("◄dark")
            elif not nr: flag.append("no-nr")
            if not mi: flag.append("no-MIBiG")
            if is_core(g): flag.append("core")
            row.append(" ".join(flag))
            L.append("| "+" | ".join(row)+" |")
        L.append("")
    out=f"{RD}/{strain}_BGC_protein_roster_v3.md"
    open(out,"w").write("\n".join(L))
    return out,len(bgcs)

if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("--strain");ap.add_argument("--all",action="store_true");a=ap.parse_args()
    strains=[os.path.basename(j)[:-len("_roster_v2.json")] for j in sorted(glob.glob(f"{RD}/*_roster_v2.json"))] if a.all else [a.strain]
    for s in strains:
        o,n=build(s);emit(f"v3 md: {os.path.basename(o)} ({n} BGCs)")
