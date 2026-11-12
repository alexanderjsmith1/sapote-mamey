"""Which detection domain triggered each antiSMASH RiPP-like protocluster.

antiSMASH calls a protocluster "RiPP-like" when any one of about twenty profile HMMs hits (DUF692, YcaO,
Linocin_M18, strepbact, TIGR03975 and others; the rule is stored on the protocluster as detection_rule).
The product label alone hides which one fired. antiSMASH records it per gene: the trigger CDS carries
gene_functions "biosynthetic (rule-based-clusters) RiPP-like: <domain>". This module reads those genes
inside each RiPP-like protocluster's core location, through the engine's shared record pass.

One row per RiPP-like protocluster. A protocluster whose trigger gene cannot be found is kept with status
TRIGGER_UNRESOLVED, never dropped. A detection domain names the rule that fired. It is capacity evidence,
not a product, structure or activity.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .antismash_evidence import _run_record_extractors

RIPP_LIKE = "RiPP-like"
_TRIGGER = re.compile(r"\(rule-based-clusters\)\s+RiPP-like:\s*(\S+)")
_INT = re.compile(r"\d+")


def _span(location: str) -> tuple[int, int] | None:
    nums = [int(x) for x in _INT.findall(location or "")]
    return (min(nums), max(nums)) if len(nums) >= 2 else None


def _q(feature: dict, key: str) -> list:
    v = (feature.get("qualifiers") or {}).get(key, [])
    return v if isinstance(v, list) else [v]


def _ripp_like_from_rec(rec: dict, name: str, out: list) -> None:
    rec_id = rec.get("id") or ""
    feats = rec.get("features") or []
    regions = []
    for f in feats:
        if f.get("type") == "region":
            sp = _span(f.get("location", ""))
            num = (_q(f, "region_number") or [""])[0]
            if sp and str(num).isdigit():
                regions.append((sp, f"region{int(num):03d}", ";".join(_q(f, "product"))))
    cds = []
    for f in feats:
        if f.get("type") != "CDS":
            continue
        doms = [m.group(1) for g in _q(f, "gene_functions") for m in [_TRIGGER.search(str(g))] if m]
        if doms:
            sp = _span(f.get("location", ""))
            if sp:
                cds.append((sp, (_q(f, "locus_tag") or [""])[0], sorted(set(doms)),
                            len((_q(f, "translation") or [""])[0])))
    for f in feats:
        if f.get("type") != "protocluster" or (_q(f, "product") or [""])[0] != RIPP_LIKE:
            continue
        pc = _span(f.get("location", ""))
        core = _span((_q(f, "core_location") or [""])[0]) or pc
        if not pc:
            continue
        reg = [r for r in regions if r[0][0] <= pc[0] and pc[1] <= r[0][1] + 1]
        trig = [c for c in cds if c[0][0] < core[1] and core[0] < c[0][1]]
        domains = sorted({d for c in trig for d in c[2]})
        products = reg[0][2] if reg else ""
        out.append({
            "source": name,
            "record_id": rec_id,
            "region": reg[0][1] if reg else "",
            "protocluster_number": (_q(f, "protocluster_number") or [""])[0],
            "protocluster_location": f.get("location", ""),
            "contig_edge": (_q(f, "contig_edge") or [""])[0],
            "region_products": products,
            "region_is_ripp_like_only": products == RIPP_LIKE,
            "trigger_locus_tags": ";".join(c[1] for c in trig),
            "trigger_lengths_aa": ";".join(str(c[3]) for c in trig),
            "trigger_domains": "+".join(domains),
            "status": "TRIGGER_FOUND" if domains and reg else ("NO_REGION" if not reg else "TRIGGER_UNRESOLVED"),
        })


def extract_ripp_like_triggers(zip_path: str | Path) -> tuple[list[dict[str, Any]], dict]:
    """Rows for every RiPP-like protocluster in an antiSMASH ZIP, and the shared record-pass receipt."""
    out: list[dict[str, Any]] = []
    receipt = _run_record_extractors(zip_path, [(_ripp_like_from_rec, out)])
    return out, receipt


def domain_summary(rows: list[dict]) -> list[dict]:
    """Protoclusters per trigger-domain combination, largest first; unresolved rows are counted, not dropped."""
    counts: dict[str, dict] = {}
    for r in rows:
        key = r["trigger_domains"] or r["status"]
        c = counts.setdefault(key, {"trigger_domains": key, "protoclusters": 0, "in_ripp_like_only_regions": 0,
                                    "on_contig_edge": 0})
        c["protoclusters"] += 1
        c["in_ripp_like_only_regions"] += bool(r["region_is_ripp_like_only"])
        c["on_contig_edge"] += str(r["contig_edge"]) == "True"
    return sorted(counts.values(), key=lambda c: (-c["protoclusters"], c["trigger_domains"]))
