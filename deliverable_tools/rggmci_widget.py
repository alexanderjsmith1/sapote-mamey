#!/usr/bin/env python3
"""rggmci_widget.py — self-contained interactive RG-GMCI split-pathway widget (graduated
into the engine as a first-class deliverable tool, v9.7.349x candidate).

RG-GMCI = Reference-Guided Gene-Module Complementarity Index: the Mamey engine's
*within-strain* split-pathway linkage channel. It proposes pairs of BGCs in the same
strain that may be fragments of one biosynthetic pathway, based on shared reference
genes plus biosynthetic-logic complementarity. Every pair carries a confidence tier and
a functional_rescue_class.

Forked from tools/bgc_widget.py (CSS-variable theming, SVG map, toggle + tooltip
pattern). Renders ONE self-contained HTML per strain:
  - a NODE-LINK graph (circular layout): nodes = BGCs, edges = RG-GMCI pairs;
    edge colour/thickness by confidence (HIGH / MODERATE / LOW), hover shows
    score + functional_rescue_class + shared tokens + avg min identity;
  - confidence toggles (LOW off by default so the strong signal reads);
  - click a node to isolate its incident pairs;
  - a synchronized table of pairs.
Stdlib-only, theme-aware (light/dark), opens over file://.

Data source: each sealed package's ``*_4A_RGGMCI_ranked_pairs.csv``.

CLAIM SAFETY: RG-GMCI links are homology-guided, class-level HYPOTHESES — NOT proven
physical pathway joins. Shared reference genes + complementary biosynthetic logic raise a
"these two fragments may belong together" flag for a human/Sapote judge. Capacity is
class-level; judgment is deferred.

Usage:
  python rggmci_widget.py --strain AS-XXX            # one strain
  python rggmci_widget.py --all                      # every strain with a CSV
  python rggmci_widget.py --all --runs-root DIR --out DIR
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, glob, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _widget_paths import ROOT_DEFAULT, runs_root as _runs_root, module_dir  # noqa: E402

# Standing hold: AS-XXX is contaminated and excluded from all deliverables.
import os as _os, sys as _sys  # bundle-root path guard (see tests/test_tool_front_doors.py)
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
try:  # cohort exclusions come from the governed SSOT, never hardcoded here
    from mamey.exclusions import governed_excluded
    SKIP_STRAINS = governed_excluded()
except Exception as _exc:  # pragma: no cover - standalone use without mamey
    raise RuntimeError(
        "cohort exclusions are governed data and are not shipped in the code tier: "
        "install the mamey package, or set MAMEY_OFFICIAL_DATA to a directory "
        "containing exclusions.json"
    ) from _exc

# Confidence tiers -> compact code used in the payload/legend/CSS.
CONF_MAP = {
    "HIGH_RG_GMCI_RESCUE": "HIGH",
    "MODERATE_RG_GMCI_CANDIDATE": "MOD",
    "LOW_SHARED_REFERENCE_SIGNAL": "LOW",
}

TEMPLATE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title>
<style>
:root{--bg:#0e0f12;--panel:#16181d;--line:#262a31;--tx:#e7e9ee;--mut:#8b91a0;--acc:#5b8def;
  --hi:#4bd07a;--mod:#f2b13d;--lo:#5b6472;--node:#c7ccd6;--nodeS:#5b8def;--tipbg:#20232a;}
@media (prefers-color-scheme: light){:root{--bg:#f6f7f9;--panel:#ffffff;--line:#dfe3ea;
  --tx:#1c2028;--mut:#6a7180;--acc:#2f6bd6;--hi:#189e52;--mod:#c8850f;--lo:#a6adba;
  --node:#4a5160;--nodeS:#2f6bd6;--tipbg:#ffffff;}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:18px}h1{font-size:15px;font-weight:600;margin:0 0 2px}
.sub{color:var(--mut);font-size:12px;margin-bottom:14px}.bar{display:flex;flex-wrap:wrap;gap:14px;align-items:center;margin-bottom:12px}
label.tg{display:inline-flex;align-items:center;gap:7px;cursor:pointer;color:var(--mut);user-select:none;font-size:13px}
label.tg input{display:none}label.tg .sw{width:22px;height:3px;border-radius:2px;display:inline-block;opacity:.35}
label.tg.on{color:var(--tx)}label.tg.on .sw{opacity:1}
.chk{display:inline-flex;align-items:center;gap:6px;color:var(--mut);font-size:12px;cursor:pointer}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 15px;margin-bottom:14px;min-height:46px;font-size:13px}
.card b{font-weight:600}.card .mut{color:var(--mut)}.card .c{color:var(--tx)}
.sec{margin:16px 0 8px;display:flex;justify-content:space-between;align-items:baseline}.sec h2{font-size:13px;font-weight:600;margin:0}.sec .r{color:var(--mut);font-size:12px}
svg{width:100%;display:block}
.legend{display:flex;flex-wrap:wrap;gap:16px;margin-top:6px;color:var(--mut);font-size:12px}
.legend span{display:inline-flex;align-items:center;gap:6px}.legend i{width:20px;height:3px;border-radius:2px;display:inline-block}
table{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:4px}
th,td{text-align:left;padding:6px 9px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--mut);font-weight:600;position:sticky;top:0;background:var(--bg);cursor:pointer;white-space:nowrap}
tbody tr{cursor:pointer}tbody tr:hover{background:var(--panel)}
.pill{display:inline-block;padding:1px 8px;border-radius:10px;font-size:11px;font-weight:600;color:#0e0f12}
.pill.HIGH{background:var(--hi)}.pill.MOD{background:var(--mod)}.pill.LOW{background:var(--lo);color:var(--tx)}
.tw{max-height:420px;overflow:auto;border:1px solid var(--line);border-radius:10px}
.foot{color:var(--mut);font-size:11.5px;margin-top:18px;border-top:1px solid var(--line);padding-top:10px}
#tip{position:fixed;pointer-events:none;background:var(--tipbg);border:1px solid var(--line);border-radius:8px;padding:8px 10px;font-size:12px;max-width:340px;opacity:0;transition:opacity .08s;z-index:9;box-shadow:0 6px 20px rgba(0,0,0,.35)}
#tip b{color:var(--tx)}#tip .mut{color:var(--mut)}
</style></head><body><div class="wrap">
<h1 id="ttl"></h1><div class="sub" id="sub"></div>
<div class="bar">
  <span style="color:var(--mut);font-size:12px">Show pairs:</span>
  <label class="tg on" data-t="HIGH"><input type="checkbox" checked><span class="sw" style="background:var(--hi)"></span>HIGH rescue <b id="cHIGH"></b></label>
  <label class="tg on" data-t="MOD"><input type="checkbox" checked><span class="sw" style="background:var(--mod)"></span>MODERATE <b id="cMOD"></b></label>
  <label class="tg" data-t="LOW"><input type="checkbox"><span class="sw" style="background:var(--lo)"></span>LOW signal <b id="cLOW"></b></label>
  <span style="flex:1"></span>
  <label class="chk"><input type="checkbox" id="lblchk" checked>node labels</label>
  <button id="clr" style="background:var(--panel);color:var(--mut);border:1px solid var(--line);border-radius:8px;padding:6px 12px;font-size:12px;cursor:pointer">clear selection</button>
</div>
<div class="card" id="card"></div>
<div class="sec"><h2>RG-GMCI split-pathway linkage graph</h2><span class="r" id="giv"></span></div>
<svg id="net" viewBox="0 0 1140 720" preserveAspectRatio="xMidYMid meet"></svg>
<div class="legend">
  <span><i style="background:var(--hi)"></i>HIGH rescue</span>
  <span><i style="background:var(--mod)"></i>MODERATE candidate</span>
  <span><i style="background:var(--lo)"></i>LOW shared-reference signal</span>
  <span style="color:var(--mut)">edge width ~ RG-GMCI score · node size ~ shown linkage degree · click a node to isolate</span>
</div>
<div class="sec"><h2>Ranked pairs</h2><span class="r" id="tcount"></span></div>
<div class="tw"><table id="tbl"><thead><tr>
  <th data-k="pair">Pair</th><th data-k="conf">Conf</th><th data-k="score">Score</th>
  <th data-k="rescue">Rescue class</th><th data-k="aid">Avg min id%</th>
  <th data-k="refs" title="Count of shared reference-cluster proteins whose homology supports this pair — NOT the strain's own gene count. 'strong' = high-quality subset.">Ref support (shared reference genes)</th>
  <th data-k="tokens">Shared reference types / product</th></tr></thead><tbody id="tb"></tbody></table></div>
<div class="foot" id="foot"></div></div><div id="tip"></div>
<script>
const DATA=__PAYLOAD__;
const NS="http://www.w3.org/2000/svg",$=i=>document.getElementById(i);
const el=(t,a)=>{const e=document.createElementNS(NS,t);for(const k in(a||{}))e.setAttribute(k,a[k]);return e;};
const esc=s=>(s==null?"":String(s)).replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));/*v9.7.409 export-injection: escape attacker text before innerHTML*/
const TIERS={HIGH:{c:"var(--hi)",w:3.4,z:3},MOD:{c:"var(--mod)",w:2.0,z:2},LOW:{c:"var(--lo)",w:0.8,z:1}};
let state={on:{HIGH:1,MOD:1,LOW:0},labels:1,sel:null,sort:{k:"score",dir:-1}};
const NODES=DATA.nodes, NI={}; NODES.forEach((n,i)=>NI[n.id]=i);
function activeEdges(){return DATA.edges.filter(e=>state.on[e.t]);}
function incident(e){return state.sel==null||e.a==state.sel||e.b==state.sel;}
function fmtTok(e){const a=(e.srt||"").trim(),b=(e.spt||"").trim();
  const s=a?("ref types: "+esc(a)):"";const p=b?("prod: "+esc(b)):"";return [s,p].filter(Boolean).join("  ·  ")||"—";}
function tip(ev,html){const t=$("tip");if(!html){t.style.opacity=0;return;}
  t.innerHTML=html;t.style.left=Math.min(ev.clientX+14,window.innerWidth-350)+"px";
  t.style.top=Math.min(ev.clientY+14,window.innerHeight-120)+"px";t.style.opacity=1;}
function edgeTip(e){return `<b>${esc(e.a)} + ${esc(e.b)}</b> · <span class="pill ${e.t}">${e.t}</span> score ${e.score}
  <br><span class="mut">${esc(e.pa)} &nbsp;|&nbsp; ${esc(e.pb)}</span>
  <br>rescue: <b>${e.rescue}</b> · avg min id ${e.aid}%
  <br><span class="mut">Ref support (shared reference genes): <b>${e.refs}</b>${(e.strong&&e.strong!="0")?` · strong: <b>${e.strong}</b>`:""} — count of reference-cluster proteins whose homology supports this pair (not the strain's own gene count)</span>
  <br>${fmtTok(e)}`;}
function init(){
  $("ttl").textContent=`${DATA.strain} — RG-GMCI split-pathway linkage widget`;
  $("sub").textContent=`${DATA.nodes.length} BGCs · ${DATA.edges.length} candidate pairs · within-strain reference-guided linkage · empty tokens = engine reported none`;
  ["HIGH","MOD","LOW"].forEach(t=>$("c"+t).textContent="("+DATA.edges.filter(e=>e.t==t).length+")");
  document.querySelectorAll("label.tg").forEach(l=>l.onclick=()=>{const t=l.dataset.t;state.on[t]=state.on[t]?0:1;l.classList.toggle("on",!!state.on[t]);draw();});
  $("lblchk").onchange=e=>{state.labels=e.target.checked?1:0;drawNet();};
  $("clr").onclick=()=>{state.sel=null;draw();};
  document.querySelectorAll("th").forEach(h=>h.onclick=()=>{const k=h.dataset.k;
    state.sort=state.sort.k==k?{k,dir:-state.sort.dir}:{k,dir:(k=="pair"||k=="rescue")?1:-1};drawTable();});
  draw();
}
function draw(){drawCard();drawNet();drawTable();
  $("foot").textContent=`RG-GMCI links are homology-guided, class-level HYPOTHESES — shared reference genes + complementary biosynthetic logic flag two fragments that MAY belong to one pathway. They are NOT proven physical pathway joins; capacity is class-level, no structure/bioactivity claim, judgment deferred to Sapote. Scores/ties come straight from the engine's ranked-pairs table.`;
}
function drawCard(){const c=$("card");const ae=activeEdges();
  if(state.sel==null){const hi=DATA.edges.filter(e=>e.t=="HIGH").length,mo=DATA.edges.filter(e=>e.t=="MOD").length;
    c.innerHTML=`<b>${DATA.strain}</b> <span class="mut">·</span> showing <b>${ae.length}</b> of ${DATA.edges.length} pairs
      <span class="mut">across ${new Set(ae.flatMap(e=>[e.a,e.b])).size} linked BGCs.</span>
      <span class="mut">${hi} HIGH-rescue, ${mo} MODERATE candidate pairs in this strain. Click a node to isolate its links.</span>`;return;}
  const inc=ae.filter(incident);const n=DATA.nodes[NI[state.sel]];
  c.innerHTML=`<b>${esc(state.sel)}</b> <span class="mut">·</span> ${esc(n.prod)} <span class="mut">· ${esc(n.contig||"")}</span>
    <br><span class="c">${inc.length}</span> shown link(s) to: <span class="mut">${esc([...new Set(inc.map(e=>e.a==state.sel?e.b:e.a))].join(", ")||"none at current filter")}</span>`;
}
function nodePos(i,n,cx,cy,r){const a=-Math.PI/2+2*Math.PI*i/n;return[cx+r*Math.cos(a),cy+r*Math.sin(a),a];}
function drawNet(){const sv=$("net");sv.innerHTML="";const W=1140,H=720,cx=W/2,cy=H/2;
  const N=DATA.nodes.length,r=Math.min(cx,cy)-92;
  const ae=activeEdges();const deg={};ae.forEach(e=>{if(incident(e)){deg[e.a]=(deg[e.a]||0)+1;deg[e.b]=(deg[e.b]||0)+1;}});
  const maxScore=Math.max(1,...ae.map(e=>e.score));
  ae.slice().sort((p,q)=>TIERS[p.t].z-TIERS[q.t].z).forEach(e=>{
    const [x1,y1]=nodePos(NI[e.a],N,cx,cy,r),[x2,y2]=nodePos(NI[e.b],N,cx,cy,r);
    const mx=(x1+x2)/2,my=(y1+y2)/2,qx=cx+(mx-cx)*0.45,qy=cy+(my-cy)*0.45;
    const d=`M${x1} ${y1} Q${qx} ${qy} ${x2} ${y2}`;
    const on=incident(e),w=TIERS[e.t].w*(0.55+0.45*e.score/maxScore);
    const p=el("path",{d,fill:"none",stroke:TIERS[e.t].c,"stroke-width":w.toFixed(2),
      "stroke-linecap":"round",opacity:on?(e.t=="LOW"?0.5:0.8):0.06});
    const hit=el("path",{d,fill:"none",stroke:"transparent","stroke-width":Math.max(8,w+7),style:"cursor:pointer"});
    hit.addEventListener("mousemove",ev=>tip(ev,edgeTip(e)));hit.addEventListener("mouseleave",()=>tip(null));
    sv.appendChild(p);sv.appendChild(hit);
  });
  NODES.forEach((n,i)=>{const [x,y,a]=nodePos(i,N,cx,cy,r);const dg=deg[n.id]||0;
    const sel=state.sel==n.id,dim=state.sel!=null&&!sel&&dg==0;
    const rad=4+Math.min(7,dg*0.9);
    const c=el("circle",{cx:x,cy:y,r:rad,fill:sel?"var(--nodeS)":"var(--node)",
      stroke:"var(--bg)","stroke-width":1.5,opacity:dim?0.28:1,style:"cursor:pointer"});
    c.addEventListener("mousemove",ev=>tip(ev,`<b>${esc(n.id)}</b> · ${esc(n.prod)}<br><span class="mut">${esc(n.contig||"")} · ${dg} shown link(s)</span>`));
    c.addEventListener("mouseleave",()=>tip(null));
    c.addEventListener("click",()=>{state.sel=state.sel==n.id?null:n.id;draw();});
    sv.appendChild(c);
    if(state.labels){const lr=r+13,lx=cx+lr*Math.cos(a),ly=cy+lr*Math.sin(a);
      const anchor=Math.cos(a)>0.2?"start":Math.cos(a)<-0.2?"end":"middle";
      const t=el("text",{x:lx,y:ly+3,fill:sel?"var(--tx)":"var(--mut)","font-size":10.5,"text-anchor":anchor,
        opacity:dim?0.3:1,style:"cursor:pointer","font-weight":sel?"600":"400"});
      t.textContent=n.id.replace(/^BGC0*/,"B");
      t.addEventListener("click",()=>{state.sel=state.sel==n.id?null:n.id;draw();});sv.appendChild(t);}
  });
  $("giv").textContent=`${ae.filter(incident).length} pairs drawn${state.sel?` · isolated on ${state.sel}`:""}`;
}
function sortKey(e,k){return {pair:e.a+e.b,conf:TIERS[e.t].z,score:e.score,rescue:e.rescue,aid:parseFloat(e.aid)||-1,refs:parseInt(e.refs)||0,tokens:(e.srt||e.spt||"")}[k];}
function drawTable(){const tb=$("tb");tb.innerHTML="";let rows=activeEdges().filter(incident);
  const {k,dir}=state.sort;rows.sort((p,q)=>{const a=sortKey(p,k),b=sortKey(q,k);return(a<b?-1:a>b?1:0)*dir;});
  $("tcount").textContent=`${rows.length} shown`;
  rows.forEach(e=>{const tr=document.createElement("tr");
    tr.innerHTML=`<td><b>${esc(e.a)} + ${esc(e.b)}</b><br><span style="color:var(--mut)">${esc(e.pa)} | ${esc(e.pb)}</span></td>
      <td><span class="pill ${e.t}">${e.t}</span></td><td>${e.score}</td><td>${e.rescue}</td>
      <td>${e.aid}</td><td>${e.refs}${(e.strong&&e.strong!="0")?`<br><span style="color:var(--mut)">${e.strong} strong</span>`:""}</td><td>${fmtTok(e)}</td>`;
    tr.onclick=()=>{state.sel=e.a;draw();};
    tr.addEventListener("mousemove",ev=>tip(ev,edgeTip(e)));tr.addEventListener("mouseleave",()=>tip(null));
    tb.appendChild(tr);});
}
init();
</script></body></html>"""


