#!/usr/bin/env python3
"""bigscape_matrix_widget.py — self-contained, theme-aware strain x GCF-family sharing matrix
for the Sapote-Mamey BiG-SCAPE cohort deliverable (graduated into the engine, v9.7.349x).

A cohort heatmap: rows = gene-cluster families (GCFs), columns = query-cohort strains
(AS + SID), cell = number of member BGCs that strain contributes to the family. A right-hand
"Type refs" badge counts named type-strain reference members. AS-private families (no Type and
no SID reference member) are flagged — these are the novelty leads.

Interactive: sort (members / #strains / family id / private-first), filter to AS-private only,
min-members threshold, and free-text search over family id / product / class. Only non-empty
cells are drawn (sparse), so the whole cohort renders in one scrollable SVG.

Data source: full_cohort.db (BiG-SCAPE 2.x SQLite; run full_cohort_AS_Type_SID_2026-07-18).
Stdlib-only; no network, no external assets; opens over file://.

Claim-safety: GCF membership = BiG-SCAPE sequence-similarity clustering, class-level only.
"AS-private" = no Type/SID reference member at this cutoff (a novelty prior, not proof).
Type/SID members are similarity anchors, not identity calls. Judgment deferred.

Usage:
  python bigscape_matrix_widget.py                    # cutoff 0.3, min 2 members
  python bigscape_matrix_widget.py --cutoff 0.5 --min-members 3 --outdir DIR
  python bigscape_matrix_widget.py --db /path/to/full_cohort.db --outdir DIR
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, json, os, sys, collections, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _bigscape_data import DB_DEFAULT, family_members  # noqa: E402
import sqlite3  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

TEMPLATE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title>
<style>
:root{--bg:#0e0f12;--panel:#16181d;--line:#262a31;--tx:#e7e9ee;--mut:#8b91a0;--acc:#5b8def;--track:#20242b;--grid:#1c2028;--as:#e0724d;--sid:#43a08a;--priv:#d15f9a}
:root[data-theme=light]{--bg:#f6f7f9;--panel:#ffffff;--line:#e2e5ea;--tx:#1b1e24;--mut:#5c6470;--acc:#2f6fe0;--track:#eef1f5;--grid:#eceff3}
@media(prefers-color-scheme:light){:root:not([data-theme=dark]){--bg:#f6f7f9;--panel:#ffffff;--line:#e2e5ea;--tx:#1b1e24;--mut:#5c6470;--acc:#2f6fe0;--track:#eef1f5;--grid:#eceff3}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1500px;margin:0 auto;padding:18px}
h1{font-size:15px;font-weight:600;margin:0 0 2px}.sub{color:var(--mut);font-size:12px;margin-bottom:12px}
.bar{display:flex;flex-wrap:wrap;gap:14px;align-items:center;margin-bottom:10px}
.chk{display:inline-flex;align-items:center;gap:6px;color:var(--mut);font-size:12.5px;cursor:pointer;user-select:none}
select,input{background:var(--track);color:var(--tx);border:1px solid var(--line);border-radius:8px;padding:6px 10px;font-size:13px}
input[type=number]{width:64px}input[type=search]{min-width:180px}
.toggle{margin-left:auto;font-size:12px;color:var(--mut);cursor:pointer;border:1px solid var(--line);border-radius:8px;padding:5px 9px;background:var(--track)}
.stats{display:flex;flex-wrap:wrap;gap:18px;margin:6px 0 12px;color:var(--mut);font-size:12px}
.stats b{color:var(--tx);font-weight:600}
.scroll{overflow:auto;max-height:74vh;border:1px solid var(--line);border-radius:10px;background:var(--panel)}
svg{display:block}
.legend{display:flex;flex-wrap:wrap;gap:16px;margin-top:10px;color:var(--mut);font-size:12px}
.legend span{display:inline-flex;align-items:center;gap:6px}.legend i{width:12px;height:12px;border-radius:3px;display:inline-block}
.foot{color:var(--mut);font-size:11.5px;margin-top:14px;border-top:1px solid var(--line);padding-top:10px}
#tip{position:fixed;pointer-events:none;background:var(--track);border:1px solid var(--line);border-radius:8px;padding:8px 10px;font-size:12px;max-width:320px;opacity:0;transition:opacity .08s;z-index:9;box-shadow:0 6px 20px rgba(0,0,0,.35)}
#tip b{color:var(--tx)}#tip .m{color:var(--mut)}
</style></head><body><div class="wrap">
<h1 id="ttl"></h1><div class="sub" id="sub"></div>
<div class="bar">
  <label class="chk">sort
    <select id="sort">
      <option value="members">members (desc)</option>
      <option value="strains">strains (desc)</option>
      <option value="private">AS-private first</option>
      <option value="fid">family id</option>
    </select></label>
  <label class="chk"><input type="checkbox" id="privonly"> AS-private only</label>
  <label class="chk">min members <input type="number" id="minm" value="2" min="1"></label>
  <label class="chk"><input type="search" id="q" placeholder="search id / product / class"></label>
  <span class="toggle" id="themebtn">theme</span>
</div>
<div class="stats" id="stats"></div>
<div class="scroll"><svg id="hm" preserveAspectRatio="xMinYMin meet"></svg></div>
<div class="legend" id="leg"></div>
<div class="foot" id="foot"></div></div><div id="tip"></div>
<script>
const DATA=__PAYLOAD__;const NS="http://www.w3.org/2000/svg";
const $=i=>document.getElementById(i);
const esc=s=>(s==null?"":String(s)).replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));/*v9.7.409 export-injection: escape attacker text before innerHTML*/
const el=(t,a,txt)=>{const e=document.createElementNS(NS,t);for(const k in(a||{}))e.setAttribute(k,a[k]);if(txt!=null)e.textContent=txt;return e;};
const ST=DATA.strains;let state={sort:"members",privonly:0,minm:2,q:""};
function cellColor(cls,cnt){const base=cls=="AS"?[224,114,77]:[67,160,138];const a=Math.min(1,.42+.20*cnt);return `rgba(${base[0]},${base[1]},${base[2]},${a})`;}
function filtered(){const q=state.q.trim().toLowerCase();
  let f=DATA.families.filter(fm=>fm.n>=state.minm);
  if(state.privonly)f=f.filter(fm=>fm.private);
  if(q)f=f.filter(fm=>(""+fm.id).includes(q)||fm.label.toLowerCase().includes(q)||fm.cls.toLowerCase().includes(q));
  const s=state.sort;
  f.sort((a,b)=> s=="members"?b.n-a.n : s=="strains"?b.ns-a.ns : s=="fid"?a.id-b.id :
    (b.private-a.private)||(b.n-a.n));
  return f;
}
function tip(ev,html){const t=$("tip");if(!html){t.style.opacity=0;return;}t.innerHTML=html;
  t.style.left=Math.min(ev.clientX+14,window.innerWidth-330)+"px";t.style.top=(ev.clientY+14)+"px";t.style.opacity=1;}
function draw(){
  const fams=filtered();const sv=$("hm");sv.innerHTML="";
  const LW=250,cw=13,rh=13,top=118,rightW=60;const nCols=ST.length;
  const W=LW+nCols*cw+rightW+16,H=top+fams.length*rh+14;
  sv.setAttribute("viewBox",`0 0 ${W} ${H}`);sv.setAttribute("width",W);sv.setAttribute("height",H);
  // class band + column headers (rotated)
  let firstSID=ST.findIndex(s=>s.cls=="SID");if(firstSID<0)firstSID=ST.length;
  sv.appendChild(el("rect",{x:LW,y:top-16,width:firstSID*cw,height:4,fill:"var(--as)",opacity:.8}));
  sv.appendChild(el("rect",{x:LW+firstSID*cw,y:top-16,width:(nCols-firstSID)*cw,height:4,fill:"var(--sid)",opacity:.8}));
  sv.appendChild(el("text",{x:LW+2,y:top-22,fill:"var(--as)","font-size":11,"font-weight":600},`AS query (${firstSID})`));
  sv.appendChild(el("text",{x:LW+firstSID*cw+2,y:top-22,fill:"var(--sid)","font-size":11,"font-weight":600},`SID query (${nCols-firstSID})`));
  sv.appendChild(el("text",{x:LW+nCols*cw+6,y:top-6,fill:"var(--mut)","font-size":10},"Type refs"));
  ST.forEach((s,i)=>{const x=LW+i*cw+cw/2;const g=el("text",{x,y:top-20,fill:"var(--mut)","font-size":9,transform:`rotate(-90 ${x} ${top-20})`,"text-anchor":"start"},s.id);sv.appendChild(g);});
  // rows
  fams.forEach((fm,r)=>{const y=top+r*rh;
    if(r%2)sv.appendChild(el("rect",{x:0,y,width:W,height:rh,fill:"var(--grid)",opacity:.5}));
    // label
    const tag=fm.private?" ◆":"";
    const lab=el("text",{x:8,y:y+10,fill:fm.private?"var(--priv)":"var(--tx)","font-size":10},`GCF ${fm.id} · ${fm.label}${tag}`);
    lab.style.cursor="default";sv.appendChild(lab);
    // cells (sparse)
    for(const ci in fm.cells){const i=+ci,cnt=fm.cells[ci];const x=LW+i*cw;
      const rect=el("rect",{x:x+1,y:y+1,width:cw-2,height:rh-2,rx:2,fill:cellColor(ST[i].cls,cnt),cursor:"pointer"});
      rect.addEventListener("mousemove",ev=>tip(ev,`<b>${esc(ST[i].id)}</b> (${ST[i].cls}) × <b>GCF ${fm.id}</b><br><span class="m">${esc(fm.label)}</span><br>${cnt} member BGC${cnt>1?"s":""}`));
      rect.addEventListener("mouseleave",()=>tip(null));sv.appendChild(rect);}
    // type refs badge
    if(fm.type_n){const x=LW+nCols*cw+6;sv.appendChild(el("rect",{x,y:y+2,width:rightW-12,height:rh-4,rx:3,fill:"var(--mut)",opacity:.22}));
      sv.appendChild(el("text",{x:x+(rightW-12)/2,y:y+10,fill:"var(--mut)","font-size":9,"text-anchor":"middle"},`${fm.type_n} type`));}
    // whole-row hover
    const hit=el("rect",{x:0,y,width:LW,height:rh,fill:"transparent",cursor:"default"});
    hit.addEventListener("mousemove",ev=>tip(ev,`<b>GCF ${fm.id}</b> — ${esc(fm.label)}<br><span class="m">${fm.n} members · ${fm.ns} strains · AS ${fm.as_n} / SID ${fm.sid_n} / Type ${fm.type_n}</span>${fm.private?'<br><span style="color:var(--priv)">AS-private (no Type/SID reference)</span>':''}`));
    hit.addEventListener("mouseleave",()=>tip(null));sv.appendChild(hit);
  });
  $("stats").innerHTML=`showing <b>${fams.length}</b> families · <b>${fams.filter(f=>f.private).length}</b> AS-private in view · `+
    `cohort AS-private total <b>${DATA.n_private}</b> · families ≥2 members <b>${DATA.n_ge2}</b>`;
}
function init(){
  $("ttl").textContent="Strain × GCF-family sharing matrix — AS + SID + Type cohort";
  $("sub").innerHTML=`${DATA.families.length} families · ${ST.length} query strains (AS+SID) · `+
    `BiG-SCAPE run ${esc(DATA.run)} · cutoff c${DATA.cutoff}`;
  ["sort"].forEach(id=>$(id).onchange=e=>{state.sort=e.target.value;draw();});
  $("privonly").onchange=e=>{state.privonly=e.target.checked?1:0;draw();};
  $("minm").oninput=e=>{state.minm=Math.max(1,+e.target.value||1);draw();};
  $("q").oninput=e=>{state.q=e.target.value;draw();};
  $("themebtn").onclick=()=>{const rt=document.documentElement;const cur=rt.getAttribute("data-theme");
    const isLight=cur?cur=="light":matchMedia("(prefers-color-scheme:light)").matches;rt.setAttribute("data-theme",isLight?"dark":"light");draw();};
  const leg=$("leg");
  [["var(--as)","AS query strain member"],["var(--sid)","SID query strain member"],["var(--priv)","◆ AS-private family (novelty lead)"]].forEach(([c,t])=>{
    const s=document.createElement("span");s.innerHTML=`<i style="background:${c}"></i>${t}`;leg.appendChild(s);});
  const s=document.createElement("span");s.innerHTML=`<i style="background:var(--mut);opacity:.4"></i>Type reference members (right badge)`;leg.appendChild(s);
  $("foot").textContent="Cell colour intensity = member BGC count. GCF membership = BiG-SCAPE sequence-similarity clustering, "+
    "class-level only. AS-private = no Type/SID reference member fell in the family at this cutoff — a novelty prior, "+
    "not proof; a family may still match a characterised cluster below the clustering threshold. Type/SID members are "+
    "similarity anchors, not identity. Judgment deferred.";
  draw();
}
init();
</script></body></html>"""


