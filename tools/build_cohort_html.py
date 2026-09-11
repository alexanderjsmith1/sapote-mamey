#!/usr/bin/env python3
"""
build_cohort_html.py — one self-contained HTML analysis across sealed Mamey packages.

There is no existing cohort-level HTML tool in the bundle: `generate_bgc_atlas.py` is
single-strain (banked JSON), and `build_master_figure_atlas.py` was retired in the v9.7.213
duplication audit. This renders the whole cohort — every strain, every BGC — into one
offline file with no external assets, no CDN, no network.

It is a VIEW over the sealed packages, not a data product: it reads
`manifest.json` + `*_4_triage_board.csv` in place and never rewrites, summarizes over, or
replaces them. The wheels carry the data; this renders it.

Conventions enforced (docs: SESSION_START_MANIFEST §5):
  * capacity language only — "biosynthetic capacity consistent with", never "produces"
  * KCB / BLASTp = similarity, not identity
  * bioactivity is extract-level only; never a per-BGC phenotype claim
  * every BGC carries its assembly_locator (NODE · region); bare BGC IDs are never shown
  * corrected BGC count = Interior x1 + Edge x1/2 + Full-contig x1/4
  * NAPAA is flagged and excluded from comparative claims (ubiquitous, not informative)
  * taxonomy placeholders are marked, never silently propagated

USAGE
  python tools/build_cohort_html.py --packages-root runs_<date> \
      --out cohort_analysis.html [--placeholder-flags taxonomy_placeholder_flags.json]
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, html, json, os
from datetime import datetime, timezone
from pathlib import Path
from _wbio import atomic_write_text


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)


# BOUNDARY_WEIGHT is the SSOT boundary-weighted "corrected count" (Rule A) used across figures,
# this cohort HTML, the cross-strain workbook, and docs/EXTERNAL_VALIDATION.md. It is a DIFFERENT
# denominator from tools/realistic_bgc_count.py's distinct-loci `Realistic_count` (RG-GMCI merge);
# the two can differ for one strain by design (e.g. RB68: 59.5 here vs 53 there). realistic_bgc_count.py
# keeps a byte-equal copy of this table and now emits both numbers side by side so neither is
# mistaken for "the" corrected count (audit F2 / realistic_count_two_denominators). Keep in sync.
BOUNDARY_WEIGHT = {"Interior": 1.0, "Edge": 0.5, "Full-contig": 0.25}
TIER_ORDER = ["Exceptional", "High", "Medium", "Low", "Inventory"]


def read_triage(pkg: Path):
    hits = sorted(pkg.glob("*_4_triage_board.csv"))
    if not hits:
        return []
    with open(hits[0], newline="", encoding="utf-8", errors="replace") as fh:
        return list(csv.DictReader(fh))


def strain_record(sdir: Path, placeholders: set):
    pkg = sdir / "package"
    man_p = pkg / "manifest.json"
    if not man_p.exists():
        return None
    man = _read_json(man_p, encoding="utf-8")
    rows = read_triage(pkg)
    asm = man.get("assembly", {}) or {}
    counts = {"Interior": 0, "Edge": 0, "Full-contig": 0}
    for r in rows:
        b = (r.get("Boundary") or "").strip()
        if b in counts:
            counts[b] += 1
    corrected = sum(counts[k] * BOUNDARY_WEIGHT[k] for k in counts)
    tiers = {t: 0 for t in TIER_ORDER}
    for r in rows:
        t = (r.get("Lead_tier_auto") or "").strip()
        if t in tiers:
            tiers[t] += 1
    sid = man.get("strain_id") or sdir.name
    return {
        "strain": sid,
        "taxonomy": man.get("taxonomy", "not verified"),
        "taxonomy_placeholder": sid.split("_")[0] in placeholders,
        "source": man.get("source", "not supplied"),
        "status": man.get("package_status", "?"),
        "engine": man.get("workflow_version", "?"),
        "genome_bp": asm.get("genome_bp"),
        "contigs": asm.get("contigs"),
        "n50": asm.get("n50"),
        "gc": asm.get("gc_pct"),
        "raw_bgc": len(rows),
        "corrected": corrected,
        "counts": counts,
        "tiers": tiers,
        "rows": rows,
        "napaa": sum(1 for r in rows if "NAPAA" in (r.get("Products") or "")),
    }


def assembly_tier(rec):
    """Locked thresholds: GOOD >=70% / MODERATE >=45% / POOR >=20% / VERY_POOR <20% interior."""
    n = rec["raw_bgc"] or 1
    pct = 100.0 * rec["counts"]["Interior"] / n
    if pct >= 70: t = "GOOD"
    elif pct >= 45: t = "MODERATE"
    elif pct >= 20: t = "POOR"
    else: t = "VERY_POOR"
    return t, pct


def e(x):
    return html.escape(str(x if x is not None else ""))


CSS = """
:root{
  --paper:#F5F4F0; --ink:#14181B; --ink-soft:#5A6068; --rule:#D8D7D0;
  --violet:#4C2A85;   /* crystal violet - Gram positive */
  --safranin:#C0325A; /* safranin counterstain */
  --medium:#1F7A6D;   /* culture medium */
  --amber:#B8730E;
  --interior:#1F7A6D; --edge:#B8730E; --fc:#C0325A;
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif;}
.wrap{max-width:1180px;margin:0 auto;padding:0 24px 96px}
code,.loc,.mono{font-family:ui-monospace,SFMono-Regular,Menlo,"DejaVu Sans Mono",monospace}

