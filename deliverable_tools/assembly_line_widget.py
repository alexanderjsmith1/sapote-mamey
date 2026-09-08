#!/usr/bin/env python3
"""assembly_line_widget.py — self-contained NRPS/PKS assembly-line / domain-architecture
reader for a Sapote-Mamey strain (graduated into the engine as a first-class deliverable
tool, v9.7.349x candidate); forked from tools/bgc_widget.py.

For each BGC that carries NRPS/PKS assembly-line content it draws every biosynthetic
gene as a bar with its ORDERED aSDomains as coloured blocks (KS/AT/KR/DH/ER/ACP for
PKS; C/A/PCP/E/Cy/TE for NRPS; tailoring + docking distinct), marks antiSMASH module
boundaries, and labels A-domain / AT-domain substrate CONSENSUS predictions where
antiSMASH emitted them. A BGC selector and a domain-type legend are included.

Data sources (all from a sealed Mamey package):
  <pkg>/<STRAIN>_3_antismash_modules.csv  — aSDomain rows (protein_start/end, subtype,
        specificity) + aSModule rows (module domain membership, type, completeness,
        monomer_pairings).
  <pkg>/<STRAIN>_gene_context.jsonl       — per-BGC CDS list (aa_length, product,
        gene_kind, strand, genomic start) -> gene bars & ordering.
  <pkg>/<STRAIN>_2_inventory.csv          — per-BGC Products / Boundary (edge status).

CLAIM SAFETY: domain calls are antiSMASH Pfam/HMM hypotheses; substrate consensus is a
capacity-level PREDICTION, not monomer identity; module counts on contig-edge / truncated
regions are a LOWER BOUND; nothing here is a structure, product, novelty, or activity
claim. Judgment deferred.

Usage:
  python assembly_line_widget.py --strain AS-XXX [--out DIR] [--runs-root DIR]
  python assembly_line_widget.py --demo                          # 5 flagship strains
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, json, os, sys, glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _widget_paths import runs_root as _runs_root, module_dir  # noqa: E402

# Demo roster is cohort-specific data, not shipped in the code tier; loaded from
# OFFICIAL_DATA/demo_strains.json ({"strains": [...]}) when present, else empty.
try:
    from mamey.exclusions import official_data_json as _official_data_json
    DEMO_STRAINS = list(_official_data_json("demo_strains.json", {}).get("strains", []))
except Exception:  # pragma: no cover - standalone use without mamey
    DEMO_STRAINS = []

# --- domain vocabulary --------------------------------------------------------
DOMAIN_MAP = {
    "PKS_KS": ("KS", "pks_core"), "PKS_AT": ("AT", "pks_core"),
    "CAL_domain": ("CAL", "pks_core"),
    "PKS_KR": ("KR", "pks_red"), "PKS_DH": ("DH", "pks_red"),
    "PKS_DH2": ("DH", "pks_red"), "PKS_DHt": ("DHt", "pks_red"),
    "PKS_ER": ("ER", "pks_red"), "Polyketide_cyc": ("CYC", "pks_red"),
    "Condensation": ("C", "nrps_core"), "Heterocyclization": ("Cy", "nrps_core"),
    "AMP-binding": ("A", "nrps_core"), "AMP-binding_C": ("A-C", "nrps_core"),
    "Epimerization": ("E", "nrps_core"),
    "PCP": ("T", "carrier"), "ACP": ("T", "carrier"), "PKS_PP": ("T", "carrier"),
    "PP-binding": ("T", "carrier"), "ACPS": ("PPT", "carrier"),
    "Thioesterase": ("TE", "release"), "TD": ("TD", "release"),
    "Abhydrolase_1": ("TE?", "release"), "NAD_binding_4": ("Red", "release"),
    "PKS_Docking_Nterm": ("dockN", "docking"),
    "PKS_Docking_Cterm": ("dockC", "docking"),
    "NRPS-COM_Nterm": ("comN", "docking"),
    "NRPS-COM_Cterm": ("comC", "docking"),
    "X": ("X", "docking"),
    "MT": ("MT", "tailor"), "cMT": ("cMT", "tailor"), "nMT": ("nMT", "tailor"),
    "oMT": ("oMT", "tailor"),
    "Aminotran_1_2": ("AmT", "tailor"), "Aminotran_3": ("AmT", "tailor"),
    "Aminotran_5": ("AmT", "tailor"), "ECH": ("ECH", "tailor"),
    "FkbH": ("FkbH", "tailor"), "TauD": ("TauD", "tailor"),
    "LPG_synthase_C": ("LPG", "tailor"),
}
CATS = [
    ("pks_core", "PKS core (KS, AT)", "#4f8ef7"),
    ("pks_red", "PKS reductive (KR, DH, ER)", "#39b7c4"),
    ("nrps_core", "NRPS core (C, A, Cy, E)", "#e0913a"),
    ("carrier", "Carrier / thiolation (T = ACP/PCP)", "#c05fd6"),
    ("release", "Release / termination (TE, TD)", "#d9534f"),
    ("docking", "Docking / linker", "#7a828f"),
    ("tailor", "Embedded tailoring (MT, AmT, ...)", "#5cae7a"),
    ("other", "Other aSDomain", "#9aa0ad"),
]
CAT_COLOR = {c: col for c, _, col in CATS}


def domain_info(name: str):
    code, cat = DOMAIN_MAP.get(name, (name[:5], "other"))
    return code, cat


def parse_specificity(spec_list, domain):
    """Return (short prediction, full pieces) for an A- or AT- domain, else (None, [])."""
    if not spec_list:
        return None, []
    pred = None
    pieces = []
    for s in spec_list:
        pieces.append(s)
        if s.lower().startswith("substrate consensus:"):
            pred = s.split(":", 1)[1].strip()
    return pred, pieces


# --- loaders ------------------------------------------------------------------
def load_gene_context(path):
    out = {}
    for ln in open(path):
        ln = ln.strip()
        if not ln:
            continue
        d = json.loads(ln)
        if "cds" not in d:
            continue
        out[d["bgc_id"]] = d["cds"]
    return out


def load_inventory(path):
    inv = {}
    if not os.path.exists(path):
        return inv
    for r in csv.DictReader(open(path)):
        inv[r["BGC_ID"]] = {"products": r.get("Products", ""),
                            "boundary": r.get("Boundary", ""),
                            "arch": r.get("Arch", "")}
    return inv


def load_domains_modules(path):
    dom = {}
    mods = {}
    dom_index = {}
    for r in csv.DictReader(open(path)):
        bgc = r["bgc_id"]
        if r["feature_type"] == "aSDomain" and r["database"] == "nrpspksdomains.hmm":
            try:
                dj = json.loads(r["detail_json"])
            except Exception:
                continue
            name = r["domain"]
            code, cat = domain_info(name)
            ps = int(dj.get("protein_start", ["0"])[0])
            pe = int(dj.get("protein_end", ["0"])[0])
            subs = dj.get("domain_subtypes", []) or []
            pred, pieces = parse_specificity(dj.get("specificity", []), name)
            did = dj.get("domain_id", [""])[0]
            locus = r["locus_tag"]
            rec = {"name": name, "code": code, "cat": cat, "ps": ps, "pe": pe,
                   "subtype": (subs[0] if subs else ""), "pred": pred,
                   "spec": pieces, "did": did,
                   "score": r.get("bitscore", ""), "evalue": r.get("evalue", "")}
            dom.setdefault(bgc, {}).setdefault(locus, []).append(rec)
            dom_index.setdefault(bgc, {})[did] = rec
        elif r["feature_type"] == "aSModule":
            try:
                dj = json.loads(r["detail_json"])
            except Exception:
                continue
            dids = dj.get("domains", []) or []
            loci = dj.get("locus_tags", []) or []
            mtype = (dj.get("type", [""]) or [""])[0]
            complete = bool((dj.get("complete", [""]) or [""])[0].strip())
            starter = bool((dj.get("starter_module", [""]) or [""])[0].strip())
            monomer = (dj.get("monomer_pairings", [""]) or [""])[0]
            mods.setdefault(bgc, []).append({
                "type": mtype, "complete": complete, "starter": starter,
                "monomer": monomer, "domain_ids": dids,
                "loci": loci})
    return dom, mods, dom_index


# --- build payload ------------------------------------------------------------
def build_payload(strain, pkg):
    gc = load_gene_context(os.path.join(pkg, f"{strain}_gene_context.jsonl"))
    inv = load_inventory(os.path.join(pkg, f"{strain}_2_inventory.csv"))
    dom, mods, dom_index = load_domains_modules(
        os.path.join(pkg, f"{strain}_3_antismash_modules.csv"))

    bgcs = []
    for bgc in sorted(dom.keys(), key=lambda b: -sum(len(v) for v in dom[b].values())):
        gene_doms = dom[bgc]
        cds_list = gc.get(bgc, [])
        cds_by_locus = {c["locus_tag"]: c for c in cds_list}
        mod_of_did = {}
        bmods = mods.get(bgc, [])
        for mi, m in enumerate(bmods):
            for did in m["domain_ids"]:
                mod_of_did[did] = mi

        genes = []
        for locus, dlist in gene_doms.items():
            dlist = sorted(dlist, key=lambda d: d["ps"])
            cds = cds_by_locus.get(locus, {})
            aa = cds.get("aa_length") or (max((d["pe"] for d in dlist), default=100) + 20)
            prod = cds.get("product", "") or ""
            kind = cds.get("gene_kind", "") or ""
            strand = cds.get("strand", 1)
            gstart = cds.get("start", 0)
            outd = []
            for d in dlist:
                outd.append({
                    "code": d["code"], "name": d["name"], "cat": d["cat"],
                    "ps": d["ps"], "pe": d["pe"], "subtype": d["subtype"],
                    "pred": d["pred"], "spec": d["spec"],
                    "score": d["score"], "evalue": d["evalue"],
                    "mod": mod_of_did.get(d["did"], -1),
                })
            genes.append({"locus": locus, "aa": aa, "product": prod,
                          "kind": kind, "strand": strand, "gstart": gstart,
                          "domains": outd})
        genes.sort(key=lambda g: g["gstart"])
        disp_mods = [{"type": m["type"], "complete": m["complete"],
                      "starter": m["starter"], "monomer": m["monomer"]}
                     for m in bmods]
        meta = inv.get(bgc, {})
        n_core = sum(1 for g in genes for d in g["domains"]
                     if d["cat"] in ("pks_core", "nrps_core"))
        bgcs.append({
            "bgc_id": bgc,
            "products": meta.get("products", ""),
            "boundary": meta.get("boundary", ""),
            "n_domains": sum(len(g["domains"]) for g in genes),
            "n_modules": len(bmods),
            "n_complete": sum(1 for m in bmods if m["complete"]),
            "genes": genes, "modules": disp_mods,
        })
    return {"strain": strain, "bgcs": bgcs}


# --- HTML template ------------------------------------------------------------
TEMPLATE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title>
<style>
:root{--bg:#0e0f12;--panel:#16181d;--line:#262a31;--tx:#e7e9ee;--mut:#8b91a0;--acc:#5b8def;
--pks_core:#4f8ef7;--pks_red:#39b7c4;--nrps_core:#e0913a;--carrier:#c05fd6;
--release:#d9534f;--docking:#7a828f;--tailor:#5cae7a;--other:#9aa0ad;}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1240px;margin:0 auto;padding:18px}
h1{font-size:16px;font-weight:600;margin:0 0 2px}.sub{color:var(--mut);font-size:12px;margin-bottom:14px}
.bar{display:flex;flex-wrap:wrap;gap:14px;align-items:center;margin-bottom:12px}
select{background:#20232a;color:var(--tx);border:1px solid var(--line);border-radius:8px;padding:8px 12px;font-size:13px;min-width:220px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:13px 16px;margin-bottom:14px}
.card .g1{font-size:13.5px}.card .g1 b{font-weight:600;color:#fff}
.card .g2{color:var(--mut);font-size:12.5px;margin-top:5px}.card .g2 .c{color:var(--tx)}
.pill{display:inline-block;background:#20232a;border:1px solid var(--line);border-radius:20px;padding:2px 10px;font-size:11.5px;margin-right:6px;color:var(--mut)}
.sec{margin:16px 0 8px;display:flex;justify-content:space-between;align-items:baseline}
.sec h2{font-size:13px;font-weight:600;margin:0}.sec .r{color:var(--mut);font-size:12px}
svg{width:100%;display:block;border-radius:10px;background:#111318}
.legend{display:flex;flex-wrap:wrap;gap:14px;margin-top:10px;color:var(--mut);font-size:12px}
.legend span{display:inline-flex;align-items:center;gap:6px}.legend i{width:13px;height:13px;border-radius:3px;display:inline-block}
.foot{color:var(--mut);font-size:11.5px;margin-top:18px;border-top:1px solid var(--line);padding-top:10px}
#tip{position:fixed;pointer-events:none;background:#20232a;border:1px solid var(--line);border-radius:8px;padding:8px 10px;font-size:12px;max-width:340px;opacity:0;transition:opacity .08s;z-index:9;box-shadow:0 6px 20px rgba(0,0,0,.45)}
#tip b{color:#fff}
</style></head><body><div class="wrap">
<h1 id="ttl"></h1><div class="sub" id="sub"></div>
<div class="bar">
  <label style="color:var(--mut);font-size:12px">BGC&nbsp;<select id="bgc"></select></label>
  <span style="flex:1"></span>
  <label style="color:var(--mut);font-size:12px"><input type="checkbox" id="labels" checked> domain labels</label>
</div>
<div class="card" id="card"></div>
<div class="sec"><h2>Assembly line — genes (genomic order) with ordered aSDomains</h2><span class="r" id="giv"></span></div>
<svg id="line" preserveAspectRatio="xMinYMin meet"></svg>
<div class="legend" id="leg"></div>
<div class="foot" id="foot"></div></div><div id="tip"></div>
<script>
const DATA=__PAYLOAD__;
const CATS=__CATS__;
const CATLABEL={};CATS.forEach(c=>CATLABEL[c[0]]=c[1]);
const NS="http://www.w3.org/2000/svg";
let state={bgc:0,labels:1};
const $=i=>document.getElementById(i);
const el=(t,a)=>{const e=document.createElementNS(NS,t);for(const k in(a||{}))e.setAttribute(k,a[k]);return e;};
const esc=s=>(s==null?"":String(s)).replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
const cvar=cat=>`var(--${cat})`;

function init(){
  $("ttl").textContent=`${DATA.strain} — NRPS/PKS assembly-line & domain-architecture reader`;
  $("sub").textContent=`${DATA.bgcs.length} BGC(s) with assembly-line (NRPS/PKS) domain content · antiSMASH nrps_pks_domains calls · domain calls are HMM hypotheses, substrate = capacity-level prediction, judgment deferred`;
  const bs=$("bgc");
  DATA.bgcs.forEach((b,i)=>{const o=document.createElement("option");o.value=i;
    o.textContent=`${b.bgc_id} · ${(b.products||"").split(";")[0]} · ${b.n_domains} dom / ${b.n_modules} mod`;bs.appendChild(o);});
  bs.value=state.bgc;bs.onchange=e=>{state.bgc=+e.target.value;draw();};
  $("labels").onchange=e=>{state.labels=e.target.checked?1:0;draw();};
  const lg=$("leg");CATS.forEach(c=>{const s=document.createElement("span");
    s.innerHTML=`<i style="background:${cvar(c[0])}"></i>${esc(c[1])}`;lg.appendChild(s);});
  const extra=document.createElement("span");
  extra.innerHTML=`<i style="background:#20232a;border:1px dashed #6a7180"></i>module bracket (dashed = incomplete)`;
  lg.appendChild(extra);
  draw();
}

function draw(){
  const b=DATA.bgcs[state.bgc];
  const edge=/edge|truncat|full-contig/i.test(b.boundary);
  $("card").innerHTML=
    `<div class="g1"><b>${esc(b.bgc_id)}</b> — ${esc(b.products||"(class n/a)")}</div>`+
    `<div class="g2">`+
    `<span class="pill">${b.genes.length} biosynthetic gene(s) with domains</span>`+
    `<span class="pill">${b.n_domains} aSDomains</span>`+
    `<span class="pill">${b.n_modules} module(s) · ${b.n_complete} complete</span>`+
    `<span class="pill">boundary: ${esc(b.boundary||"?")}</span>`+
    `</div>`+
    (edge?`<div class="g2" style="color:#d9a441">Region is contig-edge / full-contig: module &amp; domain counts are a LOWER BOUND (assembly line may be truncated).</div>`:``);
  $("giv").textContent=`${b.genes.length} gene lane(s)`;
  drawLine(b);
}

function drawLine(b){
  const sv=$("line");while(sv.firstChild)sv.removeChild(sv.firstChild);
  const LW=1240, LEFT=196, RIGHT=24, laneH=54, gap=26, top=14;
  const barH=20, domH=26;
  const trackW=LW-LEFT-RIGHT;
  const H=top+b.genes.length*(laneH+gap)+30;
  sv.setAttribute("viewBox",`0 0 ${LW} ${H}`);
  sv.style.height=(H*Math.min(1,LW/ (sv.clientWidth||LW)))+"px";
  sv.setAttribute("height",H);

  b.genes.forEach((g,gi)=>{
    const y=top+gi*(laneH+gap);
    const midY=y+laneH/2;
    const lab=el("text",{x:8,y:midY-3,fill:"var(--tx)","font-size":12,"font-weight":600});
    lab.textContent=g.locus+(g.strand<0?" ◀":" ▶");sv.appendChild(lab);
    const aaTxt=el("text",{x:8,y:midY+12,fill:"var(--mut)","font-size":10.5});
    aaTxt.textContent=`${g.aa} aa · ${(g.kind||"").slice(0,40)}`;sv.appendChild(aaTxt);

    const aa=Math.max(g.aa,1);
    const x2aa=v=>LEFT+ (v/aa)*trackW;
    sv.appendChild(el("rect",{x:LEFT,y:midY-barH/2,width:trackW,height:barH,rx:4,
      fill:"#1b1e25",stroke:"var(--line)","stroke-width":1}));

    const modSpans={};
    g.domains.forEach(d=>{if(d.mod>=0){(modSpans[d.mod]=modSpans[d.mod]||[]).push(d);}});
    Object.keys(modSpans).forEach(mi=>{
      const ds=modSpans[mi];const x0=x2aa(Math.min(...ds.map(d=>d.ps)));
      const x1=x2aa(Math.max(...ds.map(d=>d.pe)));
      const m=b.modules[mi]||{};
      const by=midY+barH/2+7;
      sv.appendChild(el("path",{d:`M ${x0} ${by} L ${x0} ${by+6} L ${x1} ${by+6} L ${x1} ${by}`,
        fill:"none",stroke:m.complete?"#6a7180":"#6a7180","stroke-width":1.3,
        "stroke-dasharray":m.complete?"":"3 2"}));
      const mt=el("text",{x:(x0+x1)/2,y:by+17,fill:"var(--mut)","font-size":9.5,"text-anchor":"middle"});
      mt.textContent=(m.type||"").toUpperCase()+(m.starter?" start":"")+(m.complete?"":" (part)");
      sv.appendChild(mt);
    });

    g.domains.forEach(d=>{
      const x0=x2aa(d.ps), x1=x2aa(d.pe);const w=Math.max(x1-x0,7);
      const r=el("rect",{x:x0,y:midY-domH/2,width:w,height:domH,rx:3,
        fill:cvar(d.cat),stroke:"#0e0f12","stroke-width":1,style:"cursor:pointer"});
      r.addEventListener("mousemove",ev=>tip(ev,d,g));
      r.addEventListener("mouseleave",()=>tip(null));
      sv.appendChild(r);
      if(state.labels && w>=14){
        const t=el("text",{x:(x0+x1)/2,y:midY+3.5,fill:"#0d0f13","font-size":10.5,
          "font-weight":700,"text-anchor":"middle","pointer-events":"none"});
        t.textContent=d.code;sv.appendChild(t);
      }
      if(d.pred){
        const pt=el("text",{x:(x0+x1)/2,y:midY-domH/2-4,fill:"#e8c07a","font-size":9.5,
          "text-anchor":"middle"});
        pt.textContent="~"+d.pred;sv.appendChild(pt);
      }
    });
  });
}

function tip(ev,d,g){
  const t=$("tip");
  if(!d){t.style.opacity=0;return;}
  const specHtml=(d.spec&&d.spec.length)?("<br>"+d.spec.map(esc).join("<br>")):"";
  t.innerHTML=`<b>${esc(d.name)}</b> <span style="color:${cvar(d.cat)}">${esc(d.code)}</span>`+
    `<br><span style="color:#8b91a0">${esc(CATLABEL[d.cat]||d.cat)}</span>`+
    (d.subtype?`<br>subtype: ${esc(d.subtype)}`:``)+
    `<br>${esc(g.locus)} · aa ${d.ps}–${d.pe}`+
    (d.pred?`<br><span style="color:#e8c07a">substrate consensus (prediction): ${esc(d.pred)}</span>`:``)+
    specHtml+
    `<br><span style="color:#8b91a0">HMM bitscore ${esc(d.score)} · E ${esc(d.evalue)}</span>`;
  t.style.opacity=1;
  const pad=14;let x=ev.clientX+pad,yy=ev.clientY+pad;
  if(x+340>window.innerWidth)x=ev.clientX-340-pad;
  t.style.left=x+"px";t.style.top=yy+"px";
}

$("foot").innerHTML=
  "CLAIM SAFETY — Domain identities are antiSMASH Pfam/HMM hypotheses (nrps_pks_domains); "+
  "they do not prove product identity, expression, or activity. Substrate 'consensus' values "+
  "are capacity-level PREDICTIONS of adenylation/acyltransferase preference, not confirmed monomer "+
  "identity or a structure claim. Module counts on contig-edge / truncated regions are a LOWER BOUND. "+
  "Genes are drawn in genomic order; each gene bar is normalised to its own aa length (bars are not "+
  "cross-comparable in absolute size). Judgment deferred — Mamey extracts, Sapote judges.";
init();
</script></body></html>"""