def build_payload(con, cutoff=0.3):
    """Read the cohort DB and return the JSON-serialisable matrix payload dict."""
    run_label = con.execute("select label from run limit 1").fetchone()[0]
    fam = family_members(con, cutoff)

    # query-cohort strain columns: AS then SID, ordered
    as_strains, sid_strains = set(), set()
    for members in fam.values():
        for m in members:
            if m["cls"] == "AS":
                as_strains.add(m["strain"])
            elif m["cls"] == "SID":
                sid_strains.add(m["strain"])

    def num_key(s):
        return int(re.sub(r"\D", "", s) or 0)

    cols = ([{"id": s, "cls": "AS"} for s in sorted(as_strains, key=num_key)] +
            [{"id": s, "cls": "SID"} for s in sorted(sid_strains, key=num_key)])
    col_idx = {c["id"]: i for i, c in enumerate(cols)}

    families = []
    n_private = 0
    for fid, members in fam.items():
        cells = collections.Counter()
        cls_count = collections.Counter()
        strains = set()
        for m in members:
            cls_count[m["cls"]] += 1
            strains.add((m["cls"], m["strain"]))
            if m["cls"] in ("AS", "SID"):
                cells[col_idx[m["strain"]]] += 1
        as_n = cls_count.get("AS", 0)
        sid_n = cls_count.get("SID", 0)
        type_n = cls_count.get("Type", 0)
        mibig_n = cls_count.get("MIBiG", 0)
        # A family containing references is not cohort-exclusive. Similarity is not identity.
        private = as_n > 0 and all(m["cls"] == "AS" for m in members)
        if private:
            n_private += 1
        prods = collections.Counter(m["product"] for m in members)
        label = prods.most_common(1)[0][0] if prods else "?"
        families.append(dict(id=fid, label=label, n=len(members), ns=len(strains),
                             as_n=as_n, sid_n=sid_n, type_n=type_n, mibig_n=mibig_n, private=private,
                             cls=" ".join(sorted({m["cls"] for m in members})),
                             cells={str(k): v for k, v in cells.items()}))

    families.sort(key=lambda f: -f["n"])
    n_ge2 = sum(1 for f in families if f["n"] >= 2)
    return dict(run=run_label, cutoff=cutoff, strains=cols, families=families,
                n_private=n_private, n_ge2=n_ge2)


