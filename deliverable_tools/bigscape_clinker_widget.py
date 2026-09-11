#!/usr/bin/env python3
"""bigscape_clinker_widget.py — self-contained, theme-aware, clinker-style within-GCF
gene-alignment widget for the Sapote-Mamey BiG-SCAPE cohort deliverable (graduated into the
engine, v9.7.349x).

For one gene-cluster family (GCF), each member BGC is drawn as a horizontal gene-arrow track
stacked vertically. Homologous genes (shared dominant Pfam = "orthogroup") are colour-linked
across tracks with ribbons, revealing synteny / conservation across strains in the family.

Data source: full_cohort.db (BiG-SCAPE 2.x SQLite; run full_cohort_AS_Type_SID_2026-07-18).
Genes, coordinates, strand, gene_kind, and Pfam HSP hits all come from that DB. Stdlib-only;
no network, no external assets — SVG is drawn inline; opens over file://.

Claim-safety: orthogroup links = shared Pfam / sequence-similarity clustering, class-level only;
"AS-private" = no Type/SID reference member in the family (a novelty prior, not proof);
Type/SID members are similarity anchors, not identity. Judgment deferred.

Usage:
  python bigscape_clinker_widget.py                     # render the curated flagship families
  python bigscape_clinker_widget.py --family 1961 2001  # render specific family ids
  python bigscape_clinker_widget.py --db /path/to/full_cohort.db --outdir DIR
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, json, os, sys, collections
from html import escape as _hesc  # v9.7.409 export-injection: escape attacker text in server-rendered index HTML

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _bigscape_data import (DB_DEFAULT, family_members, genes_for_gbk,  # noqa: E402
                            sm_annotation_index)
import sqlite3  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
# Curated flagship families at cutoff 0.3 (see README): rich, cross-strain, novelty-relevant.
CURATED = [1961, 2001, 2991, 2487]

PALETTE = ["#5b8def", "#e0724d", "#43a08a", "#c65fb0", "#d1a53a", "#6c7bd8", "#4aa3c7",
           "#d05c72", "#7fae3e", "#b078d6", "#2fa46b", "#c78a3d", "#5d9fd6", "#d15f9a",
           "#8a9a4d", "#9a6fd0", "#4bb0a0", "#cf6d5a", "#6f8fdd", "#c05fa0"]

TEMPLATE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title>
<style>
:root{--bg:#0e0f12;--panel:#16181d;--line:#262a31;--tx:#e7e9ee;--mut:#8b91a0;--acc:#5b8def;--track:#20242b;--axis:#3a3f47;--grey:#5b6270;--samelen:#d69a3c}
:root[data-theme=light]{--bg:#f6f7f9;--panel:#ffffff;--line:#e2e5ea;--tx:#1b1e24;--mut:#5c6470;--acc:#2f6fe0;--track:#eef1f5;--axis:#c7ccd4;--grey:#aab0ba}
@media(prefers-color-scheme:light){:root:not([data-theme=dark]){--bg:#f6f7f9;--panel:#ffffff;--line:#e2e5ea;--tx:#1b1e24;--mut:#5c6470;--acc:#2f6fe0;--track:#eef1f5;--axis:#c7ccd4;--grey:#aab0ba}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1240px;margin:0 auto;padding:18px}
h1{font-size:15px;font-weight:600;margin:0 0 2px}.sub{color:var(--mut);font-size:12px;margin-bottom:12px}
.bar{display:flex;flex-wrap:wrap;gap:16px;align-items:center;margin-bottom:10px}
.chk{display:inline-flex;align-items:center;gap:6px;color:var(--mut);font-size:12.5px;cursor:pointer;user-select:none}
select{background:var(--track);color:var(--tx);border:1px solid var(--line);border-radius:8px;padding:6px 10px;font-size:13px}
.btn{background:var(--track);color:var(--tx);border:1px solid var(--line);border-radius:8px;padding:6px 10px;font-size:12.5px;cursor:pointer}
svg{width:100%;display:block;border-radius:10px;background:var(--panel);border:1px solid var(--line)}
.legend{display:flex;flex-wrap:wrap;gap:12px;margin-top:10px;color:var(--mut);font-size:12px}
.legend span{display:inline-flex;align-items:center;gap:6px}.legend i{width:12px;height:12px;border-radius:3px;display:inline-block}
.foot{color:var(--mut);font-size:11.5px;margin-top:16px;border-top:1px solid var(--line);padding-top:10px}
.tag{display:inline-block;font-size:10.5px;padding:1px 6px;border-radius:999px;border:1px solid var(--line);margin-left:6px}
.tag.AS{color:#e0724d;border-color:#e0724d55}.tag.SID{color:#43a08a;border-color:#43a08a55}.tag.Type{color:#8b91a0}
.tag.priv{color:#d15f9a;border-color:#d15f9a66}
#tip{position:fixed;pointer-events:none;background:var(--track);border:1px solid var(--line);border-radius:8px;padding:8px 10px;font-size:12px;max-width:340px;opacity:0;transition:opacity .08s;z-index:9;box-shadow:0 6px 20px rgba(0,0,0,.35)}
#tip b{color:var(--tx)}#tip .m{color:var(--mut)}
.toggle{margin-left:auto;font-size:12px;color:var(--mut);cursor:pointer;border:1px solid var(--line);border-radius:8px;padding:5px 9px;background:var(--track)}
</style></head><body><div class="wrap">
<h1 id="ttl"></h1><div class="sub" id="sub"></div>
<div class="bar">
  <label class="chk">colour by
    <select id="colmode"><option value="og">orthogroup (Pfam)</option><option value="kind">gene role</option></select>
  </label>
  <label class="chk">row order
    <select id="rowsort"><option value="genes">gene count (big→small)</option><option value="sim">similarity (seriated)</option><option value="strain">group by strain type</option></select>
  </label>
  <label class="chk"><input type="checkbox" id="links" checked> homology ribbons</label>
  <label class="chk"><input type="checkbox" id="distant"> distant/paralog links</label>
  <label class="chk"><input type="checkbox" id="conserved"> conserved genes only</label>
  <label class="chk"><input type="checkbox" id="align" checked> align on shared genes</label>
  <button class="btn" id="resetalign">reset align</button>
  <span class="toggle" id="themebtn">theme</span>
</div>
<svg id="map" preserveAspectRatio="xMinYMin meet"></svg>
<div class="legend" id="leg"></div>
<div class="foot" id="foot"></div></div><div id="tip"></div>
<script>
const DATA=__PAYLOAD__;const NS="http://www.w3.org/2000/svg";
const $=i=>document.getElementById(i);
const esc=s=>(s==null?"":String(s)).replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));/*v9.7.409 export-injection: escape attacker text before innerHTML*/
const el=(t,a)=>{const e=document.createElementNS(NS,t);for(const k in(a||{}))e.setAttribute(k,a[k]);return e;};
const KIND={"biosynthetic":"#e0724d","biosynthetic-additional":"#d1a53a","transport":"#43a08a","regulatory":"#6c7bd8","resistance":"#d05c72","other":"#8b91a0","":"#5b6270"};
let state={colmode:"og",links:1,distant:0,conserved:0,align:1,rowsort:(DATA.tree?"tree":"genes"),
           anchor:null,anchorTrackId:null,nudge:{}};  // anchor: chosen shared orthogroup to line up on (null=default most-shared); anchorTrackId: reference track for auto-orient (null=top row); nudge: record_id->manual bp shift
let LAST={mn:0,mx:1,L:250,R:30,W:1200};  // last draw's x-domain, for shift-drag bp<->px conversion
let ANCHOR_TARGET=null;  // aligned-bp x that the current anchor orthogroup is snapped to (for the guide line)
const BASE=DATA.tracks.slice();  // server-seriated order (similarity chain)
function reorder(){
  const b=BASE.slice();
  if(state.rowsort=="tree"&&DATA.tree){  // phylogeny (BiG-SCAPE GCF tree) leaf order
    b.sort((a,c)=>(a.tree_rank??1e9)-(c.tree_rank??1e9)||c.genes.length-a.genes.length);}
  else if(state.rowsort=="genes"){b.sort((a,c)=>c.genes.length-a.genes.length);}  // big clusters top, fragments bottom
  else if(state.rowsort=="strain"){const rk={AS:0,SID:1,Type:2};
    b.sort((a,c)=>(rk[a.cls]??3)-(rk[c.cls]??3)||c.genes.length-a.genes.length);}
  DATA.tracks=b;  // "sim" keeps the seriated BASE order
}
// clinker-style: double-click a track to REVERSE it (mirror gene positions within its own span
// and flip every strand) so a cluster annotated on the opposite orientation lines up with its
// neighbours. Mutates the track's genes in place; ribbons + arrows redraw from the new coords.
function flipGenes(t){  // mirror gene positions within the track's own span + flip every strand (no redraw)
  if(!t||!t.genes.length) return;
  const lo=Math.min(...t.genes.map(g=>g.x0)), hi=Math.max(...t.genes.map(g=>g.x1));
  t.genes.forEach(g=>{const nx0=lo+hi-g.x1, nx1=lo+hi-g.x0; g.x0=nx0; g.x1=nx1; g.strand=-g.strand;});
  t.flipped=!t.flipped;
}
function flipTrack(i){  // MANUAL double-click flip (user override; respected until anchor change/reset)
  const t=DATA.tracks[i]; if(!t||!t.genes.length) return;
  flipGenes(t); draw();
}
// AUTO-ORIENT: flip tracks whose shared-gene core runs REVERSED relative to the reference (anchor)
// track, so all clusters read the same direction and homology ribbons run parallel (no X crossings).
// Direction is decided by the sign of the covariance between each shared orthogroup's gene-center x
// in the reference vs the track (needs >=2 shared ogs). Idempotent — safe to re-run. Homology only.
function orientRefTrack(){
  if(state.anchorTrackId!=null){const t=DATA.tracks.find(x=>x.record_id===state.anchorTrackId);if(t)return t;}
  return DATA.tracks[0];  // default: the top row after ordering
}
function applyAutoOrient(){
  if(!state.align) return;
  const R=orientRefTrack(); if(!R) return;
  const rc=sharedCentroids(R);
  DATA.tracks.forEach(t=>{
    if(t===R) return;
    const tc=sharedCentroids(t);
    const common=Object.keys(tc).filter(k=>k in rc);
    if(common.length<2) return;  // not enough shared anchors to judge direction
    const rmean=common.reduce((s,k)=>s+rc[k],0)/common.length;
    const tmean=common.reduce((s,k)=>s+tc[k],0)/common.length;
    let cov=0;common.forEach(k=>{cov+=(rc[k]-rmean)*(tc[k]-tmean);});
    if(cov<0) flipGenes(t);  // shared core runs reversed vs the reference -> flip to match
  });
}
function realign(){applyAutoOrient();draw();}  // re-orient (default/anchor reference) then redraw
function ogColor(og){if(!og)return"var(--grey)";const o=DATA.orthogroups[og];return o&&o.shared?o.color:"var(--grey)";}
function geneColor(g){return state.colmode=="kind"?(KIND[g.gene_kind]||"#5b6270"):ogColor(g.og);}
function shown(track){return state.conserved?track.genes.filter(g=>g.og&&DATA.orthogroups[g.og]&&DATA.orthogroups[g.og].shared):track.genes;}
// ---- interactive align-by-homology (client-side) -------------------------------------------
// Alignment is computed IN THE BROWSER from a chosen anchor orthogroup, so it re-runs after a
// flip, an anchor change, or a manual nudge. Default anchor = the most-shared orthogroup, which
// reproduces the server's shared-gene alignment. Homology only, class-level — judgment deferred.
function defaultAnchorOg(){let og=null,best=-1;for(const k in DATA.orthogroups){const o=DATA.orthogroups[k];if(o.shared&&o.n>best){best=o.n;og=k;}}return og;}
function currentAnchor(){return state.anchor||defaultAnchorOg();}
function anchorCenter(t,og){let s=0,n=0;t.genes.forEach(g=>{if(g.og===og){s+=(g.x0+g.x1)/2;n++;}});return n?s/n:null;}
function sharedCentroids(t){const d={};t.genes.forEach(g=>{if(g.og&&DATA.orthogroups[g.og]&&DATA.orthogroups[g.og].shared){(d[g.og]=d[g.og]||[]).push((g.x0+g.x1)/2);}});const o={};for(const k in d)o[k]=d[k].reduce((a,b)=>a+b,0)/d[k].length;return o;}
function refTrackIndex(){let ri=0,rg=-1;DATA.tracks.forEach((t,i)=>{if(t.genes.length>rg){rg=t.genes.length;ri=i;}});return ri;}
function computeOffsets(){
  const anchor=currentAnchor();
  // target = anchor og's center in the largest track that contains it (stable reference position)
  let target=null,tbest=-1;
  DATA.tracks.forEach(t=>{const c=anchorCenter(t,anchor);if(c!=null&&t.genes.length>tbest){tbest=t.genes.length;target=c;}});
  ANCHOR_TARGET=target;
  // fallback (tracks lacking the anchor og): multi-centroid alignment vs the largest track
  const refc=sharedCentroids(DATA.tracks[refTrackIndex()]);
  DATA.tracks.forEach(t=>{
    let off=0;const ac=anchorCenter(t,anchor);
    if(target!=null&&ac!=null){off=target-ac;}
    else{const tc=sharedCentroids(t);const common=Object.keys(tc).filter(k=>k in refc);
      off=common.length?common.reduce((s,k)=>s+(refc[k]-tc[k]),0)/common.length:0;}
    off+=(state.nudge[t.record_id]||0);  // manual shift-drag nudge (survives reorder; keyed by record id)
    t.alignOffset=off;
  });
}
function trackOffset(t){return state.align?(t.alignOffset||0):0;}
function setAnchor(og,trackId){if(!og||!(DATA.orthogroups[og]&&DATA.orthogroups[og].shared))return;
  state.anchor=og;if(trackId!==undefined&&trackId!==null)state.anchorTrackId=trackId;state.nudge={};realign();}
function resetAnchor(){state.anchor=null;state.anchorTrackId=null;state.nudge={};realign();}
function rowAt(ev){const sv=$("map");const vb=sv.viewBox.baseVal;const r=sv.getBoundingClientRect();
  const svY=(ev.clientY-r.top)/r.height*vb.height;const i=Math.floor((svY-50)/78);
  return (i>=0&&i<DATA.tracks.length)?i:-1;}
function domain(){let mn=1e15,mx=-1e15;DATA.tracks.forEach(t=>{const off=trackOffset(t);shown(t).forEach(g=>{mn=Math.min(mn,g.x0+off);mx=Math.max(mx,g.x1+off);});});if(mn>mx){mn=0;mx=1;}return[mn,mx];}
function tip(ev,g,t){const el2=$("tip");if(!g){el2.style.opacity=0;return;}
  const pf=(g.pfams&&g.pfams.length)?g.pfams.join(", "):"no Pfam hit";
  el2.innerHTML=`<b>${esc(t.display_locus||t.strain)}</b> · orf ${esc(g.orf)} · ${g.aa||"?"} aa · ${g.strand<0?"−":"+"} strand<br>`+
   `<span class="m">role:</span> ${esc(g.gene_kind||"—")}<br><span class="m">orthogroup (dom. Pfam):</span> ${esc(g.og||"—")}<br><span class="m">domains:</span> ${esc(pf)}`;
  el2.style.left=Math.min(ev.clientX+14,window.innerWidth-350)+"px";el2.style.top=(ev.clientY+14)+"px";el2.style.opacity=1;}
function draw(){
  const sv=$("map");sv.innerHTML="";
  computeOffsets();  // client-side homology alignment (re-runs every draw: after flip/anchor/nudge)
  const AN=currentAnchor();  // active anchor orthogroup (highlighted + guide line)
  const treeMode=(state.rowsort=="tree"&&DATA.tree);  // phylogeny-ordered clinker
  const GX0=10,GW=110;  // dendrogram gutter (x px) when tree-ordered
  const labelX=treeMode?(GX0+GW+12):14;               // labels shift right to clear the tree
  const L=treeMode?470:390,R=30,W=1500,rowH=78,top=50;const n=DATA.tracks.length;const H=top+n*rowH+30;
  sv.setAttribute("viewBox",`0 0 ${W} ${H}`);sv.style.maxHeight=(H+4)+"px";
  const[mn,mx]=domain();const sx=v=>L+(v-mn)/((mx-mn)||1)*(W-L-R);
  LAST={mn,mx,L,R,W};  // for shift-drag px->bp conversion
  // anchor guide line: faint vertical rule at the aligned-bp position the anchor og snaps to
  if(state.align&&AN&&ANCHOR_TARGET!=null){const gxp=sx(ANCHOR_TARGET);
    sv.appendChild(el("line",{x1:gxp,y1:top-4,x2:gxp,y2:H-24,stroke:"var(--samelen,#d69a3c)","stroke-width":1,"stroke-dasharray":"3 4",opacity:.55}));}
  // scale bar (top)
  const kb=10000;const x0=sx(mn),x1=sx(mn+kb);
  sv.appendChild(el("line",{x1:x0,y1:22,x2:x1,y2:22,stroke:"var(--axis)","stroke-width":2}));
  const st=el("text",{x:x0,y:16,fill:"var(--mut)","font-size":11});st.textContent="10 kb (aligned bp)";sv.appendChild(st);
  const rowY=i=>top+i*rowH+rowH/2;
  // BiG-SCAPE per-GCF-family tree dendrogram (left gutter). Rows are tree-ordered so leaf-index i
  // maps to row i; segment x in [0,1] -> gutter width, segment y (leaf-index units) -> row centers.
  // Class-level domain-distance relatedness of this ONE cluster across strains — not a species tree.
  if(treeMode){
    const gx=fx=>GX0+fx*GW, gy=fy=>rowY(fy);
    const th=el("text",{x:GX0,y:top-16,fill:"var(--mut)","font-size":10});th.textContent="BGC family tree";sv.appendChild(th);
    DATA.tree.segments.forEach(s=>{
      sv.appendChild(el("line",{x1:gx(s.x1),y1:gy(s.y1),x2:gx(s.x2),y2:gy(s.y2),
        stroke:"var(--axis)","stroke-width":1.1,"stroke-linecap":"round"}));});
    // leaf tick connecting each tip to its row
    for(let i=0;i<DATA.tree.n_leaves&&i<n;i++){
      sv.appendChild(el("line",{x1:GX0+GW,y1:gy(i),x2:labelX-6,y2:gy(i),
        stroke:"var(--line)","stroke-width":1,"stroke-dasharray":"2 3"}));}
  }
  // homology ribbons between consecutive tracks
  if(state.links){for(let i=0;i<n-1;i++){const A=DATA.tracks[i],B=DATA.tracks[i+1];const oa=trackOffset(A),ob=trackOffset(B);
    const bybOg={};shown(B).forEach(g=>{if(g.og&&DATA.orthogroups[g.og]&&DATA.orthogroups[g.og].shared){(bybOg[g.og]=bybOg[g.og]||[]).push(g);}});
    shown(A).forEach(g=>{if(!g.og)return;const o=DATA.orthogroups[g.og];if(!o||!o.shared)return;const cand=bybOg[g.og];if(!cand)return;
      const gc=(g.x0+g.x1)/2+oa;let best=cand[0],bd=1e15;cand.forEach(h=>{const d=Math.abs((h.x0+h.x1)/2+ob-gc);if(d<bd){bd=d;best=h;}});
      const ax=sx((g.x0+g.x1)/2+oa),bx=sx((best.x0+best.x1)/2+ob);const ay=rowY(i)+13,by=rowY(i+1)-13;
      // Repeated generic domains can pair distant paralogs and create distracting hairline
      // diagonals. Hide those by default while retaining a reader-controlled opt-in.
      if(!state.distant&&Math.abs(ax-bx)>140)return;
      const p=el("path",{d:`M ${ax-6} ${ay} L ${ax+6} ${ay} L ${bx+6} ${by} L ${bx-6} ${by} Z`,fill:o.color,opacity:.32,cursor:"pointer"});
      p.addEventListener("click",ev=>{ev.stopPropagation();setAnchor(g.og,A.record_id);});sv.appendChild(p);});
  }}
  // identical-sequence grey-gene links: genes with NO shared Pfam orthogroup but a BYTE-IDENTICAL
  // protein sequence (same md5) across adjacent tracks ARE the same reference-dark protein — link
  // them in amber. (Matching on sequence, not length: length alone collides and draws false links.)
  if(state.links){for(let i=0;i<n-1;i++){const A=DATA.tracks[i],B=DATA.tracks[i+1];const oa=trackOffset(A),ob=trackOffset(B);
    const dark=g=>!(g.og&&DATA.orthogroups[g.og]&&DATA.orthogroups[g.og].shared);
    const bySeq={};shown(B).forEach(g=>{if(dark(g)&&g.seq){(bySeq[g.seq]=bySeq[g.seq]||[]).push(g);}});
    shown(A).forEach(g=>{if(!dark(g)||!g.seq)return;const cand=bySeq[g.seq];if(!cand)return;
      const gc=(g.x0+g.x1)/2+oa;let best=cand[0],bd=1e15;cand.forEach(h=>{const d=Math.abs((h.x0+h.x1)/2+ob-gc);if(d<bd){bd=d;best=h;}});
      const ax=sx((g.x0+g.x1)/2+oa),bx=sx((best.x0+best.x1)/2+ob),ay=rowY(i)+13,by=rowY(i+1)-13;
      if(!state.distant&&Math.abs(ax-bx)>140)return;
      const p=el("path",{d:`M ${ax-5} ${ay} L ${ax+5} ${ay} L ${bx+5} ${by} L ${bx-5} ${by} Z`,fill:"var(--samelen,#d69a3c)",opacity:.30,stroke:"var(--samelen,#d69a3c)","stroke-width":.4});sv.appendChild(p);});
  }}
  // tracks
  DATA.tracks.forEach((t,i)=>{const y=rowY(i),off=trackOffset(t);
    // baseline
    const gs=shown(t);if(gs.length){const lo=sx(Math.min(...gs.map(g=>g.x0))+off),hi=sx(Math.max(...gs.map(g=>g.x1))+off);
      sv.appendChild(el("line",{x1:lo,y1:y,x2:hi,y2:y,stroke:"var(--track)","stroke-width":10,"stroke-linecap":"round"}));}
    // label
    const _clip=(s,m)=>s.length>m?s.slice(0,m-1)+"…":s;
    const _full=`${t.display_locus||t.strain} · ${t.cls} · ${t.product} · ${gs.length} genes`+(t.sm_annot?" · "+t.sm_annot:"");
    if(t.display_parts){
      const rows=[t.display_parts.strain,t.display_parts.full_node_or_contig,
                  `${t.display_parts.region} / ${t.display_parts.bgc_alias}`];
      rows.forEach((txt,j)=>{const lab=el("text",{x:labelX,y:y-25+j*12,fill:"var(--tx)",
        "font-size":j===0?10.5:9.5,"font-weight":j===0?700:500});lab.textContent=txt;
        {const tt=el("title");tt.textContent=_full;lab.appendChild(tt);}sv.appendChild(lab);});
    }else{
      const lab=el("text",{x:labelX,y:y-17,fill:"var(--tx)","font-size":12.5,"font-weight":600});lab.textContent=t.strain;
      {const tt=el("title");tt.textContent=_full;lab.appendChild(tt);}sv.appendChild(lab);
    }
    const sub=el("text",{x:labelX,y:y-3,fill:"var(--mut)","font-size":10});sub.textContent=_clip(`${t.cls} · ${t.product} · ${gs.length}g`,34)+(t.flipped?" ⟲":"");sv.appendChild(sub);
    if(t.sm_annot){const an=el("text",{x:labelX,y:y+22,fill:"var(--acc)","font-size":9.5,"font-weight":600});an.textContent=_clip(t.sm_annot,42);{const tt=el("title");tt.textContent=t.sm_annot;an.appendChild(tt);}sv.appendChild(an);}
    // arrows
    gs.forEach(g=>{const a=sx(g.x0+off),b=sx(g.x1+off),w=Math.max(5,b-a),ar=Math.min(9,w*0.5),h=14,col=geneColor(g);
      const up=g.strand>0;const yt=y-h/2,yb=y+h/2;
      const d=up?`M${a} ${yt} H${a+w-ar} L${a+w} ${y} L${a+w-ar} ${yb} H${a} Z`:`M${a+w} ${yt} H${a+ar} L${a} ${y} L${a+ar} ${yb} H${a+w} Z`;
      const isAnchor=(g.og&&g.og===AN);const shr=(g.og&&DATA.orthogroups[g.og]&&DATA.orthogroups[g.og].shared);
      const pa=el("path",{d,fill:col,stroke:isAnchor?"var(--samelen,#d69a3c)":"rgba(0,0,0,.25)",
        "stroke-width":isAnchor?2:.5,cursor:shr?"pointer":"default"});
      pa.addEventListener("mousemove",ev=>tip(ev,g,t));pa.addEventListener("mouseleave",()=>tip(null));
      pa.addEventListener("click",ev=>{ev.stopPropagation();if(shr)setAnchor(g.og,t.record_id);});sv.appendChild(pa);});
  });
  drawLegend();
}
function drawLegend(){const leg=$("leg");leg.innerHTML="";
  if(state.align){const AN=currentAnchor();if(AN){const s=document.createElement("span");
    s.style.flexBasis="100%";const isDef=!state.anchor;
    s.innerHTML=`<i style="background:var(--samelen,#d69a3c)"></i>Aligned + auto-oriented on <b>${AN}</b>`+
      (isDef?" (default: most-shared gene)":" (click a shared gene to change; click empty space to reset)");
    leg.appendChild(s);}}
  if(state.rowsort=="tree"&&DATA.tree){const s=document.createElement("span");
    s.style.flexBasis="100%";
    s.innerHTML=`<i style="background:var(--axis)"></i>BGC family tree (BiG-SCAPE, domain-distance) — class-level relatedness of this cluster across strains; not a species tree.`;
    leg.appendChild(s);}
  if(state.colmode=="kind"){Object.entries(KIND).forEach(([k,c])=>{if(k==="")return;const s=document.createElement("span");s.innerHTML=`<i style="background:${c}"></i>${k}`;leg.appendChild(s);});
    const s=document.createElement("span");s.innerHTML=`<i style="background:var(--grey)"></i>none`;leg.appendChild(s);return;}
  const ent=Object.entries(DATA.orthogroups).filter(([k,o])=>o.shared).sort((a,b)=>b[1].n-a[1].n).slice(0,16);
  ent.forEach(([k,o])=>{const s=document.createElement("span");s.innerHTML=`<i style="background:${o.color}"></i>${esc(k)} <span style="opacity:.6">(${o.n})</span>`;leg.appendChild(s);});
  const s=document.createElement("span");s.innerHTML=`<i style="background:var(--grey)"></i>strain-unique / no Pfam`;leg.appendChild(s);
  const s2=document.createElement("span");s2.innerHTML=`<i style="background:var(--samelen,#d69a3c)"></i>similar sequence, no Pfam (likely same protein)`;leg.appendChild(s2);}
function init(){
  $("ttl").textContent=`Sapote Clinker · GCF family ${DATA.family_id} — within-family gene alignment`;
  $("sub").innerHTML=`${DATA.tracks.length} member BGCs · ${esc(DATA.product_summary)} · cutoff c${DATA.cutoff} · `+
    `${DATA.n_shared} shared orthogroups · classes: ${esc(DATA.class_summary)}`;
  if(DATA.tree){const o=document.createElement("option");o.value="tree";
    o.textContent="phylogeny (BGC tree)";$("rowsort").insertBefore(o,$("rowsort").firstChild);
    $("rowsort").value="tree";}  // default to the phylogeny-ordered clinker when a tree is present
  $("colmode").onchange=e=>{state.colmode=e.target.value;draw();};
  $("rowsort").onchange=e=>{state.rowsort=e.target.value;reorder();draw();};
  $("map").addEventListener("dblclick",ev=>{const i=rowAt(ev);if(i>=0)flipTrack(i);});
  // click on empty SVG background -> reset alignment to the default (most-shared) anchor
  $("map").addEventListener("click",ev=>{if(ev.target===$("map"))resetAnchor();});
  // OPTIONAL: shift-drag a track left/right to manually nudge its offset (bp), keyed by record id
  let drag=null;
  $("map").addEventListener("mousedown",ev=>{if(!ev.shiftKey||!state.align)return;const i=rowAt(ev);if(i<0)return;
    ev.preventDefault();drag={rec:DATA.tracks[i].record_id,x0:ev.clientX,base:(state.nudge[DATA.tracks[i].record_id]||0)};});
  window.addEventListener("mousemove",ev=>{if(!drag)return;const sv=$("map");const vb=sv.viewBox.baseVal;
    const r=sv.getBoundingClientRect();const dxSvg=(ev.clientX-drag.x0)/r.width*vb.width;
    const dv=dxSvg*(LAST.mx-LAST.mn)/((LAST.W-LAST.L-LAST.R)||1);state.nudge[drag.rec]=drag.base+dv;draw();});
  window.addEventListener("mouseup",()=>{drag=null;});
  reorder();  // apply default row order (phylogeny when a tree is present, else gene-count desc)
  $("links").onchange=e=>{state.links=e.target.checked?1:0;draw();};
  $("distant").onchange=e=>{state.distant=e.target.checked?1:0;draw();};
  $("conserved").onchange=e=>{state.conserved=e.target.checked?1:0;draw();};
  $("align").onchange=e=>{state.align=e.target.checked?1:0;if(state.align)realign();else draw();};
  $("resetalign").onclick=()=>resetAnchor();
  $("themebtn").onclick=()=>{const r=document.documentElement;const cur=r.getAttribute("data-theme");
    const isLight=cur?cur=="light":matchMedia("(prefers-color-scheme:light)").matches;r.setAttribute("data-theme",isLight?"dark":"light");draw();};
  $("foot").textContent="Click a gene to align all clusters on that shared gene (homology anchor); double-click a track to flip it. "+
    "Alignment also AUTO-ORIENTS: tracks whose shared core runs reversed are flipped so ribbons run parallel. "+
    "'reset align' (or click empty space) returns to the default most-shared anchor; shift-drag a track to nudge it. "+
    "'row order' re-sorts (phylogeny / gene count / similarity / strain). 'distant/paralog links' restores long-span links hidden by default. "+
    "Orthogroups are shared dominant Pfam associations; see the companion caption/methods file for interpretation limits.";
  applyAutoOrient();  // orient tracks vs the top row on load so ribbons come up parallel
  draw();
}
init();
</script></body></html>"""

