#!/usr/bin/env python3
"""kcb_confidence.py — extract antiSMASH's per-region KnownClusterBlast "Similarity Confidence"
(High / Medium / Low) from an antiSMASH v8 output.

WHY: for the KCB-demotion work. antiSMASH's own confidence flags which KCB calls are weak — in
AS-XXX (v8.0.4), 17/23 region hits are **Low**, exactly the ones that get over-analyzed. The demotion
logic can key on this to mark low-confidence KCB `discounted` without re-deriving anything.

WHERE IT LIVES (verified against AS-XXX v8.0.4, read from the files):
- The label is HTML-rendered in the region-overview table: `<td class="similarity-text">High|Low|Medium</td>`.
- It is NOT a labeled field in regions.js (its `confidence` key is binding-site weak/medium/strong; its
  numeric `similarity` is per-gene, n=818, not the per-region label) and NOT in the raw
  knownclusterblast/*.txt (scores only). So the region-overview HTML is the clean per-region source.
- antiSMASH derives the label from KnownClusterBlast gene coverage; treat the label as authoritative.

Provenance: corpus (antiSMASH KnownClusterBlast vs MIBiG). Similarity, not identity. This is a
VERIFICATION signal only — it must never originate/class/prioritize a finding (per the demotion spec).
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import re, glob, os

_ROW_RE = re.compile(
    r'data-anchor="#(?P<anchor>r\d+c\d+)".*?'                        # region anchor (e.g. r2c1)
    r'<td class="similarity-text"[^>]*>(?P<conf>High|Medium|Low)</td>',
    re.S)
_CLUSTER_RE = re.compile(r'similarity-text[^>]*>(?:High|Medium|Low)</td>\s*'
                         r'<td[^>]*>\s*(?:<a[^>]*>)?\s*(?P<cluster>[^<]+?)\s*(?:</a>|<)', re.S)


def extract_kcb_confidence(antismash_dir: str) -> list[dict]:
    """Return [{region_anchor, confidence, known_cluster}] per KCB-hit region, in table order.
    confidence ∈ {High, Medium, Low}. Regions with no KCB hit are absent (blank cell, no label)."""
    html_path = next(iter(glob.glob(os.path.join(antismash_dir, "**", "index.html"), recursive=True)
                          or glob.glob(os.path.join(antismash_dir, "index.html"))), None)
    if not html_path:
        return []
    html = open(html_path, encoding="utf-8", errors="replace").read()
    confs = [(m.group("anchor"), m.group("conf")) for m in _ROW_RE.finditer(html)]
    clusters = [m.group("cluster").strip() for m in _CLUSTER_RE.finditer(html)]
    out, seen = [], set()
    for i, (anchor, conf) in enumerate(confs):
        if anchor in seen:      # v8 HTML renders the overview table twice (per-record + global) — dedup by anchor
            continue
        seen.add(anchor)
        out.append({"region_anchor": anchor, "confidence": conf,
                    "known_cluster": clusters[i] if i < len(clusters) else ""})
    return out


def confidence_summary(rows: list[dict]) -> dict:
    from collections import Counter
    c = Counter(r["confidence"] for r in rows)
    return {"n_kcb_hits": len(rows), "High": c.get("High", 0),
            "Medium": c.get("Medium", 0), "Low": c.get("Low", 0)}


if __name__ == "__main__":
    import sys, json
    d = sys.argv[1]
    rows = extract_kcb_confidence(d)
    emit(json.dumps({"summary": confidence_summary(rows), "regions": rows[:60]}, indent=2))
