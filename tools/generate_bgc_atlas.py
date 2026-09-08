#!/usr/bin/env python3
"""generate_bgc_atlas.py — browsable HTML atlas of one strain's BGC inventory (deliverable G1).

Reads banked data only. One card per region with the standard locus label (Strain/Region · class · ~KCB anchor ·
edge-status · ModeB verdict), coloured by confidence tier, grouped by predicted class. Header shows region count
and the corrected BGC count (Interior + ½·Edge + ¼·Full-contig). PRIVATE banner + filename if the strain is AS.

Claim-safety: KCB = similarity anchor (rendered with a leading ~), NOT identification; antiSMASH classes are
E-signals not structures; bioactivity metadata is optional strain-level context; verdicts are [EG] offline.

Usage: python tools/generate_bgc_atlas.py --strain SID-XXX --banked-dir cohort [--out path.html]
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, os, json, html
from collections import defaultdict
import sys as _sys, os as _os


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _wbio import atomic_write_text

# SSOT for the release tag (v9.7.236 PI decision: AS- is PUBLIC). Do not re-implement inline.
try:
    from mamey.dedup_and_guard import derive_release
except ImportError:
    _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    from mamey.dedup_and_guard import derive_release

TIER={'Confirmed':'#2E7D32','Predicted-functional':'#2E86AB','KCB-anchored':'#E59866','Candidate-novel':'#7F8C8D'}

def corrected_count(bgcs):
    n=0.0
    for b in bgcs:
        e=(b.get('edge_status') or '')
        n+= 1.0 if e=='Interior' else 0.5 if e=='Edge' else 0.25
    return round(n,2)

def tier_of(b, verdict):
    anchor=(b.get('closest_kcb_product') or '').strip()
    dark = (not anchor) or anchor.upper()=='UNRESOLVED'
    if verdict in ('CONFIRM',): return 'Confirmed'
    if dark: return 'Candidate-novel'
    # intact-ish + resistance signal → predicted-functional, else just anchored
    return 'KCB-anchored'

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--strain', required=True); ap.add_argument('--banked-dir', default='cohort')
    ap.add_argument('--out', default=None); ap.add_argument('--strictness', default='offline [EG]')
    a=ap.parse_args()
    bank=_read_json(os.path.join(a.banked_dir,'bgc_data.json'))
    strains=bank['strains']; allb=bank['bgcs']
    from mamey.figure_policy import omit_saccharides
    bgcs=[b for b in allb if b['sid']==a.strain]
    bgcs=omit_saccharides(bgcs)  # figure policy: pure-saccharide regions never rendered (text-only)
    if not bgcs: emit(f"  no BGCs for {a.strain}"); return
    # verdicts
    vmap={}
    vp=os.path.join(a.banked_dir,'modeb_verdicts.csv')
    if os.path.exists(vp):
        import csv
        for r in csv.DictReader(open(vp)):
            if r['strain']==a.strain: vmap[r['bgc']]=(r['status'],r.get('modeb_class',''))
    is_private = derive_release(a.strain) == "PRIVATE"
    org=strains.get(a.strain,{}).get('organism','') if isinstance(strains.get(a.strain),dict) else ''
    cc=corrected_count(bgcs)
    # group by primary class
    def pclass(b):
        cl=[p.strip() for p in (b.get('products') or '').split(';') if p.strip()]
        return cl[0] if cl else 'unclassified'
    groups=defaultdict(list)
    for b in bgcs: groups[pclass(b)].append(b)
    # build cards
    def card(b):
        bid=b.get('bgc_id',''); verdict,mclass=vmap.get(bid,('[EG]',''))
        tier=tier_of(b,verdict if verdict in('CONFIRM','DROP','DOWNGRADE') else None)
        anchor=html.escape((b.get('closest_kcb_product') or 'UNRESOLVED')[:60])
        vtag = verdict if verdict in('CONFIRM','DROP','DOWNGRADE') else '[EG]'
        # BC2-408: `region` is the antiSMASH region NUMBER *within its own contig*, not a
        # strain-wide-unique locator -- on a fragmented assembly (common in this cohort; the
        # cohort's own house rule is "occurrence identity = full node/contig + region, BGC
        # ordinal is a secondary source-scoped alias only") most contigs carry exactly one
        # region, so `region` alone is "region001" for EVERY BGC and every card in a class
        # renders an identical, non-disambiguating label. Live-reproduced on AS-XXX (VERY_POOR
        # assembly, 64 BGCs across 64 distinct contigs): all 64 banked rows carry
        # region=="region001"; the 14-card "PKS" group all showed the literal string
        # "AS-XXX/region001" with no way to tell the cards apart short of reading each card's
        # own KCB anchor text. `bgc_id` (already computed above for the ModeB verdict lookup)
        # is guaranteed unique per strain -- lead with it, keep `region` as supporting context
        # rather than dropping it (still useful on non-fragmented genomes where it varies).
        return f"""<div class="card" style="border-left:6px solid {TIER[tier]}">
          <div class="lab">{html.escape(a.strain)}/{html.escape(bid)} · {html.escape(b.get('region','?'))} · {html.escape(pclass(b))}</div>
          <div class="anchor">~{anchor} (similarity)</div>
          <div class="meta">{b.get('length_kb','?')} kb · {html.escape(b.get('edge_status','?'))} · <b style="color:{TIER[tier]}">{tier}</b> · ModeB {html.escape(str(vtag))}{(' · '+html.escape(mclass)) if mclass else ''}</div>
        </div>"""
    sections=''
    for cls in sorted(groups, key=lambda c:-len(groups[c])):
        cards=''.join(card(b) for b in sorted(groups[cls], key=lambda x:-(x.get('length_kb') or 0)))
        sections+=f'<h2>{html.escape(cls)} <span class="n">({len(groups[cls])})</span></h2><div class="grid">{cards}</div>'
    legend=''.join(f'<span class="chip" style="background:{c}">{t}</span>' for t,c in TIER.items())
    private = '<div class="private">PRIVATE — contains unpublished AS strain data. No public release / GitHub / Zenodo.</div>' if is_private else ''
    doc=f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(a.strain)} BGC Atlas</title>
<style>body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#f7f8fa;color:#1a1a2e}}
header{{background:#2E5E7E;color:#fff;padding:18px 26px}} header h1{{margin:0 0 4px}} .sub{{opacity:.85;font-size:14px}}
.private{{background:#C0392B;color:#fff;padding:8px 26px;font-weight:600;font-size:13px}}
main{{padding:20px 26px;max-width:1200px}} h2{{margin:24px 0 8px;font-size:16px;border-bottom:1px solid #ddd;padding-bottom:4px}} .n{{color:#888;font-weight:400}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:10px}}
.card{{background:#fff;border-radius:6px;padding:10px 12px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
.lab{{font-weight:600;font-size:13px}} .anchor{{color:#444;font-size:13px;margin:2px 0}} .meta{{font-size:12px;color:#555}}
.legend{{margin:8px 0 0}} .chip{{display:inline-block;color:#fff;border-radius:10px;padding:2px 9px;font-size:11px;margin-right:6px}}
footer{{padding:16px 26px;font-size:12px;color:#666;border-top:1px solid #ddd;margin-top:24px}}</style></head>
<body><header><h1>{html.escape(a.strain)} — BGC Atlas</h1>
<div class="sub">{html.escape(org)} · {len(bgcs)} regions · corrected count {cc} (Interior + ½·Edge + ¼·FC) · strictness {html.escape(a.strictness)}</div>
<div class="legend">{legend}</div></header>{private}
<main>{sections}</main>
<footer>KCB anchors (~) are similarity, not identification; antiSMASH classes are E-signals, not structures.
Bioactivity metadata may be `NOT_SUPPLIED` and is not asserted per BGC. Verdicts are [EG] offline
unless verified-literature-upgraded. Built from banked data only.</footer></body></html>"""
    out=a.out or f"{a.strain}_BGC_Atlas{'_PRIVATE' if is_private else ''}.html"
    atomic_write_text(out, doc)
    emit(f"  wrote {out} — {len(bgcs)} regions, corrected count {cc}, {len(groups)} classes")

if __name__=='__main__': main()
