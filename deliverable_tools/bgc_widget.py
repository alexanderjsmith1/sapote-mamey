#!/usr/bin/env python3
"""bgc_widget.py — self-contained interactive per-BGC gene widget from roster_v2.json.

Views: BGC selector, focus dropdown, 4 channel toggles (nr/Swiss-Prot/MIBiG/ClusterBlast),
gene detail card + hover tooltip, role-coloured genomic arrow map, per-gene 4-channel
similarity scatter. Refinements: hover tooltip, core-genes-only filter, coverage-weighted
markers. Dependency-free; opens over file://. Claim-safe (homology only).

Usage:
  python bgc_widget.py --strain AS-XXX [--outdir DIR] [--per-bgc]
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, json, os, re
import os

ROOT = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd())

TEMPLATE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title>
<style>
:root{--bg:#0e0f12;--panel:#16181d;--line:#262a31;--tx:#e7e9ee;--mut:#8b91a0;--acc:#5b8def;}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:18px}h1{font-size:15px;font-weight:600;margin:0 0 2px}
.sub{color:var(--mut);font-size:12px;margin-bottom:14px}.bar{display:flex;flex-wrap:wrap;gap:14px;align-items:center;margin-bottom:12px}
select{background:#20232a;color:var(--tx);border:1px solid var(--line);border-radius:8px;padding:8px 12px;font-size:13px;min-width:150px}
label.tg{display:inline-flex;align-items:center;gap:7px;cursor:pointer;color:var(--mut);user-select:none;font-size:13px}
label.tg input{display:none}label.tg .gl{width:14px;height:14px}label.tg.on{color:var(--tx)}
.chk{display:inline-flex;align-items:center;gap:6px;color:var(--mut);font-size:12px;cursor:pointer}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:16px;min-height:58px}
.card .g1{font-size:14px}.card .g1 b{font-weight:600}.card .g2{color:var(--mut);font-size:12.5px;margin-top:5px}.card .g2 .c{color:var(--tx)}
.sec{margin:18px 0 8px;display:flex;justify-content:space-between;align-items:baseline}.sec h2{font-size:13px;font-weight:600;margin:0}.sec .r{color:var(--mut);font-size:12px}
svg{width:100%;display:block;border-radius:10px}.legend{display:flex;flex-wrap:wrap;gap:14px;margin-top:8px;color:var(--mut);font-size:12px}
.legend span{display:inline-flex;align-items:center;gap:6px}.legend i{width:12px;height:12px;border-radius:3px;display:inline-block}
.foot{color:var(--mut);font-size:11.5px;margin-top:18px;border-top:1px solid var(--line);padding-top:10px}
#tip{position:fixed;pointer-events:none;background:#20232a;border:1px solid var(--line);border-radius:8px;padding:8px 10px;font-size:12px;max-width:320px;opacity:0;transition:opacity .08s;z-index:9;box-shadow:0 6px 20px rgba(0,0,0,.4)}
#tip b{color:#fff}.na{opacity:.45}
</style></head><body><div class="wrap">
<h1 id="ttl"></h1><div class="sub" id="sub"></div>
<div class="bar">
  <label style="color:var(--mut);font-size:12px">BGC&nbsp;<select id="bgc"></select></label>
  <label style="color:var(--mut);font-size:12px">Focus&nbsp;<select id="focus"></select></label>
  <label class="chk"><input type="checkbox" id="coreonly">core genes only</label>
  <span style="flex:1"></span>
  <label class="tg on" data-ch="nr"><input type="checkbox" checked><svg class="gl" viewBox="0 0 14 14"><circle cx="7" cy="7" r="5" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>nr BLASTp</label>
  <label class="tg on" data-ch="swissprot"><input type="checkbox" checked><svg class="gl" viewBox="0 0 14 14"><rect x="2.5" y="2.5" width="9" height="9" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>Swiss-Prot</label>
  <label class="tg on" data-ch="mibig"><input type="checkbox" checked><svg class="gl" viewBox="0 0 14 14"><rect x="3.6" y="3.6" width="7" height="7" transform="rotate(45 7 7)" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>MIBiG</label>
  <label class="tg on" data-ch="clusterblast"><input type="checkbox" checked><svg class="gl" viewBox="0 0 14 14"><path d="M7 2.5 L12 11 L2 11 Z" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>ClusterBlast</label>
</div>
<div class="card" id="card"></div>
<div class="sec"><h2>Genomic position and function</h2><span class="r" id="giv"></span></div>
<svg id="map" viewBox="0 0 1140 150" preserveAspectRatio="xMidYMid meet"></svg><div class="legend" id="leg"></div>
<div class="sec"><h2>Per-gene sequence similarity</h2><span class="r">Identity (%)</span></div>
<svg id="scat" viewBox="0 0 1140 340" preserveAspectRatio="xMidYMid meet"></svg>
<div class="foot" id="foot"></div></div><div id="tip"></div>
<script>
const DATA=__PAYLOAD__;const DEFBGC=__DEFBGC__;
const CH=[["nr","nr BLASTp"],["swissprot","Swiss-Prot"],["mibig","MIBiG"],["clusterblast","ClusterBlast"]];
const NS="http://www.w3.org/2000/svg";let state={bgc:DEFBGC,focus:"all",core:0,on:{nr:1,swissprot:1,mibig:1,clusterblast:1}};
const $=i=>document.getElementById(i);const el=(t,a)=>{const e=document.createElementNS(NS,t);for(const k in(a||{}))e.setAttribute(k,a[k]);return e;};
const esc=s=>(s==null?"":String(s)).replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));/*v9.7.409 export-injection: escape attacker text before innerHTML*/
const suffix=lt=>{const m=/_(\d+)$/.exec(lt);return m?+m[1]:0;};
const chVal=(g,c)=>{const x=g.channels[c];return x&&x.pid!=null?x.pid:null;};
const isCore=g=>/module|ripp|core/i.test(g.role_group)||/module|ripp/i.test(g.role||"");
function shownGenes(){const b=DATA.bgcs[state.bgc];return state.core?b.genes.filter(isCore):b.genes;}
function marker(sv,ch,x,y,col,fill,r){r=r||5;const o={fill:fill?col:"none",stroke:col,"stroke-width":fill?0:1.5};
  if(ch=="nr")return sv.appendChild(el("circle",{cx:x,cy:y,r,...o}));
  if(ch=="swissprot")return sv.appendChild(el("rect",{x:x-r+.5,y:y-r+.5,width:2*r-1,height:2*r-1,...o}));
  if(ch=="mibig")return sv.appendChild(el("rect",{x:x-r+.8,y:y-r+.8,width:2*r-1.6,height:2*r-1.6,transform:`rotate(45 ${x} ${y})`,...o}));
  return sv.appendChild(el("path",{d:`M ${x} ${y-r-.5} L ${x+r} ${y+r-1} L ${x-r} ${y+r-1} Z`,...o}));}
function fmtKcb(k){if(!k)return"—";const p=k.split("|").map(s=>s.trim());return p.length>1&&p[1]?`${p[1]} (${p[0].split(".")[0]})`:p[0].split(".")[0];}
function init(){
  $("ttl").textContent=`${DATA.strain} — per-BGC gene content widget (v2)`;
  $("sub").textContent=`${DATA.bgcs.length} BGCs · channels present: ${(DATA.channels_present||[]).join(", ")} · empty toggles = channel not run for ${DATA.strain}`;
  const bs=$("bgc");DATA.bgcs.forEach((b,i)=>{const o=document.createElement("option");o.value=i;o.textContent=`${b.bgc_id} · ${(b.products||"").split(";")[0]}`;bs.appendChild(o);});
  bs.value=state.bgc;bs.onchange=e=>{state.bgc=+e.target.value;state.focus="all";draw();};
  $("focus").onchange=e=>{state.focus=e.target.value;draw();};
  $("coreonly").onchange=e=>{state.core=e.target.checked?1:0;state.focus="all";draw();};
  document.querySelectorAll("label.tg").forEach(l=>l.onclick=()=>{const c=l.dataset.ch;state.on[c]=state.on[c]?0:1;l.classList.toggle("on",!!state.on[c]);draw();});
  draw();
}
function tip(ev,g){const t=$("tip");if(!g){t.style.opacity=0;return;}
  const ch=CH.map(([k,l])=>{const c=g.channels[k];return c&&c.pid!=null?`${l} ${c.pid}%`:null;}).filter(Boolean).join(" · ");
  const dom=(g.domains&&g.domains.length)?g.domains.join(", "):(g.smcog||"—");
  t.innerHTML=`<b>${esc(g.locus_tag)}</b> · ${g.aa||"?"} aa · ${g.strand||"?"}<br>${esc(g.role||"")} · <span class="na">${esc(dom)}</span><br>${ch||"no channel hit"}`;
  t.style.left=Math.min(ev.clientX+14,window.innerWidth-330)+"px";t.style.top=(ev.clientY+14)+"px";t.style.opacity=1;}
function draw(){
  const b=DATA.bgcs[state.bgc],genes=shownGenes();const f=$("focus");f.innerHTML="";
  const oa=document.createElement("option");oa.value="all";oa.textContent=`All ${genes.length} genes`;f.appendChild(oa);
  genes.forEach(g=>{const o=document.createElement("option");o.value=g.locus_tag;o.textContent=g.locus_tag;f.appendChild(o);});
  f.value=state.focus;drawCard();drawMap();drawScatter();
  $("foot").textContent=`Homology, not function. Domains are antiSMASH capacity calls; channel %id are class-level leads — "capacity consistent with," never "produces." Empty channels = not tested, not biological absence. KCB: ${fmtKcb(b.kcb_top)}`;
}
function drawCard(){const b=DATA.bgcs[state.bgc];const c=$("card");let g=state.focus!="all"&&b.genes.find(x=>x.locus_tag==state.focus);
  if(!g){c.innerHTML=`<div class="g1"><b>${esc(b.bgc_id)}</b> · ${esc(b.node)} · ${esc(b.region||"")} · <b>${esc(b.products)}</b></div>
    <div class="g2">${esc(b.boundary||"")} · ${b.length_kb||"?"} kb · <span class="c">KCB:</span> ${esc(fmtKcb(b.kcb_top))} · hover a gene or pick Focus</div>`;return;}
  const parts=CH.map(([k,l])=>{const x=g.channels[k];return `${l} <span class="c">${x&&x.pid!=null?x.pid+"%":"—"}</span>`;}).join(" · ");
  const dom=(g.domains&&g.domains.length)?g.domains.join(", "):(g.smcog||"—");const nrdef=g.channels.nr?g.channels.nr.def:"";
  const mi=g.channels.mibig;const mis=mi?`<br>MIBiG: ${esc(mi.subject_gene||"")} · <span class="c">${esc(mi.compound||"—")}</span>`:"";
  c.innerHTML=`<div class="g1"><b>${esc(g.locus_tag)}</b> · ${g.aa||"?"} aa · ${esc(nrdef||g.role)}</div>
    <div class="g2">${g.strand||"?"} strand · ${parts} · <span class="c">role:</span> ${esc(g.role)} · <span class="c">domains:</span> ${esc(dom)}${mis}</div>`;}
function drawMap(){const sv=$("map");sv.innerHTML="";const W=1140,cx=70,cw=W-140;const gc=shownGenes().filter(g=>g.start!=null&&g.end!=null);
  if(!gc.length){const t=el("text",{x:W/2,y:70,fill:"#8b91a0","text-anchor":"middle","font-size":13});t.textContent="no coordinate data for this BGC";sv.appendChild(t);$("giv").textContent="";$("leg").innerHTML="";return;}
  const mn=Math.min(...gc.map(g=>g.start)),mx=Math.max(...gc.map(g=>g.end)),sx=v=>cx+(v-mn)/(mx-mn||1)*cw,mid=80;
  $("giv").textContent=`${((mx-mn)/1000).toFixed(1)} kb interval`;
  sv.appendChild(el("line",{x1:cx,y1:mid,x2:cx+cw,y2:mid,stroke:"#3a3f47"}));
  for(let k=0;k<=(mx-mn);k+=10000){const x=sx(mn+k);sv.appendChild(el("line",{x1:x,y1:mid-4,x2:x,y2:mid+4,stroke:"#3a3f47"}));const t=el("text",{x,y:mid+18,fill:"#8b91a0","font-size":11,"text-anchor":"middle"});t.textContent=`${k/1000} kb`;sv.appendChild(t);}
  const roles={};gc.forEach(g=>{const x1=sx(g.start),x2=sx(g.end),up=g.strand!="-",y=up?mid-30:mid+30,h=15,w=Math.max(6,x2-x1),ar=Math.min(8,w*0.4),col=g.role_color||"#5aa9a0";roles[g.role_group]=col;
    const yt=y-h/2,yb=y+h/2;let d=up?`M${x1} ${yt} H${x1+w-ar} L${x1+w} ${y} L${x1+w-ar} ${yb} H${x1} Z`:`M${x1+w} ${yt} H${x1+ar} L${x1} ${y} L${x1+ar} ${yb} H${x1+w} Z`;
    const p=el("path",{d,fill:col,opacity:(state.focus=="all"||state.focus==g.locus_tag)?0.92:0.28,cursor:"pointer"});
    p.addEventListener("mousemove",ev=>tip(ev,g));p.addEventListener("mouseleave",ev=>tip(ev,null));
    p.addEventListener("click",()=>{state.focus=g.locus_tag;$("focus").value=g.locus_tag;draw();});sv.appendChild(p);});
  const leg=$("leg");leg.innerHTML="";Object.entries(roles).forEach(([r,c])=>{const s=document.createElement("span");s.innerHTML=`<i style="background:${esc(c)}"></i>${esc(r)}`;leg.appendChild(s);});}
function drawScatter(){const sv=$("scat");sv.innerHTML="";const W=1140,H=340,L=54,R=20,T=16,B=42;const genes=shownGenes();
  const sf=genes.map(g=>suffix(g.locus_tag)),xmn=Math.min(...sf),xmx=Math.max(...sf);const X=v=>L+(v-xmn)/((xmx-xmn)||1)*(W-L-R),Y=p=>T+(100-p)/100*(H-T-B);
  [0,25,50,75,100].forEach(p=>{const y=Y(p);sv.appendChild(el("line",{x1:L,y1:y,x2:W-R,y2:y,stroke:"#20242b"}));const t=el("text",{x:L-8,y:y+4,fill:"#8b91a0","font-size":11,"text-anchor":"end"});t.textContent=p;sv.appendChild(t);});
  for(let s=xmn;s<=xmx;s+=Math.max(1,Math.round((xmx-xmn)/9))){const x=X(s);const t=el("text",{x,y:H-14,fill:"#8b91a0","font-size":11,"text-anchor":"middle"});t.textContent=s;sv.appendChild(t);}
  sv.appendChild(el("text",{x:L,y:H-2,fill:"#8b91a0","font-size":11})).textContent="locus suffix";
  genes.forEach(g=>{const x=X(suffix(g.locus_tag)),foc=state.focus==g.locus_tag;
    CH.forEach(([ch])=>{if(!state.on[ch])return;const v=chVal(g,ch);if(v==null)return;const cc=g.channels[ch];
      const cov=cc&&cc.coverage!=null?cc.coverage:null;const r=cov!=null?3.5+cov/100*2.5:5;const col=foc?"#5b8def":"#c7ccd6";
      const m=marker(sv,ch,x,Y(v),col,foc,r);m.style.cursor="pointer";m.setAttribute("opacity",foc?1:(state.focus=="all"?0.9:0.32));
      m.addEventListener("mousemove",ev=>tip(ev,g));m.addEventListener("mouseleave",ev=>tip(ev,null));
      m.addEventListener("click",()=>{state.focus=g.locus_tag;$("focus").value=g.locus_tag;draw();});});});
  if(state.focus!="all"){const g=genes.find(x=>x.locus_tag==state.focus);if(g){const x=X(suffix(g.locus_tag));const t=el("text",{x,y:T+2,fill:"#e7e9ee","font-size":12,"text-anchor":"middle","font-weight":600});t.textContent=g.locus_tag;sv.appendChild(t);}}}
init();
</script></body></html>"""