header.hero{padding:64px 0 32px;border-bottom:2px solid var(--ink)}
.eyebrow{font:600 12px/1 ui-monospace,monospace;letter-spacing:.16em;text-transform:uppercase;
  color:var(--violet);margin-bottom:20px}
h1{font-family:"Iowan Old Style",Georgia,serif;font-weight:600;font-size:clamp(30px,4.6vw,54px);
  line-height:1.06;letter-spacing:-.02em;margin:0 0 16px}
h1 em{font-style:italic;color:var(--violet)}
.sub{max-width:66ch;color:var(--ink-soft);font-size:16.5px;margin:0}
.meta{margin-top:28px;display:flex;flex-wrap:wrap;gap:8px 28px;font:13px/1.4 ui-monospace,monospace;color:var(--ink-soft)}
.meta b{color:var(--ink);font-weight:600}

.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1px;
  background:var(--rule);border:1px solid var(--rule);margin:40px 0}
.stat{background:var(--paper);padding:18px 16px}
.stat .n{font-family:"Iowan Old Style",Georgia,serif;font-size:32px;line-height:1;letter-spacing:-.01em}
.stat .l{font:600 11px/1.3 ui-monospace,monospace;letter-spacing:.1em;text-transform:uppercase;
  color:var(--ink-soft);margin-top:8px}

