#!/usr/bin/env python3
"""af_leadboard_widget.py — cohort-wide ANTIFUNGAL lead-board dashboard, single
self-contained HTML (graduated into the engine as a first-class deliverable tool,
v9.7.349x candidate).

Flagship dashboard for the Sapote-Mamey bee/wasp actinomycete cohort: one sortable/
filterable table of AF-capacity leads across every AS strain, plus an AF-vs-novelty
scatter (points coloured by ⚡ priority tier). Ranked by AF capacity.

Data sources (all on disk, read-only):
  - strain_data/SAPOTE_PER_BGC_MASTER_all_AS.csv  (strain, bgc, products,
        lead_tier, AF, AB, novelty, family_anchor/accession = MIBiG anchor, guard_flags)
  - AS-XXX/mode_b_codex_judged_2026-07-31/*_CODEX_JUDGED.md  ('Chase it?** **<TIER>'
        priority + 'antifungal/antibacterial-capacity' bioactivity lean)
  - _OVERMERGE_MODULE/OVERMERGE_REGISTER_GBK.tsv  (per (strain,bgc) over-merge verdict)

Cohort rules baked in:
  - AS-XXX (contaminated) is EXCLUDED entirely.
  - AS-XXX (chimeric assembly) is kept but flagged audit-only (excluded from ranking crown).

Claim-safety (mandatory, printed in the dashboard):
  AF is a class-level CAPACITY prior derived from mechanism/domain content — NOT measured
  antifungal activity. Measured non-inhibition is assay-specific and never proves incapacity.
  MIBiG/KCB comparators are similarity anchors, not identity. Judgment is deferred.

Stdlib-only; theme-aware (light/dark via CSS vars); opens over file://.

Usage:
  python af_leadboard_widget.py [--out DIR] [--master-csv CSV] [--root DIR]
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, json, os, re, glob, html, datetime, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _widget_paths import ROOT_DEFAULT, master_dir as _master_dir, module_dir  # noqa: E402

import os as _os, sys as _sys  # bundle-root path guard (see tests/test_tool_front_doors.py)
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
try:  # cohort exclusions come from the governed SSOT, never hardcoded here
    from mamey.exclusions import governed_excluded, raw_assembly_void
    EXCLUDE_STRAINS = governed_excluded()      # contaminated — drop entirely
    AUDIT_ONLY_STRAINS = raw_assembly_void()   # chimeric assembly — keep but flag
except Exception as _exc:  # pragma: no cover - standalone use without mamey
    raise RuntimeError(
        "cohort exclusions are governed data and are not shipped in the code tier: "
        "install the mamey package, or set MAMEY_OFFICIAL_DATA to a directory "
        "containing exclusions.json"
    ) from _exc

TIER_ORDER = {"TOP": 6, "EXCEPTIONAL": 5, "HIGH": 4, "MEDIUM": 3, "WATCHLIST": 2,
              "LOW": 1, "OMIT": 0, "": -1}


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def parse_codex(strain_dir):
    """Return {bgc_id: {tier, lean_kind, lean_text}} for one strain's codex-judged cards."""
    out = {}
    for md in glob.glob(os.path.join(strain_dir, "mode_b_codex_judged_2026-07-31",
                                     "*_CODEX_JUDGED.md")):
        m = re.search(r"_(BGC\d+)_", os.path.basename(md))
        if not m:
            continue
        bgc = m.group(1)
        try:
            txt = open(md, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        rec = {"tier": "", "lean_kind": "", "lean_text": ""}
        cm = re.search(r"Chase it\?\*\*\s*\*\*([A-Z]+)\*\*\s*(?:—|-)?\s*(.*)", txt)
        if cm:
            rec["tier"] = cm.group(1).strip().upper()
            chase_rest = cm.group(1) and cm.group(2).strip()
        else:
            chase_rest = ""
        blob = (chase_rest or "") + " " + txt[:2000]
        low = blob.lower()
        af = "antifungal-capacity" in low or "antifungal capacity" in low
        ab = "antibacterial-capacity" in low or "antibacterial capacity" in low
        if af and ab:
            rec["lean_kind"] = "dual"
        elif af:
            rec["lean_kind"] = "antifungal"
        elif ab:
            rec["lean_kind"] = "antibacterial"
        elif "housekeeping" in low or rec["tier"] == "OMIT":
            rec["lean_kind"] = "housekeeping"
        lm = re.search(r"Bioactivity lean:\*\*\s*(.+)", txt)
        if lm:
            rec["lean_text"] = re.sub(r"\s+", " ", lm.group(1)).strip()[:300]
        elif chase_rest:
            rec["lean_text"] = re.sub(r"\s+", " ", chase_rest).strip()[:300]
        out[bgc] = rec
    return out


def parse_overmerge(overmerge_tsv):
    """Return {(strain,bgc): verdict}."""
    out = {}
    if not os.path.exists(overmerge_tsv):
        return out
    with open(overmerge_tsv, encoding="utf-8", errors="ignore") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            out[(row.get("strain", ""), row.get("bgc", ""))] = row.get("verdict", "")
    return out


def product_class(products):
    if not products:
        return "unclassified"
    first = products.split(";")[0].strip()
    return first or "unclassified"


def is_housekeeping(row, codex):
    gf = (row.get("guard_flags") or "").lower()
    if "primary_metab" in gf or "primary metabolism" in gf:
        return True
    if codex.get("lean_kind") == "housekeeping":
        return True
    if codex.get("tier") == "OMIT":
        return True
    return False


def build_leads(master_csv, master_dir, overmerge_tsv):
    overmerge = parse_overmerge(overmerge_tsv)
    codex_by_strain = {}
    leads = []
    with open(master_csv, encoding="utf-8", errors="ignore") as f:
        for row in csv.DictReader(f):
            strain = row["strain"].strip()
            if strain in EXCLUDE_STRAINS:
                continue
            if strain not in codex_by_strain:
                codex_by_strain[strain] = parse_codex(os.path.join(master_dir, strain))
            bgc = row["bgc_id"].strip()
            cx = codex_by_strain[strain].get(bgc, {})
            af = _num(row.get("AF"))
            ab = _num(row.get("AB"))
            nov = _num(row.get("novelty"))
            anchor = (row.get("family_anchor") or "").strip()
            acc = (row.get("family_accession") or "").strip()
            mibig = anchor
            if anchor and acc:
                mibig = f"{anchor} ({acc})"
            elif acc:
                mibig = acc
            om = overmerge.get((strain, bgc), "")
            om_flag = {"OVER_MERGED": "over-merged",
                       "COHERENT_HYBRID": "coherent-hybrid"}.get(om, "")
            codex_rec = cx or {"tier": "", "lean_kind": "", "lean_text": ""}
            leads.append({
                "strain": strain,
                "bgc": bgc,
                "products": (row.get("products") or "").strip(),
                "pclass": product_class(row.get("products")),
                "af": af, "ab": ab, "novelty": nov,
                "engine_tier": (row.get("lead_tier") or "").strip(),
                "tier": codex_rec.get("tier", ""),
                "lean_kind": codex_rec.get("lean_kind", ""),
                "lean_text": codex_rec.get("lean_text", ""),
                "overmerge": om_flag,
                "mibig": mibig or "—",
                "housekeeping": is_housekeeping(row, codex_rec),
                "audit_only": strain in AUDIT_ONLY_STRAINS,
                "sapote_read": (row.get("sapote_read") or "").strip(),
            })
    leads.sort(key=lambda r: (
        r["audit_only"],
        -(r["af"] if r["af"] is not None else -1),
        -(r["novelty"] if r["novelty"] is not None else -1),
        -TIER_ORDER.get(r["tier"], -1),
    ))
    for i, r in enumerate(leads, 1):
        r["af_rank"] = i
    return leads


TEMPLATE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title>
<style>
:root{--bg:#0e0f12;--panel:#16181d;--line:#262a31;--tx:#e7e9ee;--mut:#8b91a0;--acc:#5b8def;
  --exc:#c06bf0;--hi:#4bd07a;--med:#f2b13d;--wat:#5b8def;--omit:#6a7180;--af:#4bd07a;--ab:#f2b13d;
  --chip:#20232a;--row:#14161b;--rowA:#171a20;--tipbg:#20232a;--warn:#f0864b;}
@media (prefers-color-scheme: light){:root{--bg:#f6f7f9;--panel:#ffffff;--line:#dfe3ea;
  --tx:#1c2028;--mut:#6a7180;--acc:#2f6bd6;--exc:#9333c4;--hi:#189e52;--med:#c8850f;--wat:#2f6bd6;
  --omit:#a6adba;--af:#189e52;--ab:#c8850f;--chip:#eef1f5;--row:#ffffff;--rowA:#f4f6f9;--tipbg:#ffffff;--warn:#d1651f;}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1400px;margin:0 auto;padding:20px}
h1{font-size:17px;font-weight:600;margin:0 0 2px}.sub{color:var(--mut);font-size:12px;margin-bottom:12px}
.kpis{display:flex;flex-wrap:wrap;gap:10px;margin:12px 0 16px}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 14px;min-width:118px}
.kpi .n{font-size:20px;font-weight:700}.kpi .l{color:var(--mut);font-size:11px;margin-top:2px}
.bar{display:flex;flex-wrap:wrap;gap:14px;align-items:center;margin-bottom:12px;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.bar label{color:var(--mut);font-size:12px;display:inline-flex;align-items:center;gap:6px}
select,input[type=range]{accent-color:var(--acc)}
select{background:var(--chip);color:var(--tx);border:1px solid var(--line);border-radius:8px;padding:6px 10px;font-size:12.5px}
.chk{cursor:pointer;user-select:none}.chk input{margin-right:5px}
.sec{margin:18px 0 8px;display:flex;justify-content:space-between;align-items:baseline}
.sec h2{font-size:13px;font-weight:600;margin:0}.sec .r{color:var(--mut);font-size:12px}
.scatwrap{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:8px}
svg{width:100%;display:block}
.tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:10px}
table{border-collapse:collapse;width:100%;font-size:12.5px;min-width:1080px}
thead th{position:sticky;top:0;background:var(--panel);color:var(--mut);font-weight:600;text-align:left;
  padding:8px 10px;border-bottom:1px solid var(--line);cursor:pointer;white-space:nowrap;font-size:11.5px}
thead th.num{text-align:right}thead th:hover{color:var(--tx)}
tbody td{padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top}
tbody tr:nth-child(even){background:var(--rowA)}tbody tr:nth-child(odd){background:var(--row)}
td.num{text-align:right;font-variant-numeric:tabular-nums}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.chip{display:inline-block;padding:1px 7px;border-radius:20px;font-size:11px;font-weight:600;white-space:nowrap}
.t-TOP{background:var(--exc);color:#fff}.t-EXCEPTIONAL{background:var(--exc);color:#fff}.t-HIGH{background:var(--hi);color:#04240f}
.t-MEDIUM{background:var(--med);color:#2a1c00}.t-WATCHLIST{background:var(--wat);color:#04122a}
.t-OMIT{background:var(--omit);color:#fff}.t-none{background:var(--chip);color:var(--mut)}
.lean-antifungal{color:var(--af);font-weight:600}.lean-antibacterial{color:var(--ab)}
.lean-dual{color:var(--acc);font-weight:600}.lean-housekeeping{color:var(--mut)}
.om{color:var(--warn);font-weight:600;font-size:11px}.om-coherent{color:var(--mut);font-weight:500}
.audit{color:var(--warn);font-size:10px;font-weight:700;border:1px solid var(--warn);border-radius:4px;padding:0 4px;margin-left:5px}
.afbar{display:inline-block;height:9px;border-radius:3px;background:var(--af);vertical-align:middle;margin-left:6px;opacity:.85}
.dot{width:9px;height:9px;border-radius:50%;display:inline-block;vertical-align:middle}
.mut{color:var(--mut)}.rk{color:var(--mut);font-variant-numeric:tabular-nums}
#tip{position:fixed;pointer-events:none;background:var(--tipbg);border:1px solid var(--line);border-radius:8px;
  padding:8px 10px;font-size:12px;max-width:340px;opacity:0;transition:opacity .08s;z-index:9;box-shadow:0 8px 24px rgba(0,0,0,.35)}
#tip b{color:var(--tx)}
.foot{color:var(--mut);font-size:11.5px;margin-top:18px;border-top:1px solid var(--line);padding-top:12px}
.foot b{color:var(--tx)}.legend{display:flex;flex-wrap:wrap;gap:14px;margin-top:8px;color:var(--mut);font-size:12px}
.legend span{display:inline-flex;align-items:center;gap:6px}
</style></head><body><div class="wrap">
<h1>__H1__</h1>
<div class="sub" id="sub"></div>
<div class="kpis" id="kpis"></div>
<div class="bar">
  <label>Min AF <input type="range" id="minaf" min="0" max="100" step="2" value="0"><span id="minafv" class="mono">0</span></label>
  <label>Class <select id="fclass"></select></label>
  <label>Tier <select id="ftier"></select></label>
  <label>Lean <select id="flean"></select></label>
  <label class="chk"><input type="checkbox" id="hideom">hide over-merged</label>
  <label class="chk"><input type="checkbox" id="hidehk">hide housekeeping</label>
  <label class="chk"><input type="checkbox" id="hideaudit" checked>hide audit-only</label>
  <span style="flex:1"></span>
  <span class="mut" id="count"></span>
</div>
<div class="sec"><h2>AF capacity vs novelty</h2><span class="r">x = novelty prior · y = AF capacity prior · colour = ⚡ priority tier</span></div>
<div class="scatwrap"><svg id="scat" viewBox="0 0 1360 380" preserveAspectRatio="xMidYMid meet"></svg>
<div class="legend" id="leg"></div></div>
<div class="sec"><h2>AF lead board</h2><span class="r">click a header to sort · ranked by AF capacity</span></div>
<div class="tablewrap"><table>
<thead><tr>
  <th data-k="af_rank" class="num">#</th>
  <th data-k="strain">Strain</th>
  <th data-k="bgc">BGC</th>
  <th data-k="pclass">Product class</th>
  <th data-k="af" class="num">AF</th>
  <th data-k="ab" class="num">AB</th>
  <th data-k="novelty" class="num">Novelty</th>
  <th data-k="tier">⚡ Tier</th>
  <th data-k="lean_kind">Bioactivity lean</th>
  <th data-k="overmerge">Over-merge</th>
  <th data-k="mibig">MIBiG anchor</th>
</tr></thead>
<tbody id="tb"></tbody></table></div>
<div class="foot" id="foot"></div>
</div><div id="tip"></div>
<script>
const DATA=__PAYLOAD__;const META=__META__;
const $=i=>document.getElementById(i);const NS="http://www.w3.org/2000/svg";
const el=(t,a)=>{const e=document.createElementNS(NS,t);for(const k in(a||{}))e.setAttribute(k,a[k]);return e;};
const esc=s=>(s==null?"":String(s)).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c]));
const TIERC={TOP:"var(--exc)",EXCEPTIONAL:"var(--exc)",HIGH:"var(--hi)",MEDIUM:"var(--med)",WATCHLIST:"var(--wat)",OMIT:"var(--omit)","":"var(--omit)"};
const TIERO={TOP:6,EXCEPTIONAL:5,HIGH:4,MEDIUM:3,WATCHLIST:2,LOW:1,OMIT:0,"":-1};
let state={minaf:0,cls:"all",tier:"all",lean:"all",hideom:false,hidehk:false,hideaudit:true,sort:"af_rank",dir:1};
const num=v=>v==null?"—":(Math.round(v*10)/10);
function classes(){const s=new Set(DATA.map(d=>d.pclass));return [...s].sort();}
function leans(){const s=new Set(DATA.map(d=>d.lean_kind).filter(Boolean));return [...s].sort();}
function fillSelect(id,vals,label){const e=$(id);const o=document.createElement("option");o.value="all";o.textContent=label;e.appendChild(o);
  vals.forEach(v=>{const x=document.createElement("option");x.value=v;x.textContent=v;e.appendChild(x);});}
function filtered(){return DATA.filter(d=>{
  if(state.hideaudit&&d.audit_only)return false;
  if((d.af==null?-1:d.af)<state.minaf)return false;
  if(state.cls!="all"&&d.pclass!=state.cls)return false;
  if(state.tier!="all"&&d.tier!=state.tier)return false;
  if(state.lean!="all"&&d.lean_kind!=state.lean)return false;
  if(state.hideom&&d.overmerge=="over-merged")return false;
  if(state.hidehk&&d.housekeeping)return false;
  return true;});}
function cmp(a,b){const k=state.sort;let x=a[k],y=b[k];
  if(k=="tier"){x=TIERO[a.tier]??-1;y=TIERO[b.tier]??-1;}
  if(x==null)x=(typeof y=="number"?-Infinity:"");if(y==null)y=(typeof x=="number"?-Infinity:"");
  if(typeof x=="number"&&typeof y=="number")return (x-y)*state.dir;
  return String(x).localeCompare(String(y))*state.dir;}
function tip(ev,d){const t=$("tip");if(!d){t.style.opacity=0;return;}
  t.innerHTML=`<b>${esc(d.strain)} · ${esc(d.bgc)}</b>${d.audit_only?' <span class="audit">AUDIT-ONLY</span>':''}<br>`+
    `${esc(d.pclass)} · AF <b>${num(d.af)}</b> · AB ${num(d.ab)} · novelty ${num(d.novelty)}<br>`+
    `⚡ ${esc(d.tier||"—")} · ${esc(d.lean_kind||"—")}${d.overmerge?` · <span class="om">${esc(d.overmerge)}</span>`:''}<br>`+
    `<span class="mut">MIBiG anchor:</span> ${esc(d.mibig)}`;
  t.style.left=Math.min(ev.clientX+14,window.innerWidth-352)+"px";t.style.top=(ev.clientY+14)+"px";t.style.opacity=1;}
function kpis(rows){
  const nAF=rows.filter(d=>d.lean_kind=="antifungal"||d.lean_kind=="dual").length;
  const nHi=rows.filter(d=>d.tier=="EXCEPTIONAL"||d.tier=="HIGH").length;
  const strains=new Set(rows.map(d=>d.strain)).size;
  const topAF=rows.reduce((m,d)=>Math.max(m,d.af==null?0:d.af),0);
  const k=[[rows.length,"leads shown"],[strains,"strains"],[nAF,"AF-lean leads"],[nHi,"⚡ HIGH+ tier"],[num(topAF),"top AF prior"]];
  $("kpis").innerHTML=k.map(([n,l])=>`<div class="kpi"><div class="n">${n}</div><div class="l">${l}</div></div>`).join("");}
function scatter(rows){const sv=$("scat");sv.innerHTML="";const W=1360,H=380,L=54,R=20,T=16,B=44;
  const X=v=>L+(v/100)*(W-L-R),Y=v=>T+(100-v)/100*(H-T-B);
  [0,25,50,75,100].forEach(p=>{const y=Y(p);sv.appendChild(el("line",{x1:L,y1:y,x2:W-R,y2:y,stroke:"var(--line)"}));
    const t=el("text",{x:L-8,y:y+4,fill:"var(--mut)","font-size":11,"text-anchor":"end"});t.textContent=p;sv.appendChild(t);});
  [0,25,50,75,100].forEach(p=>{const x=X(p);const t=el("text",{x,y:H-16,fill:"var(--mut)","font-size":11,"text-anchor":"middle"});t.textContent=p;sv.appendChild(t);});
  sv.appendChild(el("text",{x:(L+W-R)/2,y:H-2,fill:"var(--mut)","font-size":11,"text-anchor":"middle"})).textContent="novelty prior";
  const yl=el("text",{x:14,y:H/2,fill:"var(--mut)","font-size":11,"text-anchor":"middle",transform:`rotate(-90 14 ${H/2})`});yl.textContent="AF capacity prior";sv.appendChild(yl);
  const seen={};
  rows.forEach(d=>{if(d.af==null||d.novelty==null)return;const key=d.af+","+d.novelty;const n=seen[key]=(seen[key]||0)+1;
    const ang=n*2.4,rad=n>1?3+Math.sqrt(n):0;const jx=Math.cos(ang)*rad,jy=Math.sin(ang)*rad;
    const c=el("circle",{cx:X(d.novelty)+jx,cy:Y(d.af)+jy,r:d.tier=="EXCEPTIONAL"||d.tier=="HIGH"?6:4.5,
      fill:TIERC[d.tier]||"var(--omit)",opacity:.82,stroke:"var(--bg)","stroke-width":.8,cursor:"pointer"});
    c.addEventListener("mousemove",ev=>tip(ev,d));c.addEventListener("mouseleave",()=>tip(null,null));sv.appendChild(c);});
  const L2=[["TOP","--exc"],["HIGH","--hi"],["MEDIUM","--med"],["WATCHLIST","--wat"],["OMIT","--omit"]];
  $("leg").innerHTML=L2.map(([n,v])=>`<span><i class="dot" style="background:var(${v})"></i>${n}</span>`).join("");}
function render(){
  const rows=filtered().slice().sort(cmp);
  $("count").textContent=`${rows.length} of ${DATA.length} leads`;
  kpis(rows);scatter(rows);
  const tb=$("tb");tb.innerHTML="";
  rows.forEach(d=>{const tr=document.createElement("tr");
    const afw=d.af==null?0:Math.max(0,d.af)/100*46;
    const lean=d.lean_kind?`<span class="lean-${d.lean_kind}">${esc(d.lean_kind)}</span>`:'<span class="mut">—</span>';
    const om=d.overmerge=="over-merged"?'<span class="om">over-merged</span>':(d.overmerge=="coherent-hybrid"?'<span class="om-coherent">coherent</span>':'<span class="mut">—</span>');
    const tier=`<span class="chip t-${d.tier||'none'}">${esc(d.tier||'—')}</span>`;
    tr.innerHTML=`<td class="num rk">${d.af_rank}</td>`+
      `<td>${esc(d.strain)}${d.audit_only?'<span class="audit">AUDIT</span>':''}</td>`+
      `<td class="mono">${esc(d.bgc)}</td>`+
      `<td>${esc(d.pclass)}${d.housekeeping?' <span class="mut">·hk</span>':''}</td>`+
      `<td class="num">${num(d.af)}<span class="afbar" style="width:${afw}px"></span></td>`+
      `<td class="num">${num(d.ab)}</td>`+
      `<td class="num">${num(d.novelty)}</td>`+
      `<td>${tier}</td>`+
      `<td>${lean}</td>`+
      `<td>${om}</td>`+
      `<td class="mut">${esc(d.mibig)}</td>`;
    tr.title=d.lean_text||"";
    tr.addEventListener("mousemove",ev=>tip(ev,d));tr.addEventListener("mouseleave",()=>tip(null,null));
    tb.appendChild(tr);});}
function init(){
  $("sub").textContent=`${META.n_leads} BGC leads across ${META.n_strains} AS strains · engine ${META.engine} · built ${META.built} · governed exclusions applied`;
  fillSelect("fclass",classes(),"all classes");fillSelect("ftier",["TOP","HIGH","MEDIUM","WATCHLIST","OMIT"],"all tiers");
  fillSelect("flean",leans(),"all leans");
  $("minaf").oninput=e=>{state.minaf=+e.target.value;$("minafv").textContent=e.target.value;render();};
  $("fclass").onchange=e=>{state.cls=e.target.value;render();};
  $("ftier").onchange=e=>{state.tier=e.target.value;render();};
  $("flean").onchange=e=>{state.lean=e.target.value;render();};
  $("hideom").onchange=e=>{state.hideom=e.target.checked;render();};
  $("hidehk").onchange=e=>{state.hidehk=e.target.checked;render();};
  $("hideaudit").onchange=e=>{state.hideaudit=e.target.checked;render();};
  document.querySelectorAll("thead th").forEach(th=>th.onclick=()=>{const k=th.dataset.k;
    if(state.sort==k)state.dir*=-1;else{state.sort=k;state.dir=(k=="strain"||k=="bgc"||k=="pclass"||k=="mibig"||k=="lean_kind"||k=="overmerge")?1:-1;}
    if(k=="af_rank")state.dir=1;render();});
  $("foot").innerHTML=`<b>Claim-safety.</b> AF is a class-level <b>CAPACITY prior</b> derived from mechanism and domain content — `+
    `it is <b>not</b> measured antifungal activity. Measured non-inhibition is assay-specific and never proves incapacity. `+
    `MIBiG/KCB anchors are similarity comparators, not identity; ⚡ tiers are triage priors. <b>Judgment is deferred</b> to Sapote. `+
    `AF is the primary discovery target (bee/wasp actinomycetes vs fungal pathogens); AB shown for context. `+
    `Governed exclusions applied; audit-only strains flagged.`;
  render();}
init();
</script></body></html>"""


def build(outdir, master_csv=None, master_dir=None, overmerge_tsv=None,
          engine="1.9.119 / v9.7.339"):
    """Build the AF lead-board HTML. Returns (path, leads, meta).

    master_csv    : SAPOTE_PER_BGC_MASTER_all_AS.csv (default: under strain_data).
    master_dir    : strain_data root (for per-strain codex cards).
    overmerge_tsv : OVERMERGE_REGISTER_GBK.tsv (optional; missing = no over-merge flags).
    """
    if master_dir is None:
        master_dir = _master_dir()
    if master_csv is None:
        master_csv = os.path.join(master_dir, "SAPOTE_PER_BGC_MASTER_all_AS.csv")
    if overmerge_tsv is None:
        overmerge_tsv = os.path.join(master_dir, "_OVERMERGE_MODULE",
                                     "OVERMERGE_REGISTER_GBK.tsv")
    leads = build_leads(master_csv, master_dir, overmerge_tsv)
    meta = {
        "n_leads": len(leads),
        "n_strains": len(set(r["strain"] for r in leads)),
        "engine": engine,
        "built": datetime.date.today().isoformat(),
    }
    os.makedirs(outdir, exist_ok=True)
    title = "Cohort AF lead-board — Sapote-Mamey"
    h1 = "Cohort antifungal (AF) capacity lead-board"
    html_out = (TEMPLATE
                .replace("__PAYLOAD__", json.dumps(leads, separators=(",", ":")).replace("</","<\\/").replace("<!--","<\\!--"))
                .replace("__META__", json.dumps(meta, separators=(",", ":")).replace("</","<\\/").replace("<!--","<\\!--"))
                .replace("__TITLE__", html.escape(title))
                .replace("__H1__", html.escape(h1)))
    outp = os.path.join(outdir, "AF_leadboard_cohort.html")
    with open(outp, "w", encoding="utf-8") as f:
        f.write(html_out)
    return outp, leads, meta


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=None,
                    help="Output directory (default: _AF_LEADBOARD_MODULE)")
    ap.add_argument("--master-csv", default=None,
                    help="SAPOTE_PER_BGC_MASTER_all_AS.csv (default: under strain_data)")
    ap.add_argument("--root", default=ROOT_DEFAULT,
                    help="Deliverables-workspace root")
    a = ap.parse_args()
    master_dir = _master_dir(a.root)
    outdir = a.out or module_dir("_AF_LEADBOARD_MODULE", a.root)
    outp, leads, meta = build(outdir, master_csv=a.master_csv, master_dir=master_dir)
    ranked = [r for r in leads if not r["audit_only"]]
    emit(f"AF lead-board: {meta['n_leads']} leads across {meta['n_strains']} strains -> {outp}", "Top 10 AF leads:", sep="\n")
    for r in ranked[:10]:
        emit(f"  {r['af_rank']:>3}. {r['strain']:<8} {r['bgc']:<7} AF={r['af'] or '-':<5} "
              f"nov={r['novelty'] or '-':<5} tier={r['tier'] or '-':<11} "
              f"{r['pclass'][:22]:<22} lean={r['lean_kind'] or '-'}")


if __name__ == "__main__":
    main()
