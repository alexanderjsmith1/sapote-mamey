#!/usr/bin/env python3
"""bigscape_clinker_html — clinker-style within-family gene alignment pages (HTML, optional PDF) from a BiG-SCAPE 2 DB.

One self-contained HTML page per family: each member region is a gene-arrow track; genes sharing a dominant Pfam
domain ("orthogroup", the top-scoring `hsp` row of the CDS) are colour-linked with ribbons; tracks are shifted so
shared genes line up. No external assets; opens over file://. With --chrome, each page is also printed to a
single-page PDF sized to the track count.

Selections: --family <id> … or --focus <strain> (every family at --cutoff holding one of the strain's regions,
plus, with --fallback-cutoff, the fallback family of each region unplaced at --cutoff).

Track classes come from the staged file names: query (--query-regex), MIBiG (`BGC…`), a --layer-prefix layer
(default SID_, TYPE_), or REF (`<stem>__<region>`). "Private" = every track is a query track.

Homology, not function. Orthogroups are shared dominant Pfam domains, class-level only; reference tracks are
similarity anchors, not identity. Judgment deferred.
"""
from __future__ import annotations
import argparse, collections, csv, html, json, os, re, sqlite3, subprocess, sys, tempfile, time
from pathlib import Path

try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run outside an editable install
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from _console import emit
except ImportError:
    emit = print

PALETTE = ["#5b8def", "#e0724d", "#43a08a", "#c65fb0", "#d1a53a", "#6c7bd8", "#4aa3c7", "#d05c72", "#7fae3e", "#b078d6",
           "#2fa46b", "#c78a3d", "#5d9fd6", "#d15f9a", "#8a9a4d", "#9a6fd0", "#4bb0a0", "#cf6d5a", "#6f8fdd", "#c05fa0"]

