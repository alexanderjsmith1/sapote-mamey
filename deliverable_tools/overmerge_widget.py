#!/usr/bin/env python3
"""overmerge_widget.py — self-contained over-merge inspector widget set for antiSMASH
regions that fuse several chemically distinct protoclusters into one region (graduated
into the engine as a first-class deliverable tool, v9.7.349x candidate).

antiSMASH groups nearby protoclusters into one *region* (candidate cluster). When the
neighbours are genomically adjacent but chemically distinct systems, a single *union*
score over the pooled product set over-states the strongest single system's capacity —
the region reads "hotter" than any real biosynthetic unit inside it. This tool reads the
canonical over-merge register, and for every region flagged ``OVER_MERGED`` it emits one
self-contained HTML inspector (genomic axis, one track per protocluster, genes coloured by
protocluster membership by coordinate, overlap genes on both tracks, union-vs-de-inflated
score) plus a sortable ``index.html`` ranked by AB inflation delta (union - de-inflated).

Scores are the Mamey auto-floor capacity priors (``score_keywords`` over
``AB_/AF_/NOVELTY_KEYWORDS`` from ``mamey.scoring``), NOT final judgments — this is the
only engine coupling, and it is read-only (it recomputes priors for display; it never
writes any score, board, or sealed output).

CLAIM SAFETY: class-level capacity hypotheses only. Products are antiSMASH class labels,
not compound identities; the de-inflated value is the strongest single protocluster's
prior, not a proven pathway split; comparators are similarity anchors, not identity;
judgment deferred.

Usage:
  python overmerge_widget.py                              # documented defaults
  python overmerge_widget.py --register REG.tsv --root DIR --out DIR
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, glob, html, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _widget_paths import ROOT_DEFAULT, master_dir, module_dir  # noqa: E402

# Import the engine's auto-floor keyword scorers. deliverable_tools/ sits next to the
# mamey package in the source tree; make sure the package root is importable when this
# module is run as a standalone script (the CLI path already has mamey imported).
_ENGINE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ENGINE_ROOT not in sys.path:
    sys.path.insert(0, _ENGINE_ROOT)
from mamey.scoring import (  # noqa: E402
    score_keywords, AB_KEYWORDS, AF_KEYWORDS, NOVELTY_KEYWORDS)

PALETTE = ['#6aa9ff', '#ff9e6a', '#7fd18b', '#c98bff', '#ffd166', '#ef6f6f']

# Default register: the canonical GBK-resolved over-merge register shipped in the module.
DEFAULT_MODULE = module_dir("_OVERMERGE_MODULE")
DEFAULT_REGISTER = os.path.join(DEFAULT_MODULE, "OVERMERGE_REGISTER_GBK.tsv")


def coords(s):
    ns = [int(x) for x in re.findall(r'\d+', s)]
    return (min(ns), max(ns)) if ns else (0, 0)


def parse(g):
    t = open(g, encoding='utf-8', errors='ignore').read()
    pcs = []
    for b in re.split(r'(?=^\s{5}protocluster\s)', t, flags=re.M):
        if not re.match(r'^\s{5}protocluster\s', b):
            continue
        a, z = coords(re.match(r'^\s{5}protocluster\s+(\S+)', b).group(1))
        prod = re.search(r'/product="([^"]+)"', b)
        num = re.search(r'/protocluster_number="?(\d+)', b)
        pcs.append(dict(num=int(num.group(1)) if num else len(pcs) + 1,
                        product=prod.group(1) if prod else '?', start=a, end=z))
    kinds = sorted(set(re.findall(r'/kind="([^"]+)"', t)))
    cds = []
    for b in re.split(r'(?=^\s{5}CDS\s)', t, flags=re.M):
        if not re.match(r'^\s{5}CDS\s', b):
            continue
        loc = re.match(r'^\s{5}CDS\s+(\S+)', b).group(1)
        a, z = coords(loc)
        lt = re.search(r'/locus_tag="([^"]+)"', b)
        kind = re.search(r'/gene_kind="([^"]+)"', b)
        gf = re.search(r'/gene_functions="([^"\n]+)', b) or re.search(r'/product="([^"\n]+)', b)
        cds.append(dict(lt=lt.group(1) if lt else '?', start=a, end=z,
                        strand='-' if 'complement' in loc else '+',
                        kind=kind.group(1) if kind else '',
                        role=(gf.group(1)[:48] if gf else '')))
    return pcs, kinds, cds


def score(prod):
    return dict(ab=round(25 + score_keywords(prod.lower(), AB_KEYWORDS), 1),
                af=round(20 + score_keywords(prod.lower(), AF_KEYWORDS), 1),
                nov=round(30 + score_keywords(prod.lower(), NOVELTY_KEYWORDS), 1))


TEMPLATE = r"""<!doctype html><meta charset="utf-8"><title>__TITLE__</title>
<style>
:root{--bg:#0f1216;--fg:#e8eef6;--mut:#95a3b3;--pan:#161b22;--line:#232a33}
@media (prefers-color-scheme:light){:root{--bg:#f7f9fc;--fg:#131820;--mut:#5a6672;--pan:#fff;--line:#e4e9f0}}
:root[data-theme=light]{--bg:#f7f9fc;--fg:#131820;--mut:#5a6672;--pan:#fff;--line:#e4e9f0}
:root[data-theme=dark]{--bg:#0f1216;--fg:#e8eef6;--mut:#95a3b3;--pan:#161b22;--line:#232a33}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:22px}h1{font-size:20px;margin:0 0 2px}.sub{color:var(--mut);margin-bottom:14px}
.back{display:inline-block;margin-bottom:10px;color:var(--mut);font-size:12px;text-decoration:none}.back:hover{color:var(--fg)}
.chips{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0}.chip{background:var(--pan);border:1px solid var(--line);border-radius:20px;padding:5px 12px;font-size:12px}
.chip b{color:var(--fg)}.warn{border-color:#ef6f6f;color:#ef6f6f}
.scorebar{display:flex;gap:18px;align-items:center;background:var(--pan);border:1px solid var(--line);border-radius:12px;padding:12px 16px;margin:10px 0}
.sc{font-size:13px}.sc b{font-size:20px}.arrow{color:var(--mut);font-size:22px}.down{color:#7fd18b}
svg{width:100%;display:block;background:var(--pan);border:1px solid var(--line);border-radius:12px;margin-top:8px}
.legend{display:flex;gap:16px;flex-wrap:wrap;margin-top:8px;color:var(--mut);font-size:12px}.legend i{width:12px;height:12px;border-radius:3px;display:inline-block;margin-right:5px;vertical-align:-1px}
table{width:100%;border-collapse:collapse;margin-top:14px;font-size:13px}th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line)}th{color:var(--mut);font-weight:600}
.foot{color:var(--mut);font-size:11px;margin-top:16px}
</style><div class="wrap">
<a class="back" href="../index.html">&larr; over-merge module index</a>
<h1 id="ttl"></h1><div class="sub" id="sub"></div>
<div class="chips" id="chips"></div>
<div class="scorebar" id="score"></div>
<h2 style="font-size:15px;margin:16px 0 4px">Region &rarr; protocluster tracks</h2>
<svg id="map" viewBox="0 0 1140 220" preserveAspectRatio="xMidYMid meet"></svg>
<div class="legend" id="leg"></div>
<table id="tbl"></table>
<div class="foot" id="foot"></div></div>
<script>
const D=__DATA__, PAL=__PAL__, NS="http://www.w3.org/2000/svg";
const $=i=>document.getElementById(i);
const esc=s=>(s==null?"":String(s)).replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));/*v9.7.409 export-injection: escape attacker text before innerHTML*/
$("ttl").textContent=`${D.strain} — Over-merge inspector`;
$("sub").textContent=`${D.node} · ${D.region} · ${D.n_genes} genes · ${D.protoclusters.length} protoclusters · cand_cluster kind: ${D.kinds.join(", ")}`;
$("chips").innerHTML=`<span class="chip warn"><b>${esc(D.verdict)}</b></span>`+D.protoclusters.map((p,i)=>`<span class="chip"><i style="color:${PAL[i%6]}">■</i> p${p.num}: <b>${esc(p.product)}</b> · ${p.ngenes} genes · ${((p.end-p.start)/1000).toFixed(0)} kb</span>`).join("");
$("score").innerHTML=`<div class="sc">Union (inflated): AB <b>${D.union.ab}</b> · AF ${D.union.af} · nov ${D.union.nov}</div>`
 +`<div class="arrow">→</div><div class="sc down">De-inflated (strongest protocluster: ${D.deinflated.by}): AB <b>${D.deinflated.ab}</b> · AF ${D.deinflated.af} · nov ${D.deinflated.nov}</div>`;
const W=1140,H=220,padL=30,padR=30,trkY0=54,trkH=30,gap=16;
const sx=x=>padL+(x-D.lo)/(D.hi-D.lo)*(W-padL-padR);
const svg=$("map");
D.protoclusters.forEach((p,i)=>{
  const y=trkY0+i*(trkH+gap);
  const r=document.createElementNS(NS,"rect");r.setAttribute("x",sx(p.start));r.setAttribute("y",y);r.setAttribute("width",sx(p.end)-sx(p.start));r.setAttribute("height",trkH);r.setAttribute("rx",6);r.setAttribute("fill",PAL[i%6]);r.setAttribute("opacity",.16);r.setAttribute("stroke",PAL[i%6]);svg.appendChild(r);
  const lbl=document.createElementNS(NS,"text");lbl.setAttribute("x",sx(p.start)+6);lbl.setAttribute("y",y-4);lbl.setAttribute("fill",PAL[i%6]);lbl.setAttribute("font-size","12");lbl.setAttribute("font-weight","600");lbl.textContent=`p${p.num} ${p.product}`;svg.appendChild(lbl);
});
D.genes.forEach(g=>{
  g.pcs.forEach(pn=>{
    const idx=D.protoclusters.findIndex(p=>p.num===pn); if(idx<0)return;
    const y=trkY0+idx*(trkH+gap);const x=sx(g.start),w=Math.max(2,sx(g.end)-sx(g.start));
    const rect=document.createElementNS(NS,"rect");rect.setAttribute("x",x);rect.setAttribute("y",y+8);rect.setAttribute("width",w);rect.setAttribute("height",trkH-16);rect.setAttribute("fill",PAL[idx%6]);rect.setAttribute("opacity",g.pcs.length>1?.55:.9);
    const core=(g.kind||"").toLowerCase().startsWith("biosynthetic");if(core){rect.setAttribute("stroke","#fff");rect.setAttribute("stroke-width",".7")}
    const tt=document.createElementNS(NS,"title");tt.textContent=`${g.lt} · ${g.strand} · ${g.kind||"other"}${g.pcs.length>1?" · OVERLAP":""}\n${g.role}`;rect.appendChild(tt);svg.appendChild(rect);
  });
});
const ax=document.createElementNS(NS,"line");ax.setAttribute("x1",padL);ax.setAttribute("x2",W-padR);ax.setAttribute("y1",H-24);ax.setAttribute("y2",H-24);ax.setAttribute("stroke","var(--line)");svg.appendChild(ax);
[D.lo,Math.round((D.lo+D.hi)/2),D.hi].forEach(t=>{const tx=document.createElementNS(NS,"text");tx.setAttribute("x",sx(t));tx.setAttribute("y",H-8);tx.setAttribute("fill","var(--mut)");tx.setAttribute("font-size","11");tx.setAttribute("text-anchor","middle");tx.textContent=(t/1000).toFixed(0)+" kb";svg.appendChild(tx)});
$("leg").innerHTML=D.protoclusters.map((p,i)=>`<span><i style="background:${PAL[i%6]}"></i>p${p.num} ${esc(p.product)}</span>`).join("")+`<span><i style="background:#888;opacity:.55"></i>overlap gene (both)</span><span>white outline = biosynthetic core</span>`;
$("tbl").innerHTML=`<tr><th>protocluster</th><th>product</th><th>span</th><th>genes</th><th>standalone AB</th><th>AF</th><th>novelty</th></tr>`+
 D.protoclusters.map(p=>`<tr><td>p${p.num}</td><td><b>${esc(p.product)}</b></td><td>${(p.start/1000).toFixed(0)}–${(p.end/1000).toFixed(0)} kb</td><td>${p.ngenes}</td><td>${p.ab}</td><td>${p.af}</td><td>${p.nov}</td></tr>`).join("");
$("foot").textContent="Over-merge inspector. Protocluster bands + gene assignment from the antiSMASH region GBK by coordinate. Union score is the merged-region prior; de-inflated = strongest single protocluster (RFC v9.7.349x). Capacity-level class hypotheses; comparators are similarity anchors, not identity; judgment deferred.";
</script>"""


def build_widget(strain, node, region, master, widgets_dir):
    """Render one over-merge inspector HTML for a flagged region; return a summary dict."""
    # GBK basenames vary: "AS-XXX_NODE..", "AS-XXX (1)_NODE..", "AS-XXX_new_NODE..".
    # Accept any separator/tag between strain and NODE, but reject digit-collisions.
    cand = glob.glob(f'{master}/{strain}/bigscape_regions/{strain}*{node}_*{region}.gbk')
    hits = [h for h in cand
            if not os.path.basename(h)[len(strain):len(strain) + 1].isdigit()]
    if not hits:
        raise FileNotFoundError(f'no GBK for {strain} {node} {region}')
    g = sorted(hits)[0]
    pcs, kinds, cds = parse(g)
    if not cds:
        raise ValueError('no CDS parsed')
    lo = min(c['start'] for c in cds)
    hi = max(c['end'] for c in cds)
    if hi == lo:
        hi = lo + 1
    for c in cds:
        mid = (c['start'] + c['end']) // 2
        c['pcs'] = [p['num'] for p in pcs if p['start'] - 1 <= mid <= p['end'] + 1] or [0]
    union_prod = ' '.join(sorted({p['product'] for p in pcs}))
    union = score(union_prod)
    per = [dict(num=p['num'], product=p['product'], start=p['start'], end=p['end'],
                ngenes=sum(1 for c in cds if p['num'] in c['pcs']), **score(p['product']))
           for p in pcs]
    deinf = (max(per, key=lambda x: max(x['ab'], x['af'], x['nov'])) if per
             else dict(ab=union['ab'], af=union['af'], nov=union['nov'], product='?'))
    verdict = ('COHERENT_HYBRID (one compound — not split)' if 'chemical_hybrid' in kinds
               else ('OVER-MERGED — COMPOSITE_SEPARABLE' if len(pcs) >= 2 else 'single'))
    DATA = dict(strain=strain, node=node, region=region, lo=lo, hi=hi, kinds=kinds,
                verdict=verdict, protoclusters=per, genes=cds, union=union,
                deinflated=dict(ab=deinf['ab'], af=deinf['af'], nov=deinf['nov'],
                                by=deinf['product']),
                n_genes=len(cds))
    html_out = (TEMPLATE.replace("__TITLE__", f"{strain} over-merge inspector")
                .replace("__DATA__", json.dumps(DATA).replace("</","<\\/").replace("<!--","<\\!--")).replace("__PAL__", json.dumps(PALETTE)))
    fname = f'{strain}_{node}_{region}_overmerge.html'
    os.makedirs(widgets_dir, exist_ok=True)
    open(os.path.join(widgets_dir, fname), 'w').write(html_out)
    return dict(strain=strain, node=node, region=region, fname=fname,
                n_pc=len(pcs), products=[p['product'] for p in pcs], kinds=kinds,
                union_ab=union['ab'], deinf_ab=deinf['ab'], deinf_by=deinf['product'],
                delta=round(union['ab'] - deinf['ab'], 1), n_genes=len(cds))


def write_index(built, skipped, outdir):
    esc = html.escape
    rows_html = []
    for b in built:
        prods = ', '.join(dict.fromkeys(b['products']))  # dedup preserve order
        delta_cls = 'pos' if b['delta'] > 0 else 'zero'
        rows_html.append(
            f"<tr>"
            f"<td class='str'>{esc(b['strain'])}</td>"
            f"<td>{esc(b['bgc'] or '—')}</td>"
            f"<td class='num'>{b['n_pc']}</td>"
            f"<td class='prod'>{esc(prods)}</td>"
            f"<td><span class='v'>{esc(','.join(b['kinds']) or '—')}</span></td>"
            f"<td class='num'>{b['union_ab']} <span class='mut'>&rarr;</span> {b['deinf_ab']}</td>"
            f"<td class='num {delta_cls}'>{b['delta']:+.1f}</td>"
            f"<td><a href='widgets/{esc(b['fname'])}'>inspect &rarr;</a></td>"
            f"</tr>")
    n_strains = len(set(b['strain'] for b in built))
    tbody = '\n'.join(rows_html)
    skip_note = (f"<p class='foot'>{len(skipped)} region(s) skipped (missing/unparseable "
                 f"GBK) — see build_log.txt.</p>" if skipped else "")
    doc = f"""<!doctype html><meta charset="utf-8"><title>Over-merge module — index</title>
<style>
:root{{--bg:#0f1216;--fg:#e8eef6;--mut:#95a3b3;--pan:#161b22;--line:#232a33}}
@media (prefers-color-scheme:light){{:root{{--bg:#f7f9fc;--fg:#131820;--mut:#5a6672;--pan:#fff;--line:#e4e9f0}}}}
:root[data-theme=light]{{--bg:#f7f9fc;--fg:#131820;--mut:#5a6672;--pan:#fff;--line:#e4e9f0}}
:root[data-theme=dark]{{--bg:#0f1216;--fg:#e8eef6;--mut:#95a3b3;--pan:#161b22;--line:#232a33}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}}
.wrap{{max-width:1180px;margin:0 auto;padding:22px}}h1{{font-size:22px;margin:0 0 2px}}.sub{{color:var(--mut);margin-bottom:14px}}
.chips{{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0 18px}}.chip{{background:var(--pan);border:1px solid var(--line);border-radius:20px;padding:5px 12px;font-size:12px}}.chip b{{color:var(--fg)}}
table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top}}
th{{color:var(--mut);font-weight:600;position:sticky;top:0;background:var(--bg)}}
td.num,th.num{{text-align:right;white-space:nowrap}}td.str{{font-weight:600}}td.prod{{color:var(--mut);max-width:340px}}
.v{{font-size:11px;color:var(--mut)}}.mut{{color:var(--mut)}}.pos{{color:#ef6f6f}}.zero{{color:var(--mut)}}
a{{color:#6aa9ff;text-decoration:none}}a:hover{{text-decoration:underline}}
.foot{{color:var(--mut);font-size:11px;margin-top:18px;line-height:1.6}}
tr:hover td{{background:color-mix(in srgb,var(--pan) 60%,transparent)}}
</style><div class="wrap">
<h1>Over-merge module</h1>
<div class="sub">antiSMASH regions flagged OVER_MERGED — merged-region score prior vs de-inflated (strongest single protocluster)</div>
<div class="chips">
 <span class="chip"><b>{len(built)}</b> over-merged regions</span>
 <span class="chip"><b>{n_strains}</b> strains</span>
 <span class="chip">sorted by AB inflation delta (largest first)</span>
</div>
<table>
<thead><tr><th>strain</th><th>BGC</th><th class="num">protoclusters</th><th>products</th><th>cand_cluster kind</th><th class="num">union&rarr;de-inflated AB</th><th class="num">&Delta;AB</th><th>widget</th></tr></thead>
<tbody>
{tbody}
</tbody></table>
{skip_note}
<p class="foot">
<b>Over-merge</b> = one antiSMASH region carrying multiple genomically adjacent but chemically distinct protoclusters, so a single union score over-states the strongest system's capacity. Detector: protocluster_count &gt; 1 with cand_cluster <b>kind</b> in {{neighbouring, interleaved, multi-single}} (a <b>chemical_hybrid</b> kind is coherent — one compound — and is <i>not</i> flagged). &Delta;AB is the drop from the union (inflated) antibacterial prior to the de-inflated prior of the strongest standalone protocluster; a large &Delta; marks the regions where the merged score most over-reads capacity.<br>
Class-level capacity hypotheses only. Products are antiSMASH class labels, not compound identities; comparators are similarity anchors, not identity; judgment deferred to Sapote. Review contract &amp; regeneration steps in README.md.
</p>
</div>"""
    os.makedirs(outdir, exist_ok=True)
    outp = os.path.join(outdir, 'index.html')
    open(outp, 'w').write(doc)
    return outp


def render_overmerge(register=DEFAULT_REGISTER, root=ROOT_DEFAULT, outdir=None):
    """Batch-render every OVER_MERGED region in the register. Returns a result dict.

    register : canonical over-merge register TSV (needs strain/node/region/verdict cols).
    root     : deliverables-workspace root (used to resolve the strain_data GBKs).
    outdir   : output directory (default: the register's _OVERMERGE_MODULE folder).
    """
    master = master_dir(root)
    if outdir is None:
        outdir = os.path.dirname(os.path.abspath(register)) or DEFAULT_MODULE
    widgets_dir = os.path.join(outdir, 'widgets')
    rows = []
    with open(register, newline='') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            r = {k: (v.replace('\r', '').strip() if isinstance(v, str) else v)
                 for k, v in r.items()}
            if r.get('verdict') == 'OVER_MERGED':
                rows.append(r)
    built, skipped = [], []
    for r in rows:
        strain, node, region = r['strain'], r['node'], r['region']
        try:
            rec = build_widget(strain, node, region, master, widgets_dir)
            rec['bgc'] = r.get('bgc', '')
            rec['reg_products'] = r.get('products', '')
            rec['priority'] = r.get('priority', '')
            built.append(rec)
        except Exception as e:
            skipped.append((strain, node, region, str(e)))
    built.sort(key=lambda x: x['delta'], reverse=True)
    index = write_index(built, skipped, outdir)
    log = os.path.join(outdir, 'build_log.txt')
    with open(log, 'w') as f:
        f.write(f'built {len(built)} widgets, skipped {len(skipped)}\n\nSKIPPED:\n')
        for s in skipped:
            f.write('\t'.join(map(str, s)) + '\n')
    return dict(built=len(built), skipped=len(skipped),
                n_strains=len(set(b['strain'] for b in built)),
                index=index, outdir=outdir, skips=skipped)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--register", default=DEFAULT_REGISTER,
                    help="Canonical over-merge register TSV (default: OVERMERGE_REGISTER_GBK.tsv)")
    ap.add_argument("--root", default=ROOT_DEFAULT,
                    help="Deliverables-workspace root (resolves strain_data GBKs)")
    ap.add_argument("--out", default=None,
                    help="Output directory (default: the register's folder)")
    a = ap.parse_args()
    res = render_overmerge(register=a.register, root=a.root, outdir=a.out)
    emit(f"BUILT {res['built']} widgets across {res['n_strains']} strains, "
          f"SKIPPED {res['skipped']} -> {res['index']}")
    for s in res['skips'][:30]:
        emit('  skip:', s)


if __name__ == '__main__':
    main()
