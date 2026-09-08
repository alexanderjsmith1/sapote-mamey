#!/usr/bin/env python3
"""roster_v2.py — per-BGC, multi-channel gene roster (v2) for a Sapote-Mamey AS strain.

Joins, per gene: genomic map (coords/strand/role/domains from the sealed package
locus_maps) + best NCBI-nr BLASTp hit + best MIBiG (KnownClusterBlast) hit with
compound name. Emits roster_v2.json (widget contract) and a detailed markdown.

Channels: nr (populated from the strain nr flat file), mibig (from the cohort
ClusterBlast gene master), swissprot + clusterblast (slots; populated elsewhere).

Claim-safe: homology only. A hit is a class-level lead, never a product/activity call.

Usage:
  python roster_v2.py --strain AS-XXX [--outdir DIR]
  python roster_v2.py --all           [--outdir DIR]
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, glob, html, json, os, re, collections
import os

ROOT = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd())
GMASTER = f"{ROOT}/strain_data/ClusterBlast_Gene_Master/CLUSTERBLAST_GENE_MASTER.csv"
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

_INV_VER_RE = re.compile(r"v(\d+)\.(\d+)\.(\d+)")


def _inventory_freshness_key(p):
    """Bundle-version freshness for an inventory path: the newest parseable
    ``vX.Y.Z`` among sibling ``*Complete_Package.zip`` names in the strain dir
    (covers versionless per-strain homes), else the newest version token in the
    path itself, else (-1,-1,-1). Freshness-blind picking previously returned
    stale seals whenever multiple package generations coexisted."""
    best = (-1, -1, -1)
    strain_dir = os.path.dirname(os.path.dirname(p))
    try:
        for name in os.listdir(strain_dir):
            if name.endswith("Complete_Package.zip"):
                for m in _INV_VER_RE.finditer(name):
                    t = tuple(int(x) for x in m.groups())
                    if t > best: best = t
    except OSError:
        pass
    if best == (-1, -1, -1):
        for m in _INV_VER_RE.finditer(p):
            t = tuple(int(x) for x in m.groups())
            if t > best: best = t
    return best


def resolve_inventory(strain):
    """Pick the canonical *_2_inventory.csv for a strain: newest bundle version
    first (sibling-package or path token), then home preference, then mtime."""
    cands = []
    for p in glob.glob(f"{ROOT}/**/{strain}_2_inventory.csv", recursive=True):
        if "/old/" in p: continue
        cands.append(p)
    def score(p):
        s = 0
        if "mamey_packages" in p or "mamey complete" in p.lower(): s += 100
        if "/package/" in p: s += 20
        if any(x in p for x in ("_audit","thesis_capture","paper_source_pool","older_data")): s -= 40
        return s
    def _mtime(p):
        try: return os.path.getmtime(p)
        except OSError: return 0.0
    for c in sorted(cands, key=lambda p: (_inventory_freshness_key(p), score(p), _mtime(p)), reverse=True):
        try:
            hdr = next(csv.reader(open(c)))
            if {"Products","KCB_top"}.issubset(set(hdr)): return c
        except Exception: continue
    return None

def role_group(role):
    r = (role or "").lower()
    if "glycosyl" in r or "sugar" in r and "pathway" not in r: return ("glycosyltransferase","#5b8def")
    if "pepm" in r or "ppd" in r or "sugar pathway" in r: return ("sugar pathway","#e08a3c")
    if any(k in r for k in ("tailoring","redox","methyltransferase","aminotransferase","halogenase","plp","dehydrogenase")): return ("tailoring/redox","#6fbf73")
    if "regulat" in r: return ("regulator","#e86fa0")
    if "activation" in r or "adenylation" in r or "ntp transferase" in r: return ("activation","#a06fd0")
    if "pks module" in r or "nrps module" in r or "ripp" in r: return ("biosynthetic core","#c9a227")
    if "transport" in r: return ("transport","#4fb3b3")
    return ("other","#5aa9a0")

def parse_domains(gf):
    if not gf: return [], ""
    doms = re.findall(r"([A-Za-z0-9_\-]+)\s*\(E-value", gf)
    m = re.search(r"SMCOG\d+:\s*([^(]+?)(?:\s{2,}|\(E-value|$)", gf)
    smcog = m.group(1).strip() if m else ""
    seen=set(); out=[]
    for d in doms:
        if d not in seen: seen.add(d); out.append(d)
    return out, smcog

def gkey(g):
    m = re.match(r"ctg(\d+)_(\d+)", g); return (int(m.group(1)), int(m.group(2))) if m else (9999,0)

def fpct(x):
    try: return round(float(x),1)
    except Exception: return None

def build_strain(strain, outdir):
    inv = resolve_inventory(strain)
    if not inv: return None, f"{strain}: no inventory"
    pkgdir = os.path.dirname(inv)
    meta = {}
    for r in csv.DictReader(open(inv)):
        meta[r["BGC_ID"]] = {"node":r.get("Node_ID","") or r.get("Contig",""),"products":r.get("Products",""),
            "kcb_top":r.get("KCB_top",""),"kcb_score":r.get("KCB_score",""),"length_kb":r.get("Length_kb",""),
            "boundary":r.get("Boundary",""),"region":r.get("antiSMASH_Region","") or r.get("Region","")}
    # nr
    nr = collections.defaultdict(dict)
    for f in sorted(glob.glob(f"{ROOT}/strain_data/{strain}/blastp_nr_*/*_nr_top_hit_per_gene_*.csv")):
        for r in csv.DictReader(open(f)):
            if r.get("hit_rank","1") in ("1",""): nr[r["bgc_id"]][r["gene"]] = r
    # mibig
    mibig = collections.defaultdict(dict)
    for r in csv.DictReader(open(GMASTER)):
        if r["strain"] != strain: continue
        b,g = r["bgc_id"], r["query_gene"]; pid = fpct(r.get("pct_identity")) or 0
        cur = mibig[b].get(g)
        if cur is None or pid > cur["_pid"]:
            r["_pid"] = pid; mibig[b][g] = r
    # locus maps
    def locus(bgc):
        fs = glob.glob(f"{pkgdir}/locus_maps/{bgc}_*_locus_data.csv")
        return {r["locus_tag"]: r for r in csv.DictReader(open(fs[0]))} if fs else {}
    bgcs = sorted(set(nr)|set(mibig)|set(meta), key=lambda b:int(re.sub(r"\D","",b) or 0))
    cohort = {"strain":strain,"generated":"2026-08-03","channels_present":["nr","mibig"],
              "channels_absent":{"swissprot":"not run","clusterblast_general":"not extracted"},"bgcs":[]}
    for b in bgcs:
        m = meta.get(b,{}); ld = locus(b)
        genes = sorted(set(ld)|set(nr.get(b,{}))|set(mibig.get(b,{})), key=gkey)
        if not genes: continue
        bo = {"bgc_id":b,"node":m.get("node",""),"region":m.get("region",""),"products":m.get("products",""),
              "boundary":m.get("boundary",""),"length_kb":m.get("length_kb",""),"kcb_top":m.get("kcb_top",""),
              "kcb_score":m.get("kcb_score",""),"genes":[]}
        for g in genes:
            L = ld.get(g,{}); doms,smcog = parse_domains(L.get("gene_functions",""))
            grp,color = role_group(L.get("role",""))
            nrow = nr.get(b,{}).get(g); mrow = mibig.get(b,{}).get(g)
            bo["genes"].append({"locus_tag":g,
                "order":int(L["order"]) if L.get("order","").isdigit() else None,
                "start":int(L["start"]) if L.get("start","").isdigit() else None,
                "end":int(L["end"]) if L.get("end","").isdigit() else None,
                "strand":L.get("strand",""),
                "aa":int(L["length_aa"]) if L.get("length_aa","").isdigit() else (nrow.get("aa_length") if nrow else None),
                "role":L.get("role",""),"role_group":grp,"role_color":color,"domains":doms,"smcog":smcog,
                "channels":{
                    "nr":({"pid":fpct(nrow.get("pct_identity")),"def":html.unescape(nrow.get("subject_def","")),
                           "organism":nrow.get("subject_organism",""),"acc":nrow.get("subject_acc","")} if nrow else None),
                    "swissprot":None,
                    "mibig":({"pid":fpct(mrow.get("pct_identity")),"compound":mrow.get("bgc_compound",""),
                              "coverage":fpct(mrow.get("pct_coverage")),"subject_gene":mrow.get("subject_gene",""),
                              "organism":mrow.get("reference_organism",""),"rank":mrow.get("reference_rank","")} if mrow else None),
                    "clusterblast":None}})
        cohort["bgcs"].append(bo)
    os.makedirs(outdir, exist_ok=True)
    outp = f"{outdir}/{strain}_roster_v2.json"
    _atomic_write_json(cohort, outp, owner_dir=outdir, indent=1)
    ng = sum(len(x["genes"]) for x in cohort["bgcs"])
    nrh = sum(1 for x in cohort["bgcs"] for g in x["genes"] if g["channels"]["nr"])
    mih = sum(1 for x in cohort["bgcs"] for g in x["genes"] if g["channels"]["mibig"])
    return {"strain":strain,"bgcs":len(cohort["bgcs"]),"genes":ng,"nr":nrh,"mibig":mih,"path":outp}, None

def all_strains():
    return sorted({f.split("/")[-3] for f in glob.glob(f"{ROOT}/strain_data/*/blastp_nr_*/*_nr_top_hit_per_gene_*.csv")} - EXCLUDE,
                  key=lambda s:int(re.sub(r"\D","",s) or 0))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--strain"); ap.add_argument("--all", action="store_true")
    ap.add_argument("--outdir", default=f"{ROOT}/sapote_deliverables/roster_v2")
    a = ap.parse_args()
    targets = all_strains() if a.all else [a.strain]
    for s in targets:
        if s in EXCLUDE: emit(f"SKIP {s} (excluded)"); continue
        res,err = build_strain(s, a.outdir)
        emit(f"  {s}: {res['bgcs']} BGCs {res['genes']} genes (nr {res['nr']}, MIBiG {res['mibig']})" if res else f"  {err}")