def default_bgc(data):
    return max(range(len(data["bgcs"])),
               key=lambda i: sum(1 for g in data["bgcs"][i]["genes"] if g["channels"]["nr"]), default=0)

def build(strain, outdir, per_bgc=False):
    rp = f"{ROOT}/sapote_deliverables/roster_v2/{strain}_roster_v2.json"
    data = json.load(open(rp))
    data["bgcs"] = [b for b in data["bgcs"] if b["genes"]]
    data["bgcs"].sort(key=lambda b: int(re.sub(r"\D","",b["bgc_id"]) or 0))
    os.makedirs(outdir, exist_ok=True)
    html = TEMPLATE.replace("__PAYLOAD__", json.dumps(data, separators=(",",":")).replace("</","<\\/").replace("<!--","<\\!--")) \
                   .replace("__DEFBGC__", str(default_bgc(data))).replace("__TITLE__", f"{strain} per-BGC widget")
    outp = f"{outdir}/{strain}_BGC_widget.html"
    open(outp,"w").write(html)
    made=[outp]
    if per_bgc:
        pd = f"{outdir}/{strain}_per_bgc"; os.makedirs(pd, exist_ok=True)
        for i,b in enumerate(data["bgcs"]):
            one = dict(data); one = {**data, "bgcs":[b]}
            h = TEMPLATE.replace("__PAYLOAD__", json.dumps(one, separators=(",",":")).replace("</","<\\/").replace("<!--","<\\!--")) \
                        .replace("__DEFBGC__","0").replace("__TITLE__", f"{strain} {b['bgc_id']}")
            p=f"{pd}/{strain}_{b['bgc_id']}_widget.html"; open(p,"w").write(h); made.append(p)
    return made, len(data["bgcs"]), sum(len(b["genes"]) for b in data["bgcs"])

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--strain", required=True)
    ap.add_argument("--outdir", default=f"{ROOT}/sapote_deliverables/widgets"); ap.add_argument("--per-bgc", action="store_true")
    a = ap.parse_args()
    made,nb,ng = build(a.strain, a.outdir, a.per_bgc)
    emit(f"{a.strain}: {nb} BGCs, {ng} genes -> {len(made)} html file(s); main={made[0]}")