def load_pairs(csv_path):
    with open(csv_path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    nodes, seen = [], {}

    def add(bid, prod, contig):
        if bid not in seen:
            seen[bid] = True
            nodes.append({"id": bid, "prod": prod, "contig": contig})
    edges = []
    for r in rows:
        add(r["bgc_a"], r.get("products_a", ""), r.get("contig_a", ""))
        add(r["bgc_b"], r.get("products_b", ""), r.get("contig_b", ""))
        try:
            score = int(float(r.get("rggmci_score") or 0))
        except ValueError:
            score = 0
        edges.append({
            "a": r["bgc_a"], "b": r["bgc_b"],
            "pa": r.get("products_a", ""), "pb": r.get("products_b", ""),
            "score": score,
            "t": CONF_MAP.get(r.get("rggmci_confidence", ""), "LOW"),
            "rescue": r.get("functional_rescue_class", "") or "—",
            "aid": r.get("avg_min_identity", "") or "—",
            "refs": r.get("supporting_references", "") or "0",
            "strong": r.get("strong_supporting_references", "") or "0",
            "srt": r.get("shared_reference_type_tokens", ""),
            "spt": r.get("shared_product_tokens", ""),
        })
    nodes.sort(key=lambda n: int(re.sub(r"\D", "", n["id"]) or 0))
    return nodes, edges


def build(strain, csv_path, outdir):
    nodes, edges = load_pairs(csv_path)
    payload = {"strain": strain, "nodes": nodes, "edges": edges}
    html = (TEMPLATE
            .replace("__PAYLOAD__", json.dumps(payload, separators=(",", ":")).replace("</","<\\/").replace("<!--","<\\!--"))
            .replace("__TITLE__", f"{strain} RG-GMCI widget"))
    os.makedirs(outdir, exist_ok=True)
    outp = f"{outdir}/{strain}_rggmci_widget.html"
    with open(outp, "w") as fh:
        fh.write(html)
    return outp, len(nodes), len(edges)


def discover(runs_root=None):
    """strain -> csv_path for every strain with a ranked-pairs CSV under runs_root."""
    if runs_root is None:
        runs_root = _runs_root()
    pattern = os.path.join(runs_root, "*", "package", "*_4A_RGGMCI_ranked_pairs.csv")
    out = {}
    for f in sorted(glob.glob(pattern)):
        strain = f.split(os.sep + "runs" + os.sep)[-1].split(os.sep)[0] \
            if (os.sep + "runs" + os.sep) in f else os.path.basename(os.path.dirname(os.path.dirname(f)))
        out.setdefault(strain, f)
    return out


def render(strain=None, all_strains=False, runs_root=None, outdir=None):
    """Render one or all RG-GMCI strain widgets. Returns a result dict.

    strain      : one strain id (e.g. AS-XXX), or None.
    all_strains : render every strain with a ranked-pairs CSV.
    runs_root   : directory of sealed per-strain packages (default: documented location).
    outdir      : output directory (default: _RGGMCI_MODULE/widgets).
    """
    if outdir is None:
        outdir = os.path.join(module_dir("_RGGMCI_MODULE"), "widgets")
    found = discover(runs_root)
    if strain:
        if strain not in found:
            raise FileNotFoundError(
                f"no *_4A_RGGMCI_ranked_pairs.csv for {strain} under {runs_root or _runs_root()}")
        found = {strain: found[strain]}
    elif not all_strains:
        raise ValueError("pass strain=... or all_strains=True")
    built, skipped = [], []
    for s, csvp in found.items():
        if s in SKIP_STRAINS:
            skipped.append(s)
            continue
        outp, nn, ne = build(s, csvp, outdir)
        built.append((s, nn, ne, outp))
    return dict(built=built, skipped=skipped, outdir=outdir, n=len(built))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strain", help="one strain id, e.g. AS-XXX")
    ap.add_argument("--all", action="store_true", help="build every strain with a CSV")
    ap.add_argument("--runs-root", default=None,
                    help="Directory of sealed per-strain packages (default: documented location)")
    ap.add_argument("--out", default=None,
                    help="Output directory (default: _RGGMCI_MODULE/widgets)")
    a = ap.parse_args()
    if not a.strain and not a.all:
        ap.error("pass --strain AS-XXX or --all")
    res = render(strain=a.strain, all_strains=a.all, runs_root=a.runs_root, outdir=a.out)
    for s, nn, ne, outp in res["built"]:
        emit(f"{s}: {nn} BGCs, {ne} pairs -> {outp}")
    if res["skipped"]:
        emit(f"skipped (standing hold): {', '.join(res['skipped'])}")
    emit(f"built {res['n']} strain widget(s)")


if __name__ == "__main__":
    main()