.claim{border-left:3px solid var(--violet);background:#EFEDF5;padding:16px 20px;margin:36px 0;
  font-size:14.5px;color:#2C2440}
.claim b{color:var(--violet)}

h2{font-family:"Iowan Old Style",Georgia,serif;font-size:27px;font-weight:600;letter-spacing:-.01em;
  margin:60px 0 6px;padding-top:26px;border-top:1px solid var(--rule)}
h2 .num{font:600 12px/1 ui-monospace,monospace;color:var(--safranin);letter-spacing:.14em;
  display:block;margin-bottom:12px;text-transform:uppercase}
.lede{color:var(--ink-soft);max-width:70ch;margin:0 0 26px;font-size:15px}

/* signature: the boundary bar = the corrected-count formula, drawn */
.strain{border:1px solid var(--rule);background:#FBFBF9;margin-bottom:14px}
.strain summary{cursor:pointer;list-style:none;padding:16px 18px;display:grid;
  grid-template-columns:150px 1fr 190px 108px;gap:18px;align-items:center}
.strain summary::-webkit-details-marker{display:none}
.strain summary:hover{background:#F2F1EC}
.sid{font:600 15px/1 ui-monospace,monospace}
.tax{font-style:italic;color:var(--ink-soft);font-size:13.5px;margin-top:5px}
.flag{font-style:normal;font-size:10px;font-weight:600;color:var(--safranin);
  border:1px solid var(--safranin);border-radius:2px;padding:1px 4px;margin-left:6px;letter-spacing:.04em}
.bar{display:flex;height:11px;border:1px solid var(--rule);overflow:hidden}
.bar i{display:block;height:100%}
.bar .i{background:var(--interior)} .bar .e{background:var(--edge)} .bar .f{background:var(--fc)}
.barlab{font:11px/1.3 ui-monospace,monospace;color:var(--ink-soft);margin-top:6px}
.tierpill{font:600 10px/1 ui-monospace,monospace;letter-spacing:.08em;padding:4px 7px;border:1px solid;text-transform:uppercase}
.t-GOOD{color:var(--medium);border-color:var(--medium)}
.t-MODERATE{color:var(--violet);border-color:var(--violet)}
.t-POOR{color:var(--amber);border-color:var(--amber)}
.t-VERY_POOR{color:var(--safranin);border-color:var(--safranin)}
.cnt{text-align:right;font:13px/1.4 ui-monospace,monospace}
.cnt b{font-size:17px}

table{width:100%;border-collapse:collapse;font-size:12.5px}
thead th{position:sticky;top:0;background:#EDECE6;text-align:left;padding:9px 8px;
  font:600 10.5px/1.2 ui-monospace,monospace;letter-spacing:.07em;text-transform:uppercase;
  color:var(--ink-soft);border-bottom:1px solid var(--rule);white-space:nowrap}
tbody td{padding:8px;border-bottom:1px solid #E9E8E2;vertical-align:top}
tbody tr:hover{background:#F4F3EE}
.loc{font-size:11.5px;color:var(--ink-soft);white-space:nowrap}
.prod{font-weight:500}
.lt{font:600 10px/1 ui-monospace,monospace;padding:3px 5px;border:1px solid;text-transform:uppercase;white-space:nowrap}
.lt-Exceptional{color:#fff;background:var(--violet);border-color:var(--violet)}
.lt-High{color:var(--violet);border-color:var(--violet)}
.lt-Medium{color:var(--ink-soft);border-color:var(--rule)}
.lt-Low{color:#4A6B7A;border-color:#8AA4B0;background:#EAF1F4}
.lt-Inventory{color:#9AA0A6;border-color:#E4E3DD}
.cctt{font:10.5px/1.3 ui-monospace,monospace;color:var(--safranin)}
.bd-Interior{color:var(--interior);font-weight:600}
.bd-Edge{color:var(--edge)}
.bd-Full-contig{color:var(--fc)}
.napaa{font-size:10px;color:var(--ink-soft);border:1px dashed var(--rule);padding:1px 4px}
.scroll{max-height:560px;overflow:auto;border:1px solid var(--rule)}
.controls{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 16px}
.controls input,.controls select{font:13px ui-monospace,monospace;padding:8px 10px;
  border:1px solid var(--rule);background:#fff;color:var(--ink)}
.controls input{min-width:270px}
.note{font-size:13px;color:var(--ink-soft);border-top:1px solid var(--rule);margin-top:14px;padding-top:12px}
footer{margin-top:72px;padding-top:22px;border-top:2px solid var(--ink);font-size:12.5px;color:var(--ink-soft)}
@media(max-width:800px){.strain summary{grid-template-columns:1fr;gap:10px}}
@media(prefers-reduced-motion:no-preference){.strain[open] summary{border-bottom:1px solid var(--rule)}}
"""

JS = """
(function(){
  var q=document.getElementById('q'), tier=document.getElementById('tier'),
      bnd=document.getElementById('bnd'), rows=[].slice.call(document.querySelectorAll('#allbgc tbody tr')),
      n=document.getElementById('shown');
  function apply(){
    var s=(q.value||'').toLowerCase(), t=tier.value, b=bnd.value, c=0;
    rows.forEach(function(r){
      var ok=(!s||r.textContent.toLowerCase().indexOf(s)>-1)
           &&(!t||r.dataset.tier===t)&&(!b||r.dataset.boundary===b);
      r.style.display=ok?'':'none'; if(ok)c++;
    });
    n.textContent=c;
  }
  [q,tier,bnd].forEach(function(el){el.addEventListener('input',apply)});
})();
"""


def render(records, engine, args):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    n_strain = len(records)
    n_raw = sum(r["raw_bgc"] for r in records)
    n_corr = sum(r["corrected"] for r in records)
    n_exc = sum(r["tiers"]["Exceptional"] for r in records)
    n_high = sum(r["tiers"]["High"] for r in records)
    n_napaa = sum(r["napaa"] for r in records)
    genera = sorted({r["taxonomy"].split()[0] for r in records if r["taxonomy"] and r["taxonomy"] != "not verified"})

    o = []
    o.append(f"<!doctype html><html lang=en><meta charset=utf-8>")
    o.append('<meta name=viewport content="width=device-width,initial-scale=1">')
    o.append(f"<title>AS cohort — biosynthetic capacity readout</title><style>{CSS}</style><body><div class=wrap>")

    o.append("<header class=hero>")
    o.append("<div class=eyebrow>Sapote &middot; Mamey</div>")
    o.append(f"<h1>{n_strain} actinomycete genomes,<br>{n_raw} biosynthetic gene clusters,<br><em>one boundary problem.</em></h1>")
    o.append("<p class=sub>Every cluster below is reported with the contig and region it sits on, because "
             "in draft assemblies the edge of a contig is not the edge of a pathway. Interior clusters are whole; "
             "edge and full-contig clusters are truncated to an unknown degree. The corrected count carries that "
             "uncertainty forward instead of hiding it.</p>")
    o.append(f'<div class=meta><span><b>engine</b> {e(engine)}</span>'
             f'<span><b>generated</b> {now}</span>'
             f'<span><b>release</b> PUBLIC (AS cohort, PI decision 2026-07-06)</span>'
             f'<span><b>genera</b> {e(", ".join(genera)) or "—"}</span></div>')
    o.append("</header>")

    o.append("<div class=stats>")
    for n, l in [(n_strain, "strains"), (n_raw, "raw BGCs"), (f"{n_corr:.1f}", "corrected BGCs"),
                 (n_exc, "exceptional leads"), (n_high, "high leads"), (n_napaa, "NAPAA (excluded)")]:
        o.append(f'<div class=stat><div class=n>{e(n)}</div><div class=l>{e(l)}</div></div>')
    o.append("</div>")

    o.append("<div class=claim><b>Read these as capacity, not chemistry.</b> Each cluster encodes biosynthetic "
             "capacity consistent with its predicted class. Nothing here says a strain <i>produces</i> a compound: "
             "that needs metabolomics, fractionation, isolation, or genetic proof. KnownClusterBlast and BLASTp "
             "report <b>similarity, not identity</b>. Antimicrobial activity is observed at the level of crude "
             "extract only and is never attributed to a single locus. NAPAA clusters are ubiquitous and are "
             "excluded from comparative claims.</div>")

    # ---- strains
    o.append('<h2><span class=num>Section 1 &nbsp;/&nbsp; per strain</span>Assembly decides what you can claim</h2>')
    o.append('<p class=lede>The bar under each strain is the corrected-count formula drawn to scale: '
             '<span style="color:var(--interior)">&#9632; interior</span> counts once, '
             '<span style="color:var(--edge)">&#9632; edge</span> counts a half, '
             '<span style="color:var(--fc)">&#9632; full-contig</span> counts a quarter. '
             'A long amber-and-red bar means the genome, not the biology, is the limiting reagent.</p>')

    for r in sorted(records, key=lambda x: -x["corrected"]):
        tier, pct = assembly_tier(r)
        c = r["counts"]; tot = max(1, r["raw_bgc"])
        wi, we, wf = (100.0 * c[k] / tot for k in ("Interior", "Edge", "Full-contig"))
        flag = '<span class=flag>genus placeholder</span>' if r["taxonomy_placeholder"] else ""
        gsize = f"{r['genome_bp']/1e6:.2f} Mb" if r.get("genome_bp") else "—"
        o.append("<details class=strain><summary>")
        o.append(f'<div><div class=sid>{e(r["strain"])}</div><div class=tax>{e(r["taxonomy"])}{flag}</div></div>')
        o.append(f'<div><div class=bar><i class=i style="width:{wi:.2f}%"></i>'
                 f'<i class=e style="width:{we:.2f}%"></i><i class=f style="width:{wf:.2f}%"></i></div>'
                 f'<div class=barlab>{c["Interior"]} interior &middot; {c["Edge"]} edge &middot; '
                 f'{c["Full-contig"]} full-contig &nbsp;|&nbsp; {pct:.0f}% interior</div></div>')
        o.append(f'<div><span class="tierpill t-{tier}">{tier}</span>'
                 f'<div class=barlab>{gsize} &middot; {e(r["contigs"])} contigs &middot; N50 {e(r["n50"])}</div></div>')
        o.append(f'<div class=cnt><b>{r["corrected"]:.1f}</b><br><span class=barlab>corrected / {r["raw_bgc"]} raw</span></div>')
        o.append("</summary>")

        o.append('<div class=scroll><table><thead><tr>'
                 '<th>rank</th><th>assembly locator</th><th>products</th><th>boundary</th>'
                 '<th>arch</th><th>AB</th><th>AF</th><th>novelty</th><th>lead</th><th>KCB top</th><th>CCTT</th>'
                 '</tr></thead><tbody>')
        for row in r["rows"][:400]:
            b = (row.get("Boundary") or "").strip()
            lt = (row.get("Lead_tier_auto") or "").strip()
            prod = (row.get("Products") or "").strip()
            nap = ' <span class=napaa>NAPAA · excluded</span>' if "NAPAA" in prod else ""
            o.append(
                f'<tr><td class=mono>{e(row.get("Corrected_rank") or row.get("Rank"))}</td>'
                f'<td class=loc>{e(row.get("Node_ID"))} &middot; {e(row.get("antiSMASH_Region"))}'
                f'<br><span style="color:#9AA0A6">{e(row.get("BGC_ID"))}</span></td>'
                f'<td class=prod>{e(prod)}{nap}</td>'
                f'<td class="bd-{e(b)}">{e(b)}</td>'
                f'<td class=mono>{e(row.get("Arch"))}</td>'
                f'<td class=mono>{e(row.get("AB_auto"))}</td>'
                f'<td class=mono>{e(row.get("AF_auto"))}</td>'
                f'<td class=mono>{e(row.get("Novelty_auto"))}</td>'
                f'<td><span class="lt lt-{e(lt)}">{e(lt)}</span></td>'
                f'<td>{e((row.get("KCB_top") or "")[:40])}</td>'
                f'<td class=cctt>{e(row.get("CCTT_triggers"))}</td></tr>')
        o.append("</tbody></table></div>")
        if len(r["rows"]) > 400:
            o.append(f'<div class=note>Showing first 400 of {len(r["rows"])} clusters; the full table is in '
                     f'<code>{e(r["strain"])}_4_triage_board.csv</code> inside the sealed package.</div>')
        o.append("</details>")

    # ---- all-BGC searchable table
    all_rows = [(r["strain"], row) for r in records for row in r["rows"]]
    leads = [(s, row) for s, row in all_rows
             if (row.get("Lead_tier_auto") or "").strip() in ("Exceptional", "High")]
    o.append('<h2><span class=num>Section 2 &nbsp;/&nbsp; cohort lead board</span>Where the chemistry might be new</h2>')
    o.append(f'<p class=lede>{len(leads)} clusters reach High or Exceptional on the engine\'s automated axes. '
             'Lead tier is a triage aid, not a verdict: it ranks evidence density, and a truncated cluster can rank '
             'high on a fragment. Confirmation runs through Mode B and an independent BLASTp channel.</p>')
    o.append('<div class=controls>'
             '<input id=q placeholder="filter — strain, node, product, KCB, CCTT…" aria-label="filter clusters">'
             '<select id=tier aria-label="lead tier"><option value="">all lead tiers</option>'
             '<option>Exceptional</option><option>High</option><option>Medium</option><option>Low</option><option>Inventory</option></select>'
             '<select id=bnd aria-label="boundary"><option value="">all boundaries</option>'
             '<option>Interior</option><option>Edge</option><option>Full-contig</option></select>'
             '<span class=barlab style="align-self:center"><b id=shown>' + str(len(all_rows)) + '</b> clusters shown</span>'
             '</div>')
    o.append('<div class=scroll><table id=allbgc><thead><tr>'
             '<th>strain</th><th>assembly locator</th><th>products</th><th>boundary</th>'
             '<th>AB</th><th>AF</th><th>novelty</th><th>lead</th><th>KCB top</th><th>CCTT</th>'
             '</tr></thead><tbody>')
    def sortkey(t):
        s, row = t
        try:
            i = TIER_ORDER.index((row.get("Lead_tier_auto") or "").strip())
        except ValueError:
            i = 99
        try:
            ab = -float(row.get("AB_auto") or 0)
        except ValueError:
            ab = 0
        return (i, ab)
    for s, row in sorted(all_rows, key=sortkey):
        b = (row.get("Boundary") or "").strip()
        lt = (row.get("Lead_tier_auto") or "").strip()
        prod = (row.get("Products") or "").strip()
        nap = ' <span class=napaa>NAPAA · excluded</span>' if "NAPAA" in prod else ""
        o.append(
            f'<tr data-tier="{e(lt)}" data-boundary="{e(b)}">'
            f'<td class=mono>{e(s)}</td>'
            f'<td class=loc>{e(row.get("Node_ID"))} &middot; {e(row.get("antiSMASH_Region"))}'
            f'<br><span style="color:#9AA0A6">{e(row.get("BGC_ID"))}</span></td>'
            f'<td class=prod>{e(prod)}{nap}</td>'
            f'<td class="bd-{e(b)}">{e(b)}</td>'
            f'<td class=mono>{e(row.get("AB_auto"))}</td>'
            f'<td class=mono>{e(row.get("AF_auto"))}</td>'
            f'<td class=mono>{e(row.get("Novelty_auto"))}</td>'
            f'<td><span class="lt lt-{e(lt)}">{e(lt)}</span></td>'
            f'<td>{e((row.get("KCB_top") or "")[:44])}</td>'
            f'<td class=cctt>{e(row.get("CCTT_triggers"))}</td></tr>')
    o.append("</tbody></table></div>")
    o.append('<div class=note>Saccharide-only regions appear here in text; per <code>figure_policy.py</code> they are '
             'omitted from figures. Bare BGC IDs are never used as identifiers — the node and region are the address.</div>')

    o.append("<footer>")
    o.append(f"Rendered by <code>tools/build_cohort_html.py</code> from {n_strain} sealed Mamey packages "
             f"({e(engine)}). This file is a view: it reads <code>manifest.json</code> and "
             f"<code>*_4_triage_board.csv</code> in place and modifies nothing. Provenance for every cell is "
             f"store-backed (engine output), not reconstructed or corpus-derived.")
    o.append("</footer></div>")
    o.append(f"<script>{JS}</script></body></html>")
    return "\n".join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--packages-root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--placeholder-flags", default=None,
                    help="JSON list of strains whose genus is a placeholder")
    a = ap.parse_args()

    root = Path(a.packages_root)
    placeholders = set()
    if a.placeholder_flags and os.path.exists(a.placeholder_flags):
        placeholders = set(_read_json(a.placeholder_flags))

    records = []
    for sdir in sorted(root.iterdir()):
        if not sdir.is_dir():
            continue
        rec = strain_record(sdir, placeholders)
        if rec:
            records.append(rec)
    if not records:
        raise SystemExit(f"no sealed packages under {root}")

    engine = records[0]["engine"]
    out = Path(a.out)
    atomic_write_text(str(out), render(records, engine, a), encoding="utf-8")
    n_bgc = sum(r["raw_bgc"] for r in records)
    emit(f"[html] {out} — {len(records)} strains, {n_bgc} BGCs, {out.stat().st_size/1e6:.2f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