def render_matrix(db=DB_DEFAULT, cutoff=0.3, outdir=HERE, min_members=2):
    """Render the strain x GCF-family matrix HTML. Returns a result dict with the output path.

    Self-contained: writes a single stdlib-generated HTML file (no external assets).
    """
    con = sqlite3.connect(db)
    try:
        payload = build_payload(con, cutoff)
    finally:
        con.close()
    os.makedirs(outdir, exist_ok=True)
    html = (TEMPLATE.replace("__PAYLOAD__", json.dumps(payload, separators=(",", ":")).replace("</","<\\/").replace("<!--","<\\!--"))
                    .replace("__TITLE__", f"Strain x GCF matrix (c{cutoff})"))
    # apply default min-members into the input + initial state
    html = html.replace('id="minm" value="2"', f'id="minm" value="{min_members}"') \
               .replace('let state={sort:"members",privonly:0,minm:2,q:""};',
                        f'let state={{sort:"members",privonly:0,minm:{min_members},q:""}};')
    outp = os.path.join(outdir, f"strain_family_matrix_c{cutoff}.html")
    with open(outp, "w") as fh:
        fh.write(html)
    return dict(path=outp, families=len(payload["families"]),
                strains=len(payload["strains"]), n_private=payload["n_private"],
                run=payload["run"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DB_DEFAULT)
    ap.add_argument("--cutoff", type=float, default=0.3)
    ap.add_argument("--min-members", type=int, default=2,
                    help="default value of the in-widget min-members filter")
    ap.add_argument("--outdir", default=HERE)
    a = ap.parse_args()
    res = render_matrix(db=a.db, cutoff=a.cutoff, outdir=a.outdir, min_members=a.min_members)
    emit(f"{res['families']} families, {res['strains']} query strains (AS+SID), "
          f"{res['n_private']} AS-private -> {res['path']}")


if __name__ == "__main__":
    main()