def render_html(payload):
    html = TEMPLATE
    html = html.replace("__TITLE__", f"{payload['strain']} assembly-line reader")
    html = html.replace("__PAYLOAD__", json.dumps(payload, separators=(",", ":")).replace("</","<\\/").replace("<!--","<\\!--"))
    html = html.replace("__CATS__", json.dumps([[c, l, col] for c, l, col in CATS]))
    return html


def find_pkg(runs_root, strain):
    p = os.path.join(runs_root, strain, "package")
    if os.path.exists(os.path.join(p, f"{strain}_3_antismash_modules.csv")):
        return p
    hits = glob.glob(os.path.join(runs_root, "**", f"{strain}_3_antismash_modules.csv"),
                     recursive=True)
    return os.path.dirname(hits[0]) if hits else None


def run_strain(strain, runs_root, outdir):
    pkg = find_pkg(runs_root, strain)
    if not pkg:
        emit(f"  [SKIP] {strain}: no antismash_modules.csv found under {runs_root}")
        return None
    payload = build_payload(strain, pkg)
    if not payload["bgcs"]:
        emit(f"  [SKIP] {strain}: no NRPS/PKS assembly-line domains present")
        return None
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, f"{strain}_assembly_line.html")
    with open(out, "w") as fh:
        fh.write(render_html(payload))
    top = payload["bgcs"][0]
    emit(f"  [OK]   {strain}: {len(payload['bgcs'])} BGC(s); default {top['bgc_id']} "
          f"({top['n_domains']} domains, {top['n_modules']} modules) -> {out}")
    return out


