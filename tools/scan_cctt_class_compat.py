#!/usr/bin/env python3
"""scan_cctt_class_compat.py — cohort-wide CCTT-trigger vs product-class compatibility scan (N-05/A-04).

Class-definitive CCTT triggers (T43-BLA, T43-LAN, …) should co-occur with the antiSMASH product class they
imply. When a class-defining trigger fires on a BGC whose product class is incompatible (e.g. T43-BLA on a
terpene — the A4 case), the trigger is firing on a single token without corroborating context. This scan
sizes that gap across a cohort BEFORE any piecemeal per-trigger fix, so the generalized corroboration
requirement is driven by evidence rather than guessed.

It is a DIAGNOSTIC (does not change scoring). Reads manifest.json files (cctt.per_bgc + per-BGC products).

Usage:
    python3 tools/scan_cctt_class_compat.py <manifest_or_dir> [more …]
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import json
import os
import sys
import glob
from collections import defaultdict


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)


# Make the bundle root importable when run as `python3 tools/scan_cctt_class_compat.py` (no PYTHONPATH set).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Single source of truth: the compat map + corroboration rule live in the engine; this tool only aggregates.
from mamey.source_scans import CCTT_CLASS_COMPAT, CCTT_PROMISCUOUS, cctt_trigger_corroborated

# (kept for the --help text / standalone readers; the live values come from the engine import above)
PROMISCUOUS = CCTT_PROMISCUOUS
TRIGGER_COMPAT = CCTT_CLASS_COMPAT


def _manifests(args):
    out = []
    for a in args:
        if os.path.isdir(a):
            out += glob.glob(os.path.join(a, "**", "manifest.json"), recursive=True)
        elif a.endswith(".json"):
            out.append(a)
    return sorted(set(out))


def _corroborated(trigger, products):
    return cctt_trigger_corroborated(trigger, products)


def scan(manifests):
    fired = defaultdict(int)          # trigger -> total firings
    uncorr = defaultdict(int)         # trigger -> uncorroborated firings
    examples = defaultdict(list)      # trigger -> [(strain, bgc, products)]
    n_strain = 0
    for mp in manifests:
        try:
            m = _read_json(mp)
        except Exception:
            continue
        sid = m.get("strain_id", os.path.basename(os.path.dirname(mp)))
        cctt = (m.get("source_scans") or {}).get("cctt") or {}
        per_bgc = cctt.get("per_bgc") or cctt.get("bgc_coupling") or {}
        if not per_bgc:
            continue
        n_strain += 1
        prod_by_bgc = {b.get("bgc_id"): (b.get("products") or []) for b in m.get("bgcs", [])}
        for bgc_id, trigs in per_bgc.items():
            products = prod_by_bgc.get(bgc_id, [])
            for t in trigs:
                if t in PROMISCUOUS:
                    continue
                fired[t] += 1
                if t in TRIGGER_COMPAT and not _corroborated(t, products):
                    uncorr[t] += 1
                    if len(examples[t]) < 12:
                        examples[t].append((sid, bgc_id, ";".join(products)[:60]))
    return n_strain, fired, uncorr, examples


def main():
    if len(sys.argv) < 2:
        emit(__doc__)
        return 2
    mans = _manifests(sys.argv[1:])
    n_strain, fired, uncorr, examples = scan(mans)
    emit(f"# CCTT-vs-class compatibility scan — {n_strain} strain(s), {len(mans)} manifest(s)\n", f"{'trigger':34s} {'fired':>6s} {'uncorrob.':>10s}  rate", sep="\n")
    emit("-" * 64)
    total_f = total_u = 0
    for t in sorted(fired, key=lambda x: -uncorr.get(x, 0)):
        f, u = fired[t], uncorr.get(t, 0)
        total_f += f; total_u += u
        flag = "  <-- class-defining" if t in TRIGGER_COMPAT else "  (promiscuous/ungated)"
        rate = f"{(100*u/f):.0f}%" if f else "-"
        emit(f"{t:34s} {f:6d} {u:10d}  {rate:>4s}{flag if u else ''}")
    emit("-" * 64)
    total_rate = f"{(100*total_u/total_f):.0f}%" if total_f else "-"
    emit(f"{'TOTAL (class-defining only)':34s} {total_f:6d} {total_u:10d}  {total_rate}")
    if total_u:
        emit("\n## Context-uncorroborated firings (candidate false positives):")
        for t in sorted(examples):
            if not examples[t]:
                continue
            emit(f"\n### {t} — {uncorr[t]} uncorroborated")
            for sid, bgc, prods in examples[t]:
                emit(f"  {sid:12s} {bgc:8s} products=[{prods}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