TEMPLATE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title>
<style>
:root{--bg:#0e0f12;--panel:#16181d;--line:#262a31;--tx:#e7e9ee;--mut:#8b91a0;--acc:#5b8def;--track:#20242b;--axis:#3a3f47;--grey:#5b6270}
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
.tag.query{color:#e0724d;border-color:#e0724d55}.tag.SID{color:#43a08a;border-color:#43a08a55}.tag.TYPE{color:#8b91a0}.tag.REF{color:#d1a53a}.tag.MIBiG{color:#c65fb0}.tag.Cameron{color:#d1a53a}
@media print{body{background:#fff;color:#1b1e24}.bar,#tip{display:none}}
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
  <label class="chk"><input type="checkbox" id="links" checked> homology ribbons</label>
  <label class="chk"><input type="checkbox" id="conserved"> conserved genes only</label>
  <label class="chk"><input type="checkbox" id="align" checked> align on shared genes</label>
  <span class="toggle" id="themebtn">theme</span>
</div>
<svg id="map" preserveAspectRatio="xMinYMin meet"></svg>
<div class="legend" id="leg"></div>
<div class="foot" id="hidden">__HIDDEN_NOTE__</div><div class="foot" id="foot"></div></div><div id="tip"></div>
<script>
const DATA=__PAYLOAD__;const NS="http://www.w3.org/2000/svg";
const $=i=>document.getElementById(i);
const el=(t,a)=>{const e=document.createElementNS(NS,t);for(const k in(a||{}))e.setAttribute(k,a[k]);return e;};
const KIND={"biosynthetic":"#e0724d","biosynthetic-additional":"#d1a53a","transport":"#43a08a","regulatory":"#6c7bd8","resistance":"#d05c72","other":"#8b91a0","":"#5b6270"};
let state={colmode:"og",links:1,conserved:0,align:1};
function ogColor(og){if(!og)return"var(--grey)";const o=DATA.orthogroups[og];return o&&o.shared?o.color:"var(--grey)";}
function geneColor(g){return state.colmode=="kind"?(KIND[g.gene_kind]||"#5b6270"):ogColor(g.og);}
function shown(track){return state.conserved?track.genes.filter(g=>g.og&&DATA.orthogroups[g.og]&&DATA.orthogroups[g.og].shared):track.genes;}
function trackOffset(t){return state.align?(t.offset||0):0;}
function domain(){let mn=1e15,mx=-1e15;DATA.tracks.forEach(t=>{const off=trackOffset(t);shown(t).forEach(g=>{mn=Math.min(mn,g.x0+off);mx=Math.max(mx,g.x1+off);});});if(mn>mx){mn=0;mx=1;}return[mn,mx];}
function tip(ev,g,t){const el2=$("tip");if(!g){el2.style.opacity=0;return;}
  const pf=(g.pfams&&g.pfams.length)?g.pfams.join(", "):"no Pfam hit";
  el2.innerHTML=`<b>${t.strain}</b> · orf ${g.orf} · ${g.aa||"?"} aa · ${g.strand<0?"−":"+"} strand<br>`+
   `<span class="m">role:</span> ${g.gene_kind||"—"}<br><span class="m">orthogroup (dom. Pfam):</span> ${g.og||"—"}<br><span class="m">domains:</span> ${pf}`;
  el2.style.left=Math.min(ev.clientX+14,window.innerWidth-350)+"px";el2.style.top=(ev.clientY+14)+"px";el2.style.opacity=1;}
function draw(){
  const sv=$("map");sv.innerHTML="";
  const _lab=t=>Math.max(t.strain.length*7.2,(`${t.cls} · ${t.product} · ${t.genes.length} genes${t.flipped?" · shown reverse-complemented":""}`).length*6.0);
  const L=Math.min(360,Math.max(170,14+Math.ceil(Math.max(...DATA.tracks.map(_lab)))+12)),R=30,W=1200,rowH=64,top=44;const n=DATA.tracks.length;const H=top+n*rowH+30;
  sv.setAttribute("viewBox",`0 0 ${W} ${H}`);sv.style.maxHeight=(H+4)+"px";
  const[mn,mx]=domain();const sx=v=>L+(v-mn)/((mx-mn)||1)*(W-L-R);
  // scale bar (top)
  const kb=10000;const x0=sx(mn),x1=sx(mn+kb);
  sv.appendChild(el("line",{x1:x0,y1:22,x2:x1,y2:22,stroke:"var(--axis)","stroke-width":2}));
  const st=el("text",{x:x0,y:16,fill:"var(--mut)","font-size":11});st.textContent="10 kb (aligned bp)";sv.appendChild(st);
  const rowY=i=>top+i*rowH+rowH/2;
  // homology ribbons between consecutive tracks
  if(state.links){for(let i=0;i<n-1;i++){const A=DATA.tracks[i],B=DATA.tracks[i+1];const oa=trackOffset(A),ob=trackOffset(B);
    const bybOg={};shown(B).forEach(g=>{if(g.og&&DATA.orthogroups[g.og]&&DATA.orthogroups[g.og].shared){(bybOg[g.og]=bybOg[g.og]||[]).push(g);}});
    shown(A).forEach(g=>{if(!g.og)return;const o=DATA.orthogroups[g.og];if(!o||!o.shared)return;const cand=bybOg[g.og];if(!cand)return;
      const gc=(g.x0+g.x1)/2+oa;let best=cand[0],bd=1e15;cand.forEach(h=>{const d=Math.abs((h.x0+h.x1)/2+ob-gc);if(d<bd){bd=d;best=h;}});
      const ax=sx((g.x0+g.x1)/2+oa),bx=sx((best.x0+best.x1)/2+ob);const ay=rowY(i)+13,by=rowY(i+1)-13;
      const p=el("path",{d:`M ${ax-6} ${ay} L ${ax+6} ${ay} L ${bx+6} ${by} L ${bx-6} ${by} Z`,fill:o.color,opacity:.16});sv.appendChild(p);});
  }}
  // tracks
  DATA.tracks.forEach((t,i)=>{const y=rowY(i),off=trackOffset(t);
    // baseline
    const gs=shown(t);if(gs.length){const lo=sx(Math.min(...gs.map(g=>g.x0))+off),hi=sx(Math.max(...gs.map(g=>g.x1))+off);
      sv.appendChild(el("line",{x1:lo,y1:y,x2:hi,y2:y,stroke:"var(--track)","stroke-width":10,"stroke-linecap":"round"}));}
    // label
    const lab=el("text",{x:14,y:y-6,fill:"var(--tx)","font-size":12.5,"font-weight":600});lab.textContent=t.strain;sv.appendChild(lab);if(lab.getComputedTextLength()>L-28){lab.setAttribute("textLength",L-28);lab.setAttribute("lengthAdjust","spacingAndGlyphs");}
    const sub=el("text",{x:14,y:y+11,fill:"var(--mut)","font-size":10.5});sub.textContent=`${t.cls} · ${t.product} · ${gs.length} genes${t.flipped?" · shown reverse-complemented":""}`;sv.appendChild(sub);if(sub.getComputedTextLength()>L-28){sub.setAttribute("textLength",L-28);sub.setAttribute("lengthAdjust","spacingAndGlyphs");}
    // arrows
    gs.forEach(g=>{const a=sx(g.x0+off),b=sx(g.x1+off),w=Math.max(5,b-a),ar=Math.min(9,w*0.5),h=14,col=geneColor(g);
      const up=g.strand>0;const yt=y-h/2,yb=y+h/2;
      const d=up?`M${a} ${yt} H${a+w-ar} L${a+w} ${y} L${a+w-ar} ${yb} H${a} Z`:`M${a+w} ${yt} H${a+ar} L${a} ${y} L${a+ar} ${yb} H${a+w} Z`;
      const pa=el("path",{d,fill:col,stroke:"rgba(0,0,0,.25)","stroke-width":.5,cursor:"pointer"});
      pa.addEventListener("mousemove",ev=>tip(ev,g,t));pa.addEventListener("mouseleave",()=>tip(null));sv.appendChild(pa);});
  });
  drawLegend();
}
function drawLegend(){const leg=$("leg");leg.innerHTML="";
  if(state.colmode=="kind"){Object.entries(KIND).forEach(([k,c])=>{if(k==="")return;const s=document.createElement("span");s.innerHTML=`<i style="background:${c}"></i>${k}`;leg.appendChild(s);});
    const s=document.createElement("span");s.innerHTML=`<i style="background:var(--grey)"></i>none`;leg.appendChild(s);return;}
  const ent=Object.entries(DATA.orthogroups).filter(([k,o])=>o.shared).sort((a,b)=>b[1].n-a[1].n).slice(0,16);
  ent.forEach(([k,o])=>{const s=document.createElement("span");s.innerHTML=`<i style="background:${o.color}"></i>${k} <span style="opacity:.6">(${o.n})</span>`;leg.appendChild(s);});
  const s=document.createElement("span");s.innerHTML=`<i style="background:var(--grey)"></i>strain-unique / no Pfam`;leg.appendChild(s);}
function init(){
  $("ttl").innerHTML=`GCF family ${DATA.family_id} — within-family gene alignment`+
    (DATA.private?` <span class="tag priv">query-private</span>`:"");
  $("sub").innerHTML=`${DATA.tracks.length} member BGCs · ${DATA.product_summary} · cutoff c${DATA.cutoff} · `+
    `${DATA.n_shared} shared orthogroups · classes: ${DATA.class_summary}`;
  $("colmode").onchange=e=>{state.colmode=e.target.value;draw();};
  $("links").onchange=e=>{state.links=e.target.checked?1:0;draw();};
  $("conserved").onchange=e=>{state.conserved=e.target.checked?1:0;draw();};
  $("align").onchange=e=>{state.align=e.target.checked?1:0;draw();};
  $("themebtn").onclick=()=>{const r=document.documentElement;const cur=r.getAttribute("data-theme");
    const isLight=cur?cur=="light":matchMedia("(prefers-color-scheme:light)").matches;r.setAttribute("data-theme",isLight?"dark":"light");draw();};
  $("foot").textContent="Homology, not function. Orthogroups = shared dominant Pfam domain (BiG-SCAPE HSP scan); "+
    "ribbons show sequence-similarity synteny, class-level only. query-private = every track is a query record: no reference-layer or MIBiG member fell in this "+
    "family at this cutoff (a statement about the panel, not the organism). Reference tracks are similarity anchors, not identity. Judgment deferred.";
  draw();
}
init();
</script></body></html>"""


def strain_key(basename):
    """Use the same exact staged strain namespace as the cross-strain export."""
    from mamey.bigscape_namespace import strain_from_gbk_name
    return strain_from_gbk_name(basename)


def classify(basename, organism, query_rx, prefixes, labels=None):
    """(track label, class) for one gbk row. Reference label = --labels entry for the strain prefix if given,
    else the FULL deposited organism string (never truncated: 'Saccharopolyspora spinosa NRRL 18395' used to
    print as 'Saccharopolyspora spinosa NRRL', and two S. erythraea genomes printed identically)."""
    org = " ".join((organism or "").split()) if organism and organism != "." else ""
    lab = (labels or {}).get(strain_key(basename))
    if lab:
        org = lab
    if re.match(r"^BGC\d+", basename):
        return f"{basename.split('.')[0]} {org}".strip(), "MIBiG"
    for pre in prefixes:
        if basename.startswith(pre):
            stem = re.sub(r"\.region\d+\.gbk$", "", basename[len(pre):])
            return (org or stem.replace("_", " ")), pre.rstrip("_")
    m = query_rx.match(basename)
    if m:
        return m.group(1), "query"
    if "__" in basename:
        return (org or basename.split("__", 1)[0].replace("_", " ")), "REF"
    return (org or re.sub(r"\.region\d+\.gbk$", "", basename)), "REF"


def load_labels(path):
    """TSV strain<TAB>label (header row optional); returns {} when no path."""
    if not path:
        return {}
    out = {}
    with open(path, newline="") as h:
        for r in csv.reader(h, delimiter="\t"):
            if r and r[0] == "strain":
                continue
            if len(r) != 2 or not all(r) or r[0] in out:
                raise ValueError("LABELS_REFUSED: exactly two columns and unique nonempty strain keys required")
            out[r[0]] = r[1]
    return out


def gbk_index(con, query_rx, prefixes, labels=None):
    return {gid: classify(os.path.basename(path or ""), org, query_rx, prefixes, labels) for gid, path, org in con.execute("select id, path, organism from gbk")}


def family_members(con, cutoff, idx):
    fam = collections.defaultdict(list)
    for fid, rid, gbkid, prod, a, b in con.execute(
            "select bf.family_id, r.id, r.gbk_id, r.product, r.nt_start, r.nt_stop from bgc_record_family bf join family f on f.id=bf.family_id "
            "join bgc_record r on r.id=bf.record_id where abs(f.cutoff-?)<1e-6 and r.record_type='region'", (cutoff,)):
        s, cl = idx.get(gbkid, ("?", "REF"))
        fam[fid].append(dict(record_id=rid, gbk_id=gbkid, product=prod or "", nt_start=a, nt_stop=b, strain=s, cls=cl))
    return fam


def genes_for_gbk(con, gbk_id):
    rows = con.execute("select id, nt_start, nt_stop, orf_num, strand, gene_kind, aa_seq from cds where gbk_id=? order by nt_start", (gbk_id,)).fetchall()
    if not rows:
        return []
    base = min(r[1] for r in rows); genes = []
    for cid, a, b, orf, strand, kind, aa in rows:
        pfams, seen = [], set()
        for acc, _sc in con.execute("select accession, bit_score from hsp where cds_id=? order by bit_score desc", (cid,)):
            if acc not in seen:
                seen.add(acc); pfams.append(acc)
        genes.append(dict(orf=orf, x0=a - base, x1=b - base, strand=-1 if strand in (-1, "-", "-1") else 1, gene_kind=kind or "",
                          aa=len(aa) if aa else None, pfams=pfams, og=pfams[0] if pfams else None))
    return genes


def build_family(con, fid, cutoff, fam, ref_strain=None, min_genes=1, row_order="genes"):
    members = fam.get(fid)
    if not members:
        return None
    tracks, hidden, og_members = [], [], collections.defaultdict(set)
    for mi, m in enumerate(members):
        genes = genes_for_gbk(con, m["gbk_id"])
        if len(genes) < min_genes:
            hidden.append(dict(strain=m["strain"], record_id=m["record_id"], genes=len(genes)))
            continue
        for g in genes:
            if g["og"]:
                og_members[g["og"]].add(mi)
        tracks.append(dict(strain=m["strain"], cls=m["cls"], product=m["product"], record_id=m["record_id"], genes=genes, offset=0))
    if len(tracks) < 2:
        return None
    shared = sorted([og for og, s in og_members.items() if len(s) >= 2], key=lambda og: -len(og_members[og]))
    orthogroups = {og: dict(color=PALETTE[i % len(PALETTE)], shared=True, n=len(og_members[og])) for i, og in enumerate(shared)}
    for og, s in og_members.items():
        orthogroups.setdefault(og, dict(color="#5b6270", shared=False, n=len(s)))
    cand = [i for i in range(len(tracks)) if ref_strain and tracks[i]["strain"] == ref_strain] or list(range(len(tracks)))
    ref = max(cand, key=lambda i: len(tracks[i]["genes"]))   # the focal strain's own track sets the orientation

    def centroids(tr):
        d = {}
        for g in tr["genes"]:
            if g["og"] and orthogroups[g["og"]]["shared"]:
                d.setdefault(g["og"], []).append((g["x0"] + g["x1"]) / 2)
        return {k: sum(v) / len(v) for k, v in d.items()}
    refc = centroids(tracks[ref])
    ref_strand = {g["og"]: g["strand"] for g in tracks[ref]["genes"] if g["og"] and orthogroups[g["og"]]["shared"]}
    for i, tr in enumerate(tracks):
        if i == ref:
            continue
        # Orientation: flip a track (mirror within its span, negate strands) when its shared genes run in the opposite
        # order to the reference (negative rank correlation of positions) or, with too few genes to order, when most
        # shared genes sit on the opposite strand to their reference partners.
        tc = centroids(tr); common = [og for og in tc if og in refc]
        rho = 0.0
        if len(common) >= 2:
            ra = {og: k for k, og in enumerate(sorted(common, key=lambda og: refc[og]))}
            rb = {og: k for k, og in enumerate(sorted(common, key=lambda og: tc[og]))}
            n = len(common); rho = 1 - 6 * sum((ra[og] - rb[og]) ** 2 for og in common) / (n * (n * n - 1))
        same = sum(1 for g in tr["genes"] if g["og"] in ref_strand and g["strand"] == ref_strand[g["og"]])
        opp = sum(1 for g in tr["genes"] if g["og"] in ref_strand and g["strand"] != ref_strand[g["og"]])
        if rho < -0.2 or (abs(rho) <= 0.2 and opp > same):
            span = max(g["x1"] for g in tr["genes"])
            for g in tr["genes"]:
                g["x0"], g["x1"], g["strand"] = span - g["x1"], span - g["x0"], -g["strand"]
            tr["genes"].sort(key=lambda g: g["x0"]); tr["flipped"] = True; tc = centroids(tr)
        if common:
            tr["offset"] = sum(refc[og] - tc[og] for og in common) / len(common)
    cls_count = collections.Counter(t["cls"] for t in tracks); prods = collections.Counter(t["product"] for t in tracks)
    if row_order == "similarity" and len(tracks) > 2:
        ogs = {id(t): {g["og"] for g in t["genes"] if g.get("og")} for t in tracks}
        rest = sorted(tracks, key=lambda t: -len(t["genes"])); order = [rest.pop(0)]
        while rest:
            last = ogs[id(order[-1])]
            nxt = max(rest, key=lambda t: (len(ogs[id(t)] & last), len(t["genes"])))
            rest.remove(nxt); order.append(nxt)
        tracks = order
    else:
        tracks.sort(key=lambda t: -len(t["genes"]))
    return dict(family_id=fid, cutoff=cutoff, tracks=tracks, orthogroups=orthogroups, n_shared=len(shared), hidden_tracks=hidden, min_genes=min_genes,
                product_summary="; ".join(f"{p} x{n}" for p, n in prods.most_common()),
                class_summary=", ".join(f"{c} {n}" for c, n in cls_count.most_common()), private=all(m["cls"] == "query" for m in members))


def to_pdf(html_path, n_tracks, chrome):
    """Print in an isolated profile; a complete validated PDF is the completion signal.

    Some browser builds retain background services after printing. Stop only the isolated
    process once its PDF is complete; never treat a stale output or a partial PDF as success.
    """
    try:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError
    except ImportError:
        sys.stderr.write("CLINKER_PDF_REFUSED: install the documents extra (pypdf) for validated PDF output\n")
        return None
    height = 44 + n_tracks * 64 + 30 + 320
    src = Path(html_path).read_text(encoding="utf-8")
    pdf = str(Path(html_path).with_suffix(".pdf"))
    if Path(pdf).exists():
        sys.stderr.write("CLINKER_PDF_REFUSED: output already exists\n")
        return None
    tmp = str(html_path) + ".print.html"
    Path(tmp).write_text(src.replace("</style>", f"@page{{size:1260px {height}px;margin:10px}}</style>", 1), encoding="utf-8")
    complete = False
    try:
        with tempfile.TemporaryDirectory(prefix="clinker-chrome-") as profile:
            process = subprocess.Popen([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                "--virtual-time-budget=4000", "--no-first-run", "--no-default-browser-check",
                "--disable-extensions", "--disable-background-networking", "--disable-component-update",
                "--disable-sync", "--disable-features=MediaRouter", f"--user-data-dir={profile}", f"--print-to-pdf={pdf}",
                Path(tmp).resolve().as_uri()], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                deadline = time.monotonic() + 60
                while time.monotonic() < deadline:
                    if Path(pdf).is_file():
                        try:
                            reader = PdfReader(pdf)
                            text = reader.pages[0].extract_text() if len(reader.pages) == 1 else ""
                            complete = bool(text and "GCF family" in text and "ERR_" not in text)
                        except (PdfReadError, OSError, ValueError, IndexError):
                            complete = False
                    if complete or process.poll() is not None:
                        break
                    time.sleep(0.2)
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill(); process.wait(timeout=5)
    finally:
        Path(tmp).unlink(missing_ok=True)
    if complete:
        return pdf
    sys.stderr.write("CLINKER_PDF_REFUSED: no complete single-page family PDF within the print deadline\n")
    return None


def write_page(payload, title, outp):
    hidden = payload.get("hidden_tracks", [])
    note = ""
    if hidden:
        note = (f"{len(hidden)} track(s) with fewer than {payload['min_genes']} genes hidden from this view. "
                "They remain in the database and export; this is a display filter.")
    encoded = json.dumps(payload, separators=(",", ":")).replace("<", "\\u003c")
    page = TEMPLATE.replace("__PAYLOAD__", encoded).replace("__TITLE__", html.escape(title))
    page = page.replace("__HIDDEN_NOTE__", html.escape(note))
    Path(outp).write_text(page, encoding="utf-8")


def strain_family_map(con, strain, cutoff):
    recs = [r[0] for r in con.execute("select r.id from bgc_record r join gbk g on g.id=r.gbk_id where r.record_type='region'")
            if True]
    names = dict(con.execute("select r.id, g.path from bgc_record r join gbk g on g.id=r.gbk_id where r.record_type='region'").fetchall())
    recs = [rid for rid in recs if os.path.basename(names[rid]).startswith(strain + "_")]
    q = ",".join("?" * len(recs)) or "NULL"
    m = dict(con.execute(f"select bf.record_id, f.id from bgc_record_family bf join family f on f.id=bf.family_id where abs(f.cutoff-?)<1e-6 and bf.record_id in ({q})", (cutoff, *recs)).fetchall())
    return recs, m


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--db", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--cutoff", type=float, default=0.3); ap.add_argument("--fallback-cutoff", type=float, default=None)
    ap.add_argument("--family", type=int, nargs="*", default=None); ap.add_argument("--focus", action="append", default=[])
    ap.add_argument("--query-regex", default=r"^([A-Za-z]+-\d+)_", help="regex on the staged GBK basename; group 1 becomes the track label. MUST contain one capture group, e.g. '^(SYN-[0-9]+)'")
    ap.add_argument("--layer-prefix", action="append", default=None)
    ap.add_argument("--row-order", choices=("genes","similarity"), default="genes")
    ap.add_argument("--min-genes", type=int, default=1)
    ap.add_argument("--chrome", default=None, help="path to a Chrome/Chromium binary; when given each page is also printed to PDF")
    ap.add_argument("--labels", default=None, help="TSV strain<TAB>label: track label per staged-GBK strain prefix (deposited organism + strain, [Type] from the assembly-from-type flag)")
    a = ap.parse_args(argv)
    try:
        query_rx = re.compile(a.query_regex)
    except re.error as exc:
        ap.error(f"--query-regex is invalid: {exc}")
    if a.min_genes < 1:
        ap.error("--min-genes must be at least 1")
    if query_rx.groups < 1:
        ap.error(f"--query-regex {a.query_regex!r} has no capture group; group 1 is the track label (try '^(SYN-[0-9]+)')")
    prefixes = tuple(a.layer_prefix) if a.layer_prefix else ("SID_", "TYPE_")
    con = sqlite3.connect(a.db); idx = gbk_index(con, query_rx, prefixes, load_labels(a.labels))
    fams = {a.cutoff: family_members(con, a.cutoff, idx)}
    if a.fallback_cutoff:
        fams[a.fallback_cutoff] = family_members(con, a.fallback_cutoff, idx)
    jobs = []   # (out dir, cutoff, fid, strain label, strain record ids)
    for fid in a.family or []:
        jobs.append((Path(a.out), a.cutoff, fid, "", []))
    for strain in a.focus:
        recs, m_main = strain_family_map(con, strain, a.cutoff)
        m_fb = strain_family_map(con, strain, a.fallback_cutoff)[1] if a.fallback_cutoff else {}
        todo = collections.OrderedDict()
        for rid in recs:
            if rid in m_main: todo.setdefault((a.cutoff, m_main[rid]), []).append(rid)
            elif rid in m_fb: todo.setdefault((a.fallback_cutoff, m_fb[rid]), []).append(rid)
        for (cut, fid), rids in todo.items():
            jobs.append((Path(a.out) / "strain_focus" / strain / f"clinker_c{cut:g}", cut, fid, strain, rids))
    index = collections.defaultdict(list)
    for d, cut, fid, strain, rids in jobs:
        d.mkdir(parents=True, exist_ok=True); n_rec = len(rids)
        prods = sorted({(p or "") for (p,) in con.execute(f"select product from bgc_record where id in ({','.join('?'*len(rids)) or 'NULL'})", rids)}) if rids else []
        product = ";".join(p for p in prods if p) or ""
        payload = build_family(con, fid, cut, fams[cut], ref_strain=strain or None, min_genes=a.min_genes, row_order=a.row_order)
        if not payload:
            index[strain].append({"family_id": fid, "cutoff": cut, "status": "skipped: <2 renderable members"}); continue
        prefix = (re.sub(r"[^A-Za-z0-9]+", "-", product).strip("-")[:40] + "__") if product else ""   # product first: a folder sorts by class
        outp = d / f"{prefix}GCF{fid}_c{cut:g}_clinker.html"
        write_page(payload, f"{strain + ' ' if strain else ''}GCF {fid} alignment (c{cut:g})", outp)
        pdf = to_pdf(outp, len(payload["tracks"]), a.chrome) if a.chrome else None
        cls = collections.Counter(t["cls"] for t in payload["tracks"])
        index[strain].append({"family_id": fid, "cutoff": cut, "strain_product": product, "tracks": len(payload["tracks"]), "strain_records": n_rec,
                              "classes": ";".join(f"{k}={v}" for k, v in sorted(cls.items())), "shared_orthogroups": payload["n_shared"],
                              "private": payload["private"], "html": os.path.relpath(outp, a.out), "pdf": os.path.relpath(pdf, a.out) if pdf else "",
                              "status": "OK" if (pdf or not a.chrome) else "PDF FAILED"})
        emit(f"{strain or 'family'} GCF{fid} c{cut:g}: {len(payload['tracks'])} tracks, {payload['n_shared']} shared orthogroups" + (f", pdf={'ok' if pdf else 'FAILED'}" if a.chrome else ""))
    for strain, rows in index.items():
        d = (Path(a.out) / "strain_focus" / strain) if strain else Path(a.out); d.mkdir(parents=True, exist_ok=True)
        with open(d / "CLINKER_INDEX.tsv", "w", encoding="utf-8", newline="") as h:
            w = _SafeDictWriter(h, fieldnames=["family_id", "cutoff", "strain_product", "tracks", "strain_records", "classes", "shared_orthogroups", "private", "html", "pdf", "status"],
                               delimiter="\t", lineterminator="\n", extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