def discover(runs_root=None):
    """strain -> package dir for every strain with an antismash_modules.csv under runs_root.

    v9.7.413 (BC2): the sibling `rggmci_widget` has had `--all` since it shipped; this tool had
    only --strain/--demo, which is why the reader covered 5 flagship strains out of the 44 that
    have the table. Same glob shape as the sibling so both agree on what "every strain" means.
    """
    if runs_root is None:
        runs_root = _runs_root()
    out = {}
    for f in sorted(glob.glob(os.path.join(runs_root, "*", "package",
                                           "*_3_antismash_modules.csv"))):
        pkg = os.path.dirname(f)
        strain = os.path.basename(os.path.dirname(pkg))
        out[strain] = pkg
    return out


def render(strains=None, demo=False, runs_root=None, outdir=None, all_strains=False):
    """Render assembly-line reader HTML for one or more strains. Returns a result dict."""
    if runs_root is None:
        runs_root = _runs_root()
    if outdir is None:
        outdir = os.path.join(module_dir("_ASSEMBLY_LINE_MODULE"), "widgets")
    if demo:
        strains = DEMO_STRAINS
    elif all_strains:
        strains = sorted(discover(runs_root))
    strains = strains or []
    if not strains:
        raise ValueError("give strains=[...] or demo=True")
    built = []
    for s in strains:
        out = run_strain(s, runs_root, outdir)
        if out:
            built.append((s, out))
    return dict(built=built, n=len(built), outdir=outdir, requested=len(strains))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strain")
    ap.add_argument("--demo", action="store_true", help=f"render {DEMO_STRAINS}")
    ap.add_argument("--all", action="store_true", dest="all_strains",
                    help="every strain with an antismash_modules.csv under --runs-root")
    ap.add_argument("--runs-root", default=None,
                    help="Directory of sealed per-strain packages (default: documented location)")
    ap.add_argument("--out", default=None,
                    help="Output directory (default: _ASSEMBLY_LINE_MODULE/widgets)")
    a = ap.parse_args()
    strains = DEMO_STRAINS if a.demo else ([a.strain] if a.strain else [])
    if not strains and not a.all_strains:
        ap.error("give --strain AS-XXX, --demo, or --all")
    res = render(strains=(None if (a.demo or a.all_strains) else strains), demo=a.demo,
                 runs_root=a.runs_root, outdir=a.out, all_strains=a.all_strains)
    emit(f"assembly_line_widget -> {res['outdir']}: {res['n']}/{res['requested']} built")


if __name__ == "__main__":
    main()