INDEX_TEMPLATE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title>
<style>
:root{--bg:#0e0f12;--panel:#16181d;--line:#262a31;--tx:#e7e9ee;--mut:#8b91a0;--acc:#5b8def;--priv:#d15f9a}
:root[data-theme=light]{--bg:#f6f7f9;--panel:#fff;--line:#e2e5ea;--tx:#1b1e24;--mut:#5c6470;--acc:#2f6fe0}
@media(prefers-color-scheme:light){:root:not([data-theme=dark]){--bg:#f6f7f9;--panel:#fff;--line:#e2e5ea;--tx:#1b1e24;--mut:#5c6470;--acc:#2f6fe0}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:900px;margin:0 auto;padding:24px}
h1{font-size:16px;font-weight:600;margin:0 0 4px}.sub{color:var(--mut);font-size:12.5px;margin-bottom:18px}
a.card{display:block;text-decoration:none;color:var(--tx);background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:10px}
a.card:hover{border-color:var(--acc)}
.fid{font-size:14px;font-weight:600}.meta{color:var(--mut);font-size:12px;margin-top:4px}
.tag{display:inline-block;font-size:10.5px;padding:1px 7px;border-radius:999px;border:1px solid var(--priv);color:var(--priv);margin-left:8px}
.foot{color:var(--mut);font-size:11.5px;margin-top:20px;border-top:1px solid var(--line);padding-top:12px}
</style></head><body><div class="wrap">
<h1>BiG-SCAPE clinker alignments — within-GCF gene synteny</h1>
<div class="sub">__SUB__</div>
__CARDS__
<div class="foot">Each page draws member BGCs of one gene-cluster family as gene-arrow tracks with
homology ribbons. Orthogroup links are shared dominant Pfam associations. Interpretation limits,
run-specific status, and provenance are retained in each page's companion caption/methods file.</div>
</div></body></html>"""


# Similarity cutoff for linking reference-dark (no-Pfam) proteins across tracks. 5-mer Jaccard stays
# high through scattered substitutions (a single A->V changes only the ~k k-mers spanning it), so this
# links near-identical homologs, not just byte-identical ones — while a real cutoff avoids the false
# links that matching on aa-length alone produced. Tunable.
DARK_SIM_CUTOFF = 0.55


def _kmers(s, k=5):
    return {s[i:i + k] for i in range(len(s) - k + 1)} if len(s) >= k else {s}


def cluster_dark_proteins(tracks, orthogroups, cutoff=DARK_SIM_CUTOFF):
    """Single-linkage cluster reference-dark proteins (no shared Pfam orthogroup) by 5-mer Jaccard
    similarity; write a shared cluster label into each clustered gene's `seq`. Strips `_aa` from every
    gene. Length-banded (±20%) to keep it fast and to avoid clustering across very different sizes."""
    items = []  # (gene, kmerset, length)
    for t in tracks:
        for g in t["genes"]:
            aa = g.pop("_aa", None)
            g["seq"] = None
            og = g.get("og")
            shared = og and orthogroups.get(og, {}).get("shared")
            if not shared and aa and len(aa) >= 8:
                items.append((g, _kmers(aa), len(aa)))
    n = len(items)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    order = sorted(range(n), key=lambda i: items[i][2])  # by length, for banded comparison
    for a in range(n):
        i = order[a]
        gi, ki, li = items[i]
        for b in range(a + 1, n):
            j = order[b]
            gj, kj, lj = items[j]
            if lj - li > 0.20 * lj:   # lengths sorted ascending; once out of band, stop
                break
            inter = len(ki & kj)
            if inter and inter / len(ki | kj) >= cutoff:
                parent[find(i)] = find(j)
    groups = collections.defaultdict(list)
    for i in range(n):
        groups[find(i)].append(i)
    lab = 0
    for idxs in groups.values():
        if len(idxs) >= 2:
            lab += 1
            for i in idxs:
                items[i][0]["seq"] = f"dc{lab}"


# ---------------------------------------------------------------------------------------------
# BiG-SCAPE per-GCF-family tree ("phylogeny-ordered clinker") — optional, opt-in via --gcf-trees-dir.
# BiG-SCAPE writes one Newick per GCF family under <run>/output_files/<ts>_c<cutoff>/<class>/
# GCF_trees/FAM_<N>.newick. Tips are integer bgc_record.id values; branch lengths are BiG-SCAPE
# domain-distance (class-level relatedness of ONE cluster across strains) — NOT a species tree,
# NOT a compound/activity claim. Stdlib-only recursive-descent parse; no external deps.
# ---------------------------------------------------------------------------------------------
class _TreeNode:
    __slots__ = ("name", "length", "children", "x", "y", "_dist", "_depth")

    def __init__(self):
        self.name = None      # leaf name (int record id) or internal support label
        self.length = 0.0     # branch length to parent
        self.children = []
        self.x = 0.0
        self.y = 0.0


def parse_newick(s):
    """Tiny recursive-descent Newick parser (stdlib only). Returns the root _TreeNode.
    Handles `(a:0.1,b:0.2)support:0.05;` with optional internal support labels + branch lengths.
    Leaf names are kept as strings (the caller coerces the integer record ids)."""
    s = s.strip()
    pos = 0

    def parse_node():
        nonlocal pos
        node = _TreeNode()
        if pos < len(s) and s[pos] == "(":
            pos += 1  # consume '('
            while True:
                node.children.append(parse_node())
                if pos < len(s) and s[pos] == ",":
                    pos += 1
                    continue
                if pos < len(s) and s[pos] == ")":
                    pos += 1
                    break
                break
        # name/support label: read until ':' (branch length) or a structural char
        start = pos
        while pos < len(s) and s[pos] not in ",:()[;":
            pos += 1
        label = s[start:pos].strip()
        length = 0.0
        if pos < len(s) and s[pos] == ":":  # branch length follows
            pos += 1
            lstart = pos
            while pos < len(s) and s[pos] not in ",()[;":
                pos += 1
            try:
                length = float(s[lstart:pos])
            except ValueError:
                length = 0.0
        node.name = label or None
        node.length = length
        return node

    root = parse_node()
    return root


def _leaf_ids(node, out):
    if not node.children:
        if node.name is not None:
            try:
                out.append(int(node.name))
            except (TypeError, ValueError):
                pass
        return
    for c in node.children:
        _leaf_ids(c, out)


def tree_layout(root):
    """Compute a rectangular phylogram layout for a parsed Newick root.

    Returns (order, segments, n_leaves):
      order      = list of int record ids in traversal (leaf) order — this is the ROW order.
      segments   = list of {x1,y1,x2,y2}; x in [0,1] (cumulative branch length from root,
                   normalized), y in leaf-index units (0..L-1) matching the row y-centers.
      n_leaves   = number of tips.
    Guards all-zero branch lengths by falling back to topological depth for x."""
    # cumulative distance from root (x, pre-normalization) + topological depth fallback
    order = []

    def assign_x(node, acc_dist, depth):
        node._dist = acc_dist + (node.length or 0.0)
        node._depth = depth
        if not node.children:
            if node.name is not None:
                order.append(node)
            return
        for c in node.children:
            assign_x(c, node._dist, depth + 1)

    root._dist = 0.0
    root._depth = 0
    for c in root.children:
        assign_x(c, 0.0, 1)
    if not root.children and root.name is not None:
        order.append(root)  # degenerate single-tip tree

    L = len(order)
    max_dist = max((n._dist for n in _walk(root)), default=0.0)
    max_depth = max((n._depth for n in _walk(root)), default=0)
    use_depth = max_dist <= 0  # all-zero branch lengths -> topological layout

    def norm_x(node):
        if use_depth:
            return (node._depth / max_depth) if max_depth else 0.0
        return node._dist / max_dist

    # leaf y = its index in traversal order
    for i, leaf in enumerate(order):
        leaf.y = float(i)
        leaf.x = norm_x(leaf)

    # internal node y = mean of child ys (post-order), x from its distance/depth
    def set_internal(node):
        if not node.children:
            return node.y
        ys = [set_internal(c) for c in node.children]
        node.y = sum(ys) / len(ys)
        node.x = norm_x(node)
        return node.y
    set_internal(root)
    root.x = norm_x(root)

    # rectangular elbow segments: for each internal node, a vertical bar at node.x spanning its
    # children's y, plus a horizontal bar from (node.x, child.y) to (child.x, child.y).
    segments = []

    def emit(node):
        if not node.children:
            return
        cys = [c.y for c in node.children]
        segments.append({"x1": round(node.x, 5), "y1": round(min(cys), 5),
                         "x2": round(node.x, 5), "y2": round(max(cys), 5)})
        for c in node.children:
            segments.append({"x1": round(node.x, 5), "y1": round(c.y, 5),
                             "x2": round(c.x, 5), "y2": round(c.y, 5)})
            emit(c)
    emit(root)

    return [int(n.name) for n in order], segments, L


def _walk(node):
    yield node
    for c in node.children:
        yield from _walk(c)


# module-level cache: trees_dir -> list of (leafset:frozenset[int], root:_TreeNode, path:str)
_TREE_CACHE = {}


def _load_gcf_trees(trees_dir):
    """Glob every */GCF_trees/FAM_*.newick under trees_dir, parse each, and return a list of
    (leafset, root, path). Cached per trees_dir. Returns [] if the dir is missing/empty."""
    if trees_dir in _TREE_CACHE:
        return _TREE_CACHE[trees_dir]
    import glob
    trees = []
    if trees_dir and os.path.isdir(trees_dir):
        for path in sorted(glob.glob(os.path.join(trees_dir, "*", "GCF_trees", "FAM_*.newick"))):
            try:
                with open(path) as fh:
                    txt = fh.read().strip()
                if not txt:
                    continue
                root = parse_newick(txt)
                leaves = []
                _leaf_ids(root, leaves)
                if leaves:
                    trees.append((frozenset(leaves), root, path))
            except Exception:
                continue  # a malformed tree just doesn't match; never fatal
    _TREE_CACHE[trees_dir] = trees
    return trees


def find_family_tree(trees_dir, member_ids):
    """Match a family (by its member record_id set) to the best-overlapping GCF tree.

    Robust to FAM_<N> numbering NOT equalling the family id: we compare the family's member
    record_id set to each tree's leaf set and pick the strongest overlap. Requires >=2 shared
    tips AND Jaccard(members, leaves) > 0.5. Returns (order, segments, n_leaves, path) or None."""
    members = set(int(m) for m in member_ids)
    if not members:
        return None
    best = None
    best_key = (0, 0.0)  # (shared, jaccard)
    for leafset, root, path in _load_gcf_trees(trees_dir):
        shared = len(members & leafset)
        if shared < 2:
            continue
        union = len(members | leafset)
        jac = shared / union if union else 0.0
        if jac <= 0.5:
            continue
        key = (shared, jac)
        if key > best_key:
            best_key = key
            best = (root, path)
    if best is None:
        return None
    root, path = best
    order, segments, L = tree_layout(root)
    return order, segments, L, path


def load_locus_display_map(path):
    """Load a fail-closed GBK-basename to complete exact-locus display map."""
    if not path:
        return None
    required = ("gbk_basename", "strain", "full_node_or_contig", "region", "bgc_alias")
    out = {}
    with open(path, newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        missing = [c for c in required if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"locus display map missing columns: {', '.join(missing)}")
        for line_no, row in enumerate(reader, 2):
            if any(not (row.get(c) or "").strip() for c in required):
                raise ValueError(f"locus display map row {line_no} has an empty required field")
            key = os.path.basename(row["gbk_basename"].strip())
            parts = {c: row[c].strip() for c in required[1:]}
            parts["display_locus"] = " / ".join(parts[c] for c in required[1:])
            if key in out and out[key] != parts:
                raise ValueError(f"conflicting locus display rows for {key}")
            out[key] = parts
    return out


def build_family(con, fid, cutoff, fam, annot_for=None, trees_dir=None, locus_display_map=None):
    members = fam.get(fid)
    if not members:
        return None
    tracks = []
    og_members = collections.defaultdict(set)  # og -> set(member idx)
    for mi, m in enumerate(members):
        genes = genes_for_gbk(con, m["gbk_id"])
        if not genes:
            continue
        for g in genes:
            if g["og"]:
                og_members[g["og"]].add(mi)
        prow = con.execute("select path from gbk where id=?", (m["gbk_id"],)).fetchone()
        gbk_path = prow[0] if prow else None
        tr = dict(strain=m["strain"], cls=m["cls"], product=m["product"],
                  record_id=m["record_id"], genes=genes, offset=0)
        if locus_display_map is not None:
            key = os.path.basename(gbk_path or "")
            parts = locus_display_map.get(key)
            if parts is None:
                raise ValueError(
                    f"complete exact-locus display identity missing for {key or m['gbk_id']}"
                )
            tr["display_locus"] = parts["display_locus"]
            tr["display_parts"] = {
                k: parts[k] for k in
                ("strain", "full_node_or_contig", "region", "bgc_alias")
            }
        # Sapote/Mamey verdict overlay — AS tracks only. Resolve this member's region gbk PATH
        # from the DB, then join to the enriched cohort row (tier/lead_priority/reference_dark/
        # activity). SID/Type comparators carry no verdict (annot_for returns None). Reader-side:
        # nothing is recomputed here, we reconcile with already-built tables.
        if annot_for is not None and m["cls"] == "AS":
            if gbk_path:
                sm = annot_for(gbk_path)
                if sm:
                    tr["sm_annot"] = sm
        tracks.append(tr)
    if len(tracks) < 2:
        return None
    # orthogroup colours: only those spanning >= 2 members get a colour (conserved)
    shared = [og for og, s in og_members.items() if len(s) >= 2]
    shared.sort(key=lambda og: -len(og_members[og]))
    orthogroups = {}
    for i, og in enumerate(shared):
        orthogroups[og] = dict(color=PALETTE[i % len(PALETTE)], shared=True, n=len(og_members[og]))
    for og, s in og_members.items():
        if og not in orthogroups:
            orthogroups[og] = dict(color="#5b6270", shared=False, n=len(s))
    # ---- vertical ordering (seriation) ---------------------------------------------------------
    # Ribbons are drawn only between CONSECUTIVE tracks, so raw DB order gives a jumbled read
    # (large/small/large, AS/SID interleaved). Seriate: start from the reference (most genes) and
    # greedily append the not-yet-placed track sharing the most conserved orthogroups with the last
    # one, so neighbours are maximally similar and the ribbons line up. Tie-break by gene count.
    def _shared_set(tr):
        return {g["og"] for g in tr["genes"]
                if g["og"] and orthogroups.get(g["og"], {}).get("shared")}
    ogsets = [_shared_set(t) for t in tracks]
    start = max(range(len(tracks)), key=lambda i: len(tracks[i]["genes"]))
    order, used = [start], {start}
    while len(order) < len(tracks):
        last = order[-1]
        nxt = max((i for i in range(len(tracks)) if i not in used),
                  key=lambda i: (len(ogsets[i] & ogsets[last]), len(tracks[i]["genes"])))
        order.append(nxt); used.add(nxt)
    tracks = [tracks[i] for i in order]
    # alignment offsets: reference = track with most genes; shift others so shared-og centroids line up
    ref = max(range(len(tracks)), key=lambda i: len(tracks[i]["genes"]))

    def centroids(tr):
        d = {}
        for g in tr["genes"]:
            if g["og"] and orthogroups[g["og"]]["shared"]:
                d.setdefault(g["og"], []).append((g["x0"] + g["x1"]) / 2)
        return {k: sum(v) / len(v) for k, v in d.items()}
    refc = centroids(tracks[ref])
    for i, tr in enumerate(tracks):
        if i == ref:
            continue
        tc = centroids(tr)
        common = [og for og in tc if og in refc]
        if common:
            tr["offset"] = sum(refc[og] - tc[og] for og in common) / len(common)
    # link reference-dark (no shared Pfam) proteins by sequence SIMILARITY (a cutoff, tolerant of a
    # few substitutions) rather than exact identity; sets each gene's `seq` to a shared cluster label
    # and strips the raw `_aa` from every gene so the payload stays compact.
    cluster_dark_proteins(tracks, orthogroups)
    # ---- optional BiG-SCAPE per-GCF-family tree ("phylogeny-ordered clinker") ------------------
    # If a --gcf-trees-dir was provided AND a tree robustly matches this family's member set,
    # attach a `tree` payload (traversal leaf order + rectangular dendrogram segments) and stamp
    # each track's `tree_rank` (its position in the leaf order; tracks absent from the tree sink
    # to the bottom via a large rank). Class-level domain-distance relatedness only — not a species
    # tree, not a compound/activity claim. When no tree matches, no `tree` key is emitted and the
    # widget is byte-for-byte the current one.
    tree_payload = None
    if trees_dir:
        member_ids = [t.get("record_id") for t in tracks if t.get("record_id") is not None]
        matched = find_family_tree(trees_dir, member_ids)
        if matched:
            order, segments, n_leaves, _path = matched
            rank_of = {rid: i for i, rid in enumerate(order)}
            big = len(order) + len(tracks) + 1
            for t in tracks:
                t["tree_rank"] = rank_of.get(t.get("record_id"), big)
            tree_payload = {"order": order, "segments": segments, "n_leaves": n_leaves}
    # summaries
    cls_count = collections.Counter(t["cls"] for t in tracks)
    prods = collections.Counter(t["product"] for t in tracks)
    private = set(cls_count) == {"AS"}
    payload = dict(
        family_id=fid, cutoff=cutoff, tracks=tracks, orthogroups=orthogroups,
        n_shared=len(shared),
        product_summary="; ".join(f"{p} x{n}" for p, n in prods.most_common()),
        class_summary=", ".join(f"{c} {n}" for c, n in cls_count.most_common()),
    private=private,
    )
    if tree_payload is not None:
        payload["tree"] = tree_payload
    return payload


def render_families(db=DB_DEFAULT, cutoff=0.3, families=None, outdir=HERE, trees_dir=None,
                    locus_map=None):
    """Render clinker-style within-GCF alignment pages + an index. Returns a result dict.

    families: iterable of int family ids; default = curated flagship set.
    trees_dir: optional BiG-SCAPE run `output_files/<ts>_c<cutoff>` dir. When given, each family
      is matched to its best-overlapping GCF Newick tree and rendered phylogeny-ordered with a
      left-gutter dendrogram. None (default) -> identical to the current widget.
    Self-contained: each output is a single stdlib-generated HTML file (no external assets).
    """
    con = sqlite3.connect(db)
    try:
        fam = family_members(con, cutoff)
        annot_for = sm_annotation_index()  # AS-track Sapote/Mamey verdict lookup (reader-side join)
        fids = list(families) if families else CURATED
        locus_display_map = load_locus_display_map(locus_map)
        os.makedirs(outdir, exist_ok=True)
        made = []
        for fid in fids:
            payload = build_family(
                con, fid, cutoff, fam, annot_for=annot_for, trees_dir=trees_dir,
                locus_display_map=locus_display_map,
            )
            if not payload:
                continue
            title = f"GCF {fid} alignment (c{cutoff})"
            html = (TEMPLATE.replace("__PAYLOAD__", json.dumps(payload, separators=(",", ":")).replace("</","<\\/").replace("<!--","<\\!--"))
                            .replace("__TITLE__", title))
            outp = os.path.join(outdir, f"GCF_{fid}_clinker_c{cutoff}.html")
            with open(outp, "w") as fh:
                fh.write(html)
            caption_path = os.path.join(outdir, f"GCF_{fid}_clinker_c{cutoff}_caption_methods.md")
            with open(caption_path, "w") as fh:
                fh.write(_caption_methods(payload))
            made.append(dict(path=outp, family_id=fid, tracks=len(payload["tracks"]),
                             n_shared=payload["n_shared"], private=payload["private"],
                             product_summary=payload["product_summary"],
                             class_summary=payload["class_summary"],
                             caption_path=caption_path,
                             has_tree=("tree" in payload),
                             tree_leaves=(payload.get("tree", {}) or {}).get("n_leaves", 0)))
    finally:
        con.close()
    index_path = _write_index(made, cutoff, outdir)
    return dict(index=index_path, families=made, outdir=outdir)


def _write_index(made, cutoff, outdir):
    """Write an index.html linking every rendered clinker page. Returns its path."""
    cards = []
    for m in made:
        cards.append(
            f'<a class="card" href="{os.path.basename(m["path"])}">'
            f'<div class="fid">GCF {m["family_id"]}</div>'
            f'<div class="meta">{m["tracks"]} member BGCs · {m["n_shared"]} shared orthogroups · '
            f'classes: {_hesc(str(m["class_summary"]))} · {_hesc(str(m["product_summary"]))}</div></a>')
    sub = f"{len(made)} family alignment page(s) · cutoff c{cutoff} · BiG-SCAPE 2.x cohort DB"
    html = (INDEX_TEMPLATE.replace("__TITLE__", f"BiG-SCAPE clinker index (c{cutoff})")
                          .replace("__SUB__", sub)
                          .replace("__CARDS__", "\n".join(cards) if cards
                                   else '<div class="meta">No renderable families.</div>'))
    index_path = os.path.join(outdir, "index.html")
    with open(index_path, "w") as fh:
        fh.write(html)
    return index_path


def _caption_methods(payload):
    """Return reader-facing caption/methods text kept outside the uncluttered figure."""
    fid = payload["family_id"]
    cutoff = payload["cutoff"]
    return f"""# GCF family {fid} clinker — caption and methods

## Figure caption

Interactive gene-neighborhood comparison for {len(payload['tracks'])} records assigned to GCF family {fid} at BiG-SCAPE cutoff {cutoff}. Arrows show CDS order and direction. Colored links connect proteins sharing the dominant Pfam association used by this renderer. Long-span links are hidden by default to reduce paralog-driven hairlines and can be restored with the `distant/paralog links` control. Similarity and neighborhood conservation do not establish identical function, pathway identity, compound identity, production, activity, or novelty.

## Methods

Gene coordinates, strand, antiSMASH gene role, and Pfam HSP assignments were read from the selected BiG-SCAPE SQLite database. Tracks were auto-oriented and aligned on a shared orthogroup; readers may change the anchor, flip tracks, reorder rows, and restore distant links. The family number and private/shared state are run- and cutoff-specific navigation properties. Reference members are similarity comparators, not identity assignments.

## Display policy

The interactive figure omits status slogans and private/public badges so the gene architecture remains primary. Claim ceilings and provenance remain in this sidecar. Exact-locus deployments must additionally provide the complete `strain / full node-or-contig / region / BGC alias` identity for every displayed record.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DB_DEFAULT)
    ap.add_argument("--cutoff", type=float, default=0.3)
    ap.add_argument("--family", type=int, nargs="*", default=None)
    ap.add_argument("--outdir", default=HERE)
    ap.add_argument("--gcf-trees-dir", default=None, dest="gcf_trees_dir",
                    help="BiG-SCAPE run output_files/<ts>_c<cutoff> dir; when set, families are "
                         "phylogeny-ordered by their matched GCF Newick tree (dendrogram gutter).")
    ap.add_argument("--locus-map", default=None,
                    help="TSV binding each GBK basename to strain, full_node_or_contig, region, "
                         "and bgc_alias. When supplied, every member must bind or rendering "
                         "fails closed.")
    a = ap.parse_args()
    res = render_families(db=a.db, cutoff=a.cutoff, families=a.family, outdir=a.outdir,
                          trees_dir=a.gcf_trees_dir, locus_map=a.locus_map)
    for m in res["families"]:
        tree = f", tree={m['tree_leaves']} tips" if m.get("has_tree") else ""
        emit(f"fam {m['family_id']}: {m['tracks']} tracks, {m['n_shared']} shared "
              f"orthogroups, private={m['private']}{tree} -> {os.path.basename(m['path'])}")
    emit(f"\n{len(res['families'])} html file(s) + index -> {res['index']}")


if __name__ == "__main__":
    main()
