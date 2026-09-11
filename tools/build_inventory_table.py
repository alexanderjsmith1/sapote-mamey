#!/usr/bin/env python3
"""Improved BGC inventory deliverable: ONE document, two views of the same BGCs.
  View A  serial  - antiSMASH region order (region001, region002, ...), exactly how antiSMASH lists them.
  View B  by class - same BGCs grouped by headline class, ranked within class by AB capacity.
Auto-generatable per strain from the inventory + triage board. Claim-safe; node/contig on every row.
Usage: python3 build_inventory_table.py <package_dir> <strain> [--out <path.md>]
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import csv, os, re, sys
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _wbio import atomic_write_text

# SSOT for the release tag (v9.7.236 PI decision: AS- is PUBLIC). Do not re-implement inline.
try:
    from mamey.dedup_and_guard import derive_release
except ImportError:
    _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    from mamey.dedup_and_guard import derive_release

def short_node(n):
    m = re.search(r"(NODE_\d+)", n or "")
    return m.group(1) if m else (n or "-")[:16]
def short_kcb(k):
    if not k: return "-"
    parts = [p.strip() for p in k.split("|")]
    return (parts[1] if len(parts) > 1 else parts[0])[:30]
def region_num(r):
    m = re.search(r"(\d+)", r or "")
    return int(m.group(1)) if m else 9999
def headline_class(products):
    tl = (products or "").lower()
    for key, lab in [("nrps", "NRPS"), ("transat", "PKS (trans-AT)"), ("t1pks", "PKS (T1)"),
                     ("t2pks", "PKS (T2)"), ("t3pks", "PKS (T3)"), ("lanthi", "RiPP"), ("ripp", "RiPP"),
                     ("lasso", "RiPP"), ("thiopep", "RiPP"), ("ranthi", "RiPP"), ("sacti", "RiPP"),
                     ("terpene", "terpene"), ("sidero", "siderophore"), ("indole", "indole"),
                     ("butyrolactone", "signalling"), ("saccharide", "saccharide (excl.)"),
                     ("napaa", "NAPAA (excl.)")]:
        if key in tl: return lab
    if "pks" in tl: return "PKS (other)"
    return "other"

def load(pkg, strain):
    # v9.7.371 fix: no explicit encoding -- relied on the platform/locale default, a portability
    # landmine (a non-UTF-8-locale environment reads this differently, silently). Explicit
    # encoding="utf-8" matches this codebase's established convention elsewhere (_wbio.py's
    # atomic_write_text, redact_public_tier.py's strict-UTF-8 read).
    inv = {r["BGC_ID"]: r for r in csv.DictReader(open(f"{pkg}/{strain}_2_inventory.csv", encoding="utf-8"))}
    tri = {}
    tp = f"{pkg}/{strain}_4_triage_board.csv"
    if os.path.exists(tp):
        tri = {r["BGC_ID"]: r for r in csv.DictReader(open(tp, encoding="utf-8"))}
    rows = []
    for bid, i in inv.items():
        t = tri.get(bid, {})
        rows.append({
            "bgc": bid, "region": i.get("antiSMASH_Region") or i.get("Region") or "-",
            "node": short_node(i.get("Node_ID") or i.get("Contig")),
            "products": (i.get("Products") or "")[:40], "class": headline_class(i.get("Products")),
            "bound": (i.get("Boundary") or "")[:4], "kb": (i.get("Length_kb") or "")[:6],
            "ab": t.get("AB_auto") or "-", "af": t.get("AF_auto") or "-",
            "tier": (t.get("Lead_tier_auto") or "-")[:10], "kcb": short_kcb(i.get("KCB_top")),
        })
    return rows

def md_table(rows):
    H = "| BGC | region | node/contig | class | products | bnd | kb | AB | AF | tier | KCB ~ |"
    S = "|---|---|---|---|---|---|---|---|---|---|---|"
    L = [H, S]
    for r in rows:
        L.append(f"| {r['bgc']} | {r['region']} | {r['node']} | {r['class']} | {r['products']} | {r['bound']} | {r['kb']} | {r['ab']} | {r['af']} | {r['tier']} | {r['kcb']} |")
    return "\n".join(L)

def build(pkg, strain, out, release="PUBLIC", display=None):
    rows = load(pkg, strain)
    serial = sorted(rows, key=lambda r: region_num(r["region"]))
    # by class: group, order classes by best AB within, rank within class by AB desc
    def absort(r):
        # v9.7.371 fix: was `except Exception: return 0.0` -- an UNSCORED BGC (missing from the
        # triage board, or AB_auto blank -> r["ab"]=="-") and a GENUINELY zero-AB-capacity BGC
        # (r["ab"]=="0.0") both landed on sort key 0.0 (float(-0.0) compares equal to 0.0 in
        # Python's sort), making them indistinguishable in display order -- "not yet evaluated"
        # and "confirmed zero capacity" are different findings and shouldn't silently collapse.
        # float('inf') guarantees unscored always sorts strictly after every real score (including
        # a real zero), never tied with it, while leaving every real-score comparison unchanged.
        try: return -float(r["ab"])
        except Exception: return float("inf")
    by_cls = {}
    for r in rows: by_cls.setdefault(r["class"], []).append(r)
    cls_order = sorted(by_cls, key=lambda c: min(absort(r) for r in by_cls[c]))  # best (most negative) first
    disp = display or f"strain {strain}"
    try:
        from mamey import __version__ as _ev  # version-sync-ok: derived at runtime, not a literal
    except Exception:
        _ev = "?"
    doc = [f"# {disp} \u2014 BGC inventory ({release})",
           f"\n*Mamey v{_ev} \u00b7 {len(rows)} BGCs \u00b7 node/contig listed per row \u00b7 claim-safe: AB/AF are capacity rankings (not activity), KCB is a similarity anchor (not identity), Edge/Full-contig sizes are floors. saccharide/NAPAA shown but excluded from headline ranking.*",
           "\n## View A \u2014 serial (antiSMASH region order)",
           "*BGCs in the order antiSMASH reports them, for side-by-side reading against the antiSMASH output.*\n",
           md_table(serial),
           "\n## View B \u2014 by BGC class (ranked within class by AB capacity)",
           "*Same BGCs, grouped by headline class so leads of a kind sit together.*\n"]
    for c in cls_order:
        grp = sorted(by_cls[c], key=absort)
        doc.append(f"\n### {c}  ({len(grp)})")
        doc.append(md_table(grp))
    atomic_write_text(out, "\n".join(doc))
    return out, len(rows)

if __name__ == "__main__":
    pkg, strain = sys.argv[1], sys.argv[2]
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.join(os.environ.get("MAMEY_OUT", "."), f"{strain}_inventory_serial+byclass.md")
    rel = derive_release(strain)
    disp = ("Amycolatopsis sp. strain M39" if strain == "AmycSp_M39" else None)
    p, n = build(pkg, strain, out, rel, disp)
    emit(f"wrote {p.split('/')[-1]} ({n} BGCs, serial + by-class, {rel})")
