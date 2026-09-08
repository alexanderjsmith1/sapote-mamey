#!/usr/bin/env python3
"""Rebuild the v1 BGC protein roster (best-NCBI-nr-hit-per-gene, grouped by BGC
class family) from the refreshed roster_v2 JSON. Keeps the established v1 format.
Usage: build_v1.py --strain AS-XXX   |   build_v1.py --all
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import json, glob, os, re, argparse, html
import os

ROOT = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd())
RD   = f"{ROOT}/sapote_deliverables/roster_v2"

def family(products):
    p = products.lower()
    has_nrps = 'nrps' in p
    has_pks  = any(x in p for x in ('t1pks','t2pks','t3pks','transat-pks','hgle-ks','pks'))
    if has_nrps and has_pks: return "PKS–NRPS hybrid"
    if has_nrps: return "NRPS"
    if has_pks:
        if 't3pks' in p: return "T3PKS"
        if 't2pks' in p: return "T2PKS"
        if 't1pks' in p or 'transat' in p: return "T1PKS"
        return "PKS"
    ripp = ('ripp','lanthipeptide','lassopeptide','lasso','thiopeptide','lap',
            'ranthipeptide','sactipeptide','linaridin','thioamitides','rre-containing',
            'redox-cofactor','microviridin','cyanobactin','bottromycin','glycocin',
            'proteusin','epipeptide','spliceotide','guanidinotides','head_to_tail')
    if any(x in p for x in ripp): return "RiPP"
    if 'terpene' in p: return "Terpene"
    if 'siderophore' in p: return "NI-siderophore" if 'ni-siderophore' in p else "Siderophore"
    if 'saccharide' in p: return "Saccharide"
    if 'betalactone' in p: return "Betalactone"
    if 'butyrolactone' in p: return "Butyrolactone"
    if 'ectoine' in p: return "Ectoine"
    if 'melanin' in p: return "Melanin"
    if 'phosphonate' in p: return "Phosphonate"
    if 'indole' in p: return "Indole"
    if 'arylpolyene' in p: return "Arylpolyene"
    if 'nucleoside' in p: return "Nucleoside"
    if 'other' in p: return "Other"
    first = products.split(';')[0].strip()
    return first or "Other"

def node_short(node):
    m = re.match(r"(NODE_\d+)", node or "")
    return m.group(1) if m else (node or "—")

def kcb_line(kcb_top, kcb_score):
    if not kcb_top or kcb_top.strip() in ("", "—"):
        return "—  (score )"
    parts = [x.strip() for x in kcb_top.split("|")]
    bgcid = parts[0] if parts else ""
    bgcid = re.sub(r"\.\d+$", "", bgcid)          # strip version suffix
    compound = parts[1] if len(parts) > 1 else ""
    sc = kcb_score or ""
    if compound:
        return f"{compound} ({bgcid})  (score {sc})"
    return f"{bgcid}  (score {sc})"

def build(strain):
    jp = f"{RD}/{strain}_roster_v2.json"
    if not os.path.exists(jp): return None, f"no JSON for {strain}"
    d = json.load(open(jp))
    gen = d.get("generated", "")
    # only BGCs with >=1 nr-hit gene
    rows = []   # (bgcnum, fam, bgc)
    for b in d["bgcs"]:
        nrg = [g for g in b["genes"] if g["channels"].get("nr")]
        if not nrg: continue
        num = int(re.sub(r"\D","", b["bgc_id"]) or 0)
        rows.append((num, family(b.get("products","")), b, nrg))
    rows.sort(key=lambda x: x[0])
    nbgc = len(rows)
    nprot = sum(len(nrg) for *_ , nrg in rows)
    out = []
    out.append(f"# {strain} — BGC protein roster (v1)\n")
    out.append("Every antiSMASH-called protein per BGC with its **best NCBI-nr BLASTp hit** "
               "(rank-1 = highest bitscore) and % identity. Grouped by BGC class family.\n")
    out.append(f"*Strain {strain} · {nbgc} BGCs with nr BLASTp · {nprot} proteins · "
               f"channel = ncbi_nr · generated {gen}*\n")
    out.append("> **Homology, not function.** Each hit is a class-level lead — "
               "\"capacity consistent with,\" never \"produces.\" %id is shown so the reader "
               "can weight each call. BLASTp best hit ≠ product identity.\n")
    # group by family in first-seen order
    fam_order, fam_map = [], {}
    for num, fam, b, nrg in rows:
        if fam not in fam_map:
            fam_map[fam] = []; fam_order.append(fam)
        fam_map[fam].append((b, nrg))
    for fam in fam_order:
        out.append(f"\n## {fam}\n")
        for b, nrg in fam_map[fam]:
            out.append(f"### {strain} · {b['bgc_id']} · {node_short(b.get('node'))}")
            out.append(f"**Class:** {b.get('products','')}  ·  **Length:** {b.get('length_kb','')} kb")
            out.append(f"**KCB top:** {kcb_line(b.get('kcb_top',''), b.get('kcb_score',''))}\n")
            for i, g in enumerate(nrg, 1):
                nr = g["channels"]["nr"]
                dfn = html.unescape(nr.get("def","") or "")
                pid = nr.get("pid")
                pids = f"{float(pid):.1f}" if pid is not None else "?"
                out.append(f"{i:>2}. `{g['locus_tag']}` — {dfn} · **{pids}% id**")
            out.append("")
    txt = "\n".join(out).rstrip() + "\n"
    op = f"{RD}/{strain}_BGC_protein_roster_v1.md"
    open(op, "w").write(txt)
    return {"strain":strain,"bgcs":nbgc,"proteins":nprot,"path":op}, None

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--strain"); ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    strains = ([os.path.basename(j)[:-len("_roster_v2.json")] for j in sorted(glob.glob(f"{RD}/*_roster_v2.json"))]
               if a.all else [a.strain])
    for s in strains:
        res, err = build(s)
        emit(f"v1 md: {os.path.basename(res['path'])} ({res['bgcs']} BGCs, {res['proteins']} proteins)" if res else f"  {err}")
