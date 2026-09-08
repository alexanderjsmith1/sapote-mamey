#!/usr/bin/env python3
"""reclass_check.py — antiSMASH label vs. diagnostic-domain discrepancy (lead L1).

The shippable reconciliation of two prototypes (eval-chat undeclared-strong + label-unsupported;
deepdive exact-token matching + FP fix), consuming the CURATED discriminating-domain map that
IDEA_BUNDLE_EVALUATED.md flagged as the required pre-ship fix.

CLAIM DISCIPLINE (hard): CLASS_DISCREPANCY is a **review prompt**, never a reclassification verdict
and never a phenotype. Language is capacity-level. Domain evidence is similarity, not identity.
Provenance: store-backed (sealed-package gene_by_gene_all_bgcs.csv + triage_board.csv). BGCs cited node·region.

Key properties (verified on AS-XXX v9.7.202, 39 BGCs — FP trajectory 20→17→11→8, remaining all real signal):
  - curated map: generic domains (AMP-binding, Abhydrolase, bare Condensation) excluded
  - skip_domain_check: terpene/ectoine/saccharide (diagnostic machinery absent from sec_met_domains) not flagged
  - require_specific + min_domains per class; exact-token matching (no TatD_DNase->TD collision)
  - thiopeptide upgrade: azole-RiPP + Thiopeptide_F_RRE/TIGR03882 -> flag thiopeptide

LIMIT (stated plainly): motif-on-precursor half (mycofactocin IDGMCGVY) NOT implemented — needs CDS
sequences from region GBKs via the RiPP-precursor caller (lead M6). Only the domain-implication arm is live.
Tokenization caveat: per-gene sec_met_domains uses different tokens than region rules (micKC->Pkinase,
Condensation->NRPS-A_a*); label_unsupported is unreliable for re-tokenized classes (documented in map _meta).
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import sys, csv, glob, json, re, argparse
from pathlib import Path
from collections import defaultdict


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)



def _find(pkg, suffix):
    m = glob.glob(f"{pkg}/*{suffix}")
    return m[0] if m else None

def _rows(path):
    return list(csv.DictReader(open(path, encoding="utf-8", errors="replace"))) if path else []

def _locator(r):
    node = r.get("Node_ID", "")
    reg = (r.get("antiSMASH_Region", "") or "").replace("region", "r")
    return f"{r.get('BGC_ID','?')} ({node} · {reg})"

def _domains_present(dom_set, wanted):
    """Exact-token or _-boundary-prefix match. Prevents substring collisions (TatD_DNase vs TD)."""
    present = []
    for w in wanted:
        for d in dom_set:
            if d == w or d.startswith(w + "_") or d.startswith(w + "."):
                present.append(w); break
    return present


def analyze(pkg, cmap):
    """Core logic. Returns (per_bgc_findings, summary). Pure; no printing.

    cmap: the loaded curated-map dict (so tests can pass a synthetic map without a file).
    per_bgc_findings: list of {bgc_id, locator, label, findings:[{kind,cls,present}]}
    summary: {n_bgc, n_flagged, kinds:{...}}
    """
    classes = cmap["classes"]
    skip = set(cmap["skip_domain_check"]["classes"])
    # Case-insensitive lookups: real antiSMASH Products labels are lowercase for several of
    # this curated map's own class keys (e.g. "t1pks"/"nrps", confirmed against the engine's
    # own production vocabulary in mamey/class_architecture.py::_REAL_CLASSES), but the map's
    # keys and this tool's original comparisons were case-sensitive exact-match. That silently
    # exempted every T1PKS/T2PKS/T3PKS/NRPS-labelled BGC from checks (A)/(C) entirely and made
    # check (A) false-positive-flag them as "undeclared" even when the label already agreed —
    # reproduced live against the real curated map with a realistic lowercase "t1pks" label.
    # Matches this project's established case-insensitivity-bug-family fix pattern.
    classes_ci = {k.lower(): k for k in classes}
    skip_ci = {s.lower() for s in skip}

    tb = _find(pkg, "4_triage_board.csv")
    gbg = _find(pkg, "gene_by_gene_all_bgcs.csv")
    if not (tb and gbg):
        return [], {"error": "missing inputs (triage_board / gene_by_gene)", "n_bgc": 0, "n_flagged": 0}

    doms_by_bgc = defaultdict(set)
    for g in _rows(gbg):
        for d in re.split(r"[;|]", g.get("sec_met_domains", "") or ""):
            d = d.strip()
            if d:
                doms_by_bgc[g["bgc_id"]].add(d)

    tri = _rows(tb)
    out = []
    kind_counts = defaultdict(int)
    for r in sorted(tri, key=lambda x: int(float(x.get("Rank") or 9999))):
        bid = r["BGC_ID"]
        label = (r.get("Products", "") or "")
        label_toks = [t.strip() for t in re.split(r"[;,]", label) if t.strip()]
        label_toks_ci = {t.lower() for t in label_toks}
        doms = doms_by_bgc.get(bid, set())
        if not doms:
            continue

        findings = []

        # (A) undeclared domain-strong class
        for cls, spec in classes.items():
            if cls.lower() in label_toks_ci:
                continue
            wanted = spec["specific_domains"] if spec.get("require_specific") else spec["discriminating_domains"]
            present = _domains_present(doms, wanted)
            if len(present) >= spec.get("min_domains", 1):
                findings.append({"kind": "undeclared_strong", "cls": cls, "present": present})

        # (B) thiopeptide upgrade
        if label_toks_ci & {"azole-containing-ripp", "ripp", "ripp-like"}:
            tp = _domains_present(doms, ["Thiopeptide_F_RRE", "TIGR03882"])
            if tp and not any(f["cls"] == "thiopeptide" for f in findings):
                findings.append({"kind": "thiopeptide_upgrade", "cls": "thiopeptide", "present": tp})

        # (C) label lacks its own diagnostic domain — non-skip classes only
        for lt in label_toks:
            lt_ci = lt.lower()
            if lt_ci in skip_ci or lt_ci not in classes_ci:
                continue
            cls = classes_ci[lt_ci]
            spec = classes[cls]
            wanted = spec["specific_domains"] if spec.get("require_specific") else spec["discriminating_domains"]
            present = _domains_present(doms, wanted)
            if len(present) < spec.get("min_domains", 1):
                findings.append({"kind": "label_unsupported", "cls": cls, "present": present})

        if findings:
            for f in findings:
                kind_counts[f["kind"]] += 1
            out.append({"bgc_id": bid, "locator": _locator(r), "label": label, "findings": findings})

    summary = {"n_bgc": len(tri), "n_flagged": len(out), "kinds": dict(kind_counts)}
    return out, summary


def render(out, summary, cmap):
    classes = cmap["classes"]; skip = cmap["skip_domain_check"]["classes"]
    emit(f"# reclass-check (curated map: {len(classes)} classes, {len(skip)} skip-domain)", f"# [store-backed: gene_by_gene_all_bgcs.csv + triage_board.csv | curated map JSON]", f"# LIMIT: motif-on-precursor half (mycofactocin IDGMCGVY) NOT run — needs region-GBK CDS seqs", f"# CLASS_DISCREPANCY = review prompt, capacity-level only, NOT a reclassification verdict", sep="\n")
    emit()
    if summary.get("error"):
        emit("ERROR:", summary["error"], file=sys.stderr); return 1
    for e in out:
        emit(f"CLASS_DISCREPANCY  {e['locator']}", f"    antiSMASH label : {e['label'][:60]}", sep="\n")
        for f in e["findings"]:
            if f["kind"] == "undeclared_strong":
                emit(f"    undeclared class: {f['cls']}  (specific domains present: {', '.join(f['present'])})")
            elif f["kind"] == "thiopeptide_upgrade":
                emit(f"    UPGRADE azole->thiopeptide  (present: {', '.join(f['present'])})")
            elif f["kind"] == "label_unsupported":
                p = "none" if not f["present"] else ", ".join(f["present"])
                emit(f"    label '{f['cls']}' weakly supported  (specific domains present: {p})")
        emit()
    emit(f"# {summary['n_flagged']}/{summary['n_bgc']} BGC(s) flagged for reclass review")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pkg")
    ap.add_argument("--map", default="reclass_discriminating_domains.json")
    a = ap.parse_args()
    cmap = _read_json(a.map, encoding="utf-8")
    out, summary = analyze(a.pkg, cmap)
    sys.exit(render(out, summary, cmap))
