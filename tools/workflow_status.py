#!/usr/bin/env python3
"""Workflow status: where each strain sits in the pipeline. Emits a stage-matrix CSV + an SVG progress graphic.

Stages (left->right): Parse -> Scans -> RG-GMCI -> Boards -> ModeB -> Banked.
Marker per stage:  full = complete | half = partial | empty/x = not run / failed.
Usage: python3 workflow_status.py            (text + CSV + SVG)
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import os, csv, json, sys
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
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

LIB = os.environ.get("MAMEY_LIB", "library")
RUNS, BANK = f"{LIB}/runs", f"{LIB}/bank"
OUT = os.environ.get("MAMEY_OUT", ".")
STAGES = ["Parse", "Scans", "RG-GMCI", "Boards", "ModeB", "Banked"]


def release_scope(rows):
    """The release tier this emission actually covers, derived from the rows.

    Single source for BOTH the on-figure caption and the output filename suffix, so a file can
    never be named for a tier its own content contradicts. Fail-safe: any PRIVATE row makes the
    whole emission PRIVATE (derive_release already fails safe per-strain; this only aggregates).
    """
    return "PRIVATE" if any(r["release"] == "PRIVATE" for r in rows) else "PUBLIC"


def results_index():
    """Per-strain results + source filename from scan_index.csv."""
    p = f"{LIB}/scan_index.csv"
    out = {}
    if os.path.exists(p):
        for r in csv.DictReader(open(p)):
            out[r.get("strain", "")] = r
    return out


def stage_status():
    banked = set()
    bp = f"{BANK}/bgc_data.json"
    if os.path.exists(bp):
        banked = set(_read_json(bp)["strains"])
    idx = results_index()
    rows = []
    for s in sorted(os.listdir(RUNS)) if os.path.isdir(RUNS) else []:
        d = f"{RUNS}/{s}"
        if not os.path.isdir(d):
            continue
        def has(suf):
            for root, _, fs in os.walk(d):
                if any(f.endswith(suf) for f in fs):
                    return True
            return False
        inv, tri = has("_2_inventory.csv"), has("_4_triage_board.csv")
        brd, dd = has("_4c_AB_lead_board.csv"), has("deep_data.json")
        modeb_dives = has("_ModeB_dives.md") or has("modeb_deepdive.md")  # full judgment dives
        st = {
            "Parse":   "full" if inv else "x",
            "Scans":   "full" if tri else "x",
            "RG-GMCI": "full" if tri else "x",          # runs inside gold
            "Boards":  "full" if brd else "x",
            "ModeB":   "full" if modeb_dives else ("half" if dd else "x"),  # data ready vs dives run
            "Banked":  "full" if s in banked else "x",
        }
        priv = derive_release(s) == "PRIVATE"
        ix = idx.get(s, {})
        rows.append({"strain": s, "release": "PRIVATE" if priv else "PUBLIC",
                     "source_file": ix.get("source_file", ""),
                     "corrected": ix.get("corrected", "-"), "tier": ix.get("tier", "-"),
                     "top_AB": f'{ix.get("top_AB_bgc","-")}={ix.get("AB","-")}',
                     "top_AF": f'{ix.get("top_AF_bgc","-")}={ix.get("AF","-")}', **st})
    return rows


def render_svg(rows):
    rowH, x0, colW, top = 26, 200, 118, 92
    W = x0 + colW * len(STAGES) + 250
    H = top + rowH * len(rows) + 50
    scope = release_scope(rows)
    def marker(cx, cy, state):
        if state == "full":
            return f'<circle cx="{cx}" cy="{cy}" r="7" fill="#2E7D32" stroke="#1B5E20"/><path d="M{cx-3.5},{cy} l2.5,2.8 l4.5,-5.5" stroke="#fff" stroke-width="1.6" fill="none"/>'
        if state == "half":
            return (f'<circle cx="{cx}" cy="{cy}" r="7" fill="#fff" stroke="#E69500" stroke-width="1.6"/>'
                    f'<path d="M{cx},{cy-7} a7,7 0 0,1 0,14 z" fill="#E69500"/>')
        return f'<circle cx="{cx}" cy="{cy}" r="7" fill="#fff" stroke="#BBB" stroke-width="1.4"/><path d="M{cx-3},{cy-3} l6,6 M{cx+3},{cy-3} l-6,6" stroke="#C0392B" stroke-width="1.3"/>'
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Arial,Helvetica,sans-serif">']
    svg.append(f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>')
    svg.append(f'<text x="20" y="32" font-size="17" font-weight="bold" fill="#1A2F4A">Sapote\u2013Mamey \u2014 strain workflow status</text>')
    tag = "PRIVATE (contains unpublished AS strains)" if scope == "PRIVATE" else "PUBLIC"
    svg.append(f'<text x="20" y="52" font-size="11" fill="#666">{len(rows)} strains \u00b7 {tag} \u00b7 stage = progress through the pipeline</text>')
    # stage headers + arrow baseline
    for i, st in enumerate(STAGES):
        cx = x0 + colW * i + colW // 2
        svg.append(f'<text x="{cx}" y="{top-18}" font-size="11" font-weight="bold" fill="#1A2F4A" text-anchor="middle">{st}</text>')
    # legend (bottom, clear of headers)
    ly = H - 22
    svg.append(marker(x0, ly, "full") + f'<text x="{x0+12}" y="{ly+4}" font-size="10" fill="#555">complete</text>')
    svg.append(marker(x0+110, ly, "half") + f'<text x="{x0+122}" y="{ly+4}" font-size="10" fill="#555">data ready / partial</text>')
    svg.append(marker(x0+280, ly, "x") + f'<text x="{x0+292}" y="{ly+4}" font-size="10" fill="#555">not run / failed</text>')
    for ri, r in enumerate(rows):
        cy = top + rowH * ri + 13
        zebra = "#F4F7FA" if ri % 2 else "#FFFFFF"
        svg.append(f'<rect x="10" y="{cy-12}" width="{W-20}" height="{rowH}" fill="{zebra}"/>')
        col = "#7A2E2E" if r["release"] == "PRIVATE" else "#1A2F4A"
        nm = r["strain"] if r["release"] == "PUBLIC" else f'{r["strain"]} \u25aa'
        svg.append(f'<text x="20" y="{cy+4}" font-size="11" fill="{col}">{nm}</text>')
        # progress arrow: extends to the last completed/partial stage
        last = -1
        for i, st in enumerate(STAGES):
            if r[st] in ("full", "half"):
                last = i
        ax0 = x0 + colW // 2
        if last >= 0:
            ax1 = x0 + colW * last + colW // 2
            svg.append(f'<line x1="{ax0}" y1="{cy}" x2="{ax1}" y2="{cy}" stroke="#9CC3E0" stroke-width="3"/>')
            svg.append(f'<path d="M{ax1+4},{cy} l-7,-4 l0,8 z" fill="#9CC3E0"/>')
        for i, st in enumerate(STAGES):
            cx = x0 + colW * i + colW // 2
            svg.append(marker(cx, cy, r[st]))
        # source filename (right of the stages) — acronyms are lossy, show the original
        sf = (r.get("source_file") or "").replace("(source not recorded)", "\u2014 backfill")
        if len(sf) > 30: sf = sf[:28] + "\u2026"
        svg.append(f'<text x="{x0 + colW*len(STAGES) + 6}" y="{cy+4}" font-size="9" fill="#888">{sf}</text>')
    svg.append('</svg>')
    p = f"{OUT}/workflow_status_{scope}.svg"
    atomic_write_text(p, "\n".join(svg))
    return p


def render_detailed_svg(rows):
    """Detailed view: stages + results (corrected, tier, top AB/AF) + source file."""
    rowH, top = 26, 96
    cols = [("strain", 110), ("source file", 210), ("stages", 175),
            ("corr", 56), ("tier", 92), ("top AB lead", 150), ("top AF lead", 150)]
    x0 = 16
    xs = {}; cx = x0
    for name, w in cols: xs[name] = cx; cx += w
    W = cx + 20; H = top + rowH * len(rows) + 30
    scope = release_scope(rows)
    def marker(mx, my, state, r=5):
        if state == "full": return f'<circle cx="{mx}" cy="{my}" r="{r}" fill="#2E7D32"/>'
        if state == "half": return f'<circle cx="{mx}" cy="{my}" r="{r}" fill="#fff" stroke="#E69500" stroke-width="1.4"/><path d="M{mx},{my-r} a{r},{r} 0 0,1 0,{2*r} z" fill="#E69500"/>'
        return f'<circle cx="{mx}" cy="{my}" r="{r}" fill="#fff" stroke="#C0392B" stroke-width="1.2"/>'
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Arial,Helvetica,sans-serif">',
           f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>',
           f'<text x="16" y="30" font-size="16" font-weight="bold" fill="#1A2F4A">Sapote\u2013Mamey \u2014 workflow status + results (detailed)</text>',
           f'<text x="16" y="48" font-size="10" fill="#666">{len(rows)} strains \u00b7 stages = Parse\u00b7Scans\u00b7RG-GMCI\u00b7Boards\u00b7ModeB\u00b7Banked (left\u2192right) \u00b7 results from the run \u00b7 {scope}</text>']
    for name, w in cols:
        svg.append(f'<text x="{xs[name]}" y="{top-14}" font-size="10" font-weight="bold" fill="#1A2F4A">{name}</text>')
    for ri, r in enumerate(rows):
        cy = top + rowH * ri + 13
        if ri % 2: svg.append(f'<rect x="8" y="{cy-12}" width="{W-16}" height="{rowH}" fill="#F4F7FA"/>')
        colr = "#7A2E2E" if r["release"] == "PRIVATE" else "#1A2F4A"
        nm = r["strain"] + ("\u25aa" if r["release"] == "PRIVATE" else "")
        svg.append(f'<text x="{xs["strain"]}" y="{cy+4}" font-size="10" fill="{colr}">{nm}</text>')
        sf = (r.get("source_file") or "").replace("(source not recorded)", "\u2014 backfill")
        if len(sf) > 30: sf = sf[:28] + "\u2026"
        svg.append(f'<text x="{xs["source file"]}" y="{cy+4}" font-size="8.5" fill="#888">{sf}</text>')
        for i, st in enumerate(STAGES):
            svg.append(marker(xs["stages"] + i * 14 + 6, cy, r[st]))
        svg.append(f'<text x="{xs["corr"]}" y="{cy+4}" font-size="10" fill="#222">{r.get("corrected","-")}</text>')
        tier = r.get("tier", "-"); tcol = {"GOOD": "#2E7D32", "MODERATE": "#1f6fb0", "POOR": "#E69500", "VERY_POOR": "#C0392B"}.get(tier, "#666")
        svg.append(f'<text x="{xs["tier"]}" y="{cy+4}" font-size="9" fill="{tcol}">{tier}</text>')
        svg.append(f'<text x="{xs["top AB lead"]}" y="{cy+4}" font-size="9" fill="#222">{r.get("top_AB","-")}</text>')
        svg.append(f'<text x="{xs["top AF lead"]}" y="{cy+4}" font-size="9" fill="#222">{r.get("top_AF","-")}</text>')
    svg.append('</svg>')
    p = f"{OUT}/workflow_status_detailed_{scope}.svg"
    atomic_write_text(p, "\n".join(svg))
    return p


def write_csv(rows):
    p = f"{OUT}/workflow_status_matrix_{release_scope(rows)}_data.csv"
    with open(p, "w", newline="") as f:
        w = _SafeWriter(f)
        w.writerow(["strain", "release", "source_file"] + STAGES + ["corrected", "tier", "top_AB", "top_AF"])
        for r in rows:
            w.writerow([r["strain"], r["release"], r.get("source_file", "")] + [r[s] for s in STAGES]
                       + [r.get("corrected", ""), r.get("tier", ""), r.get("top_AB", ""), r.get("top_AF", "")])
    return p


if __name__ == "__main__":
    rows = stage_status()
    emit(f"{'strain':<22}{'  '.join(s[:5] for s in STAGES)}")
    for r in rows:
        ic = {"full": "\u2713", "half": "\u25d1", "x": "\u2717"}
        emit(f"{r['strain']:<22}" + "      ".join(ic[r[s]] for s in STAGES) + f"   [{r['release']}]")
    csvp = write_csv(rows); svgp = render_svg(rows); dsvgp = render_detailed_svg(rows)
    n_done = sum(1 for r in rows if r["Banked"] == "full")
    n_bare = sum(1 for r in rows if r["Parse"] == "x")
    emit(f"\n{n_done} banked, {n_bare} bare/held. -> {svgp.split('/')[-1]} (overview) + {dsvgp.split('/')[-1]} (detailed) + {csvp.split('/')[-1]}")
