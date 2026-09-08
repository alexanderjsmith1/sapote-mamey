#!/usr/bin/env python3
"""backfill_coords_from_antismash.py — for strains whose roster_v2.json lacks gene
coordinates (no sealed-package locus_maps), read start/end/strand/aa + domains straight
from the antiSMASH result JSON, and also backfill the general ClusterBlast channel.
Read-only on the antiSMASH data. Claim-safe: geometry + homology only.

Resolver checks known antiSMASH-zip homes in priority order (the seed of a canonical
per-strain antiSMASH/package folder system)."""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import json, io, os, re, glob, zipfile, argparse, collections, sys
import os
ROOT = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd())
RD=f"{ROOT}/sapote_deliverables/roster_v2"
_TOOLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
if _TOOLS_DIR not in sys.path: sys.path.insert(0, _TOOLS_DIR)
from _wbio import atomic_dump_json_owned as _atomic_write_json

def find_antismash_zip(strain):
    cands=[f"{ROOT}/strain_data/{strain}/antiSMASH/{strain}.zip",
           f"{ROOT}/strain_data/{strain}/antiSMASH/*.zip",
           f"{ROOT}/Antismash/{strain}.zip"]
    for pat in cands:
        for p in sorted(glob.glob(pat)):
            try:
                zf=zipfile.ZipFile(p)
                if any(n.endswith(".json") and "/input/" not in n and not n.startswith("input") for n in zf.namelist()):
                    return p
            except Exception: continue
    return None

def role_group(text):
    r=(text or "").lower()
    if "glycosyl" in r or ("sugar" in r and "pathway" not in r): return ("glycosyltransferase","#5b8def")
    if any(k in r for k in ("pks","nrps"," nrp","ripp","lanthi","lasso","ladderane","terpene_synth","t1pks","transat")): return ("biosynthetic core","#c9a227")
    if any(k in r for k in ("p450","methyltransferase","oxidoreductase","dehydrogenase","halogenase","monooxygenase","reductase","hydroxylase","aminotransferase")): return ("tailoring/redox","#6fbf73")
    if "regulat" in r or "transcription" in r: return ("regulator","#e86fa0")
    if "transport" in r or "abc" in r or "permease" in r or "mfs" in r: return ("transport","#4fb3b3")
    return ("other","#5aa9a0")

def parse_loc(s):
    m=re.search(r"\[<?(\d+):>?(\d+)\]\(([+-])\)", s or "")
    return (int(m.group(1)),int(m.group(2)),m.group(3)) if m else (None,None,"")

def cds_map(zpath):
    zf=zipfile.ZipFile(zpath)
    jn=[n for n in zf.namelist() if n.endswith(".json") and "/input/" not in n and not n.startswith("input")][0]
    d=json.load(io.TextIOWrapper(zf.open(jn),encoding="utf-8"))
    out={}
    cbg={}   # general clusterblast per locus (best perc_ident)
    for rec in d.get("records",[]):
        for f in rec.get("features",[]):
            if f.get("type")!="CDS": continue
            q=f.get("qualifiers",{})
            lt=(q.get("locus_tag") or q.get("gene") or [None])[0]
            if not lt: continue
            st,en,strand=parse_loc(f.get("location",""))
            tr=(q.get("translation") or [""])[0]
            gf=" ".join(q.get("gene_functions",[]) or []) or " ".join(q.get("sec_met_domain",[]) or [])
            doms=re.findall(r"([A-Za-z0-9_\-]+)\s*\(E-value", gf)
            out[lt]={"start":st,"end":en,"strand":strand,"aa":len(tr) if tr else None,
                     "gf":gf,"domains":list(dict.fromkeys(doms))[:4]}
        cb=rec.get("modules",{}).get("antismash.modules.clusterblast",{}).get("general",{})
        for res in cb.get("results",[]):
            for ref,score in res.get("ranking",[]):
                for pr in score.get("pairings",[]):
                    if isinstance(pr,list) and len(pr)>=3:
                        lt=next((p for p in pr[0].split("|") if re.match(r"ctg\d+_\d+$",p)),None)
                        try: pid=float(pr[2].get("perc_ident"))
                        except: continue
                        if lt and (lt not in cbg or pid>cbg[lt]["pid"]):
                            cbg[lt]={"pid":round(pid,1),"coverage":round(float(pr[2].get("perc_coverage",0)),1),
                                     "subject_gene":pr[2].get("name",""),"annotation":pr[2].get("annotation","") or "",
                                     "genecluster":pr[2].get("genecluster","")}
    return out, cbg

def backfill(strain):
    rp=f"{RD}/{strain}_roster_v2.json"
    if not os.path.exists(rp): return f"{strain}: no roster"
    z=find_antismash_zip(strain)
    if not z: return f"{strain}: NO antiSMASH zip found in any known home"
    cm, cbg = cds_map(z)
    r=json.load(open(rp)); nc=ncb=0
    for b in r["bgcs"]:
        for g in b["genes"]:
            lt=g["locus_tag"]; info=cm.get(lt)
            if info and g.get("start") is None and info["start"] is not None:
                g["start"],g["end"],g["strand"],g["aa"]=info["start"],info["end"],info["strand"],info["aa"] or g.get("aa")
                if not g.get("domains") and info["domains"]: g["domains"]=info["domains"]
                if not g.get("role") or g.get("role_group")=="other":
                    grp,col=role_group(info["gf"] or g.get("role","")); 
                    if grp!="other": g["role"]=g.get("role") or grp; g["role_group"],g["role_color"]=grp,col
                nc+=1
            if cbg.get(lt) and not g["channels"].get("clusterblast"):
                g["channels"]["clusterblast"]=cbg[lt]; ncb+=1
    if ncb: r["channels_present"]=sorted(set(r.get("channels_present",[]))|{"clusterblast"})
    _atomic_write_json(r, rp, owner_dir=RD, indent=1)
    return f"{strain}: +coords {nc} genes, +clusterblast {ncb} genes (from {os.path.basename(z)})"

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("strains",nargs="+"); a=ap.parse_args()
    for s in a.strains: emit(" ", backfill(s))
