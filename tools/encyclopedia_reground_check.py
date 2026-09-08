#!/usr/bin/env python3
"""encyclopedia_reground_check.py — mechanize per-volume re-grounding of the Encyclopedia.

The Technical Manual Encyclopedia carries a per-volume colophon claiming its facts were
"verified against the running engine" at some bundle/engine version. When the engine moves on,
those colophons go stale — but bumping them without re-verifying would falsely claim re-grounding.

This tool re-verifies the *mechanically checkable* claims each volume makes (counts, constants,
thresholds, named symbols) against the live engine source, and reports per volume:
    OK     — every checkable claim still holds at the current engine; colophon is safe to bump
    DRIFT  — a checkable claim no longer matches; FIX the prose before bumping
    EYES   — claims that are real but not auto-checkable (verify by hand before bumping)

It changes no files. Run it from a tree that has both mamey/ and the encyclopedia HTML.

Usage:  tools/encyclopedia_reground_check.py [--root .] [--json]
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, json, pathlib, re, sys


def _src(root: pathlib.Path, rel: str) -> str:
    p = root / rel
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _count_dict(text: str, name: str) -> int:
    m = re.search(name + r"\s*[:=]\s*\{(.*?)\n\}", text, re.S)
    if not m:
        return -1
    return len(re.findall(r'^\s*[\"\']([A-Za-z0-9_\- ]+)[\"\']\s*:', m.group(1), re.M))


def _count_seq(text: str, name: str) -> int:
    m = re.search(name + r"\s*=\s*[\[{](.*?)[\]}]", text, re.S)
    if not m:
        return -1
    return len(re.findall(r'\"[a-z0-9_\- ]+\"', m.group(1)))


def build_checks(root: pathlib.Path):
    """Return {volume: [(label, ok_bool_or_None, detail), ...]}. None = EYES (manual)."""
    scoring = _src(root, "mamey/scoring.py")
    scans = _src(root, "mamey/source_scans.py")
    rggmci = _src(root, "mamey/rggmci.py")
    assembly = _src(root, "mamey/assembly.py")

    def has(rel, sym):
        return sym in _src(root, rel)

    def any_has(sym, rels):
        return any(sym in _src(root, r) for r in rels)

    tiers_ok = all(f">= {n}" in assembly for n in (70, 45, 20))
    cctt = _count_dict(scans, "CCTT_PATTERNS")
    ab, af, nov = (_count_seq(scoring, k) for k in ("AB_KEYWORDS", "AF_KEYWORDS", "NOVELTY_KEYWORDS"))
    rg = {m.group(1): int(m.group(2)) for m in re.finditer(r"([A-Z_]*(?:GAP|SPAN|HUB|DEGREE)[A-Z_]*)\s*=\s*(\d+)", rggmci)}
    rg_ok = (rg.get("ADJ_MAX_LOCUS_GAP") == 30 and rg.get("ADJ_MAX_SPAN") == 400
             and rg.get("RGGMCI_MAX_HUB_DEGREE") == 4)

    eng_mods = list((root / "mamey").glob("*.py"))
    scan_funcs = sum(len(re.findall(r"def scan_[a-z0-9_]+\(", _src(root, m.name and f"mamey/{m.name}"))) for m in eng_mods)

    C = {}
    C["I — Foundations"] = [
        ("assembly tiers 70/45/20", tiers_ok, "GOOD>=70 MODERATE>=45 POOR>=20"),
        ("corrected-count formula present", "Interior" in assembly or any_has("corrected", ["mamey/assembly.py", "mamey/bgc_inventory.py"]), "Interior + ½Edge + ¼FC"),
        ("standing exclusions (NAPAA/hglE-KS/saccharide)", any_has("NAPAA", ["mamey/scoring.py", "mamey/standing_rules.py"]), "permanent downgrades"),
    ]
    C["II — Mamey engine"] = [
        ("assembly tier computation 70/45/20", tiers_ok, "engine view"),
        (f"scan_* functions present (found {scan_funcs})", scan_funcs >= 10, "ten-scan roster"),
        ("_edge_status boundary rule", any_has("_edge_status", ["mamey/bgc_inventory.py", "mamey/assembly.py", "mamey/parsers.py"]), None),
    ]
    C["III — Sapote layer"] = [
        ("AB/AF/novelty scoring axes present", ab > 0 and af > 0 and nov > 0, f"{ab}/{af}/{nov}"),
        ("RG-GMCI rescue present", bool(rggmci), None),
        ("lead-tier thresholds present", "TIER" in scoring, None),
        ("guard composition order", None, "verify guard stack order by hand"),
    ]
    C["IV — Detection & triggers"] = [
        ("fifteen CCTT families", cctt == 15, f"found {cctt}"),
        ("RG-GMCI constants gap30/span400/hub4", rg_ok, str(rg)),
        ("6 AB / 2 AF diagnostic subsets", None, "verify diagnostic subset partition by hand"),
        ("3 promiscuous families", None, "verify by hand"),
        ("TFBS 300 bp window", any_has("300", ["mamey/source_scans.py", "mamey/tfbs.py"]), None),
    ]
    C["V — Scoring & DAPR"] = [
        ("AB keywords = 18", ab == 18, f"found {ab}"),
        ("AF keywords = 17", af == 17, f"found {af}"),
        ("novelty keywords = 11", nov == 11, f"found {nov}"),
        ("TIER1_FLOOR_EXCLUDED_PREFIXES present", "TIER1_FLOOR_EXCLUDED_PREFIXES" in scoring, None),
        ("PC-12 concordance gate", any_has("PC-12", ["mamey/scoring.py", "mamey/concordance.py"]) or any_has("PC12", ["mamey/scoring.py"]), None),
    ]
    C["VI — Deliverables"] = [
        ("strain_display_label()", any_has("strain_display_label", ["mamey/figure_policy.py", "mamey/labels.py", "mamey/render_brief.py"]), None),
        ("cap-40 figure policy (CAP=40)", bool(re.search(r"CAP\s*=\s*40\b", _src(root, "mamey/render_brief.py"))), "cap-40; lives in render_brief.py not figure_policy.py"),
        ("build_modeb_deepdive.py present", (root / "tools/build_modeb_deepdive.py").exists(), None),
        ("ingest_package.py merge + schema gate", (root / "tools/ingest_package.py").exists(), None),
    ]
    C["VII — Operations & release"] = [
        ("four-tier make_public_tier.sh", (root / "tools/make_public_tier.sh").exists(), None),
        ("version single-source-of-truth", "bundle_version" in _src(root, "pyproject.toml"), None),
        ("derive/resolve release fns + PUBLIC-refused asymmetry", None, "verify guard asymmetry by hand"),
    ]
    C["VIII — Reference & apparatus"] = [
        ("three denominator_type values", None, "verify denominator_type enum by hand"),
        ("nine KCB BGCRecord fields", None, "verify BGCRecord KCB field count by hand"),
        ("registry_inventory SSOT present", bool(list(root.glob("registry_inventory*")) + list((root/"mamey/data").glob("registry_inventory*"))), None),
    ]
    C["IX — Non-actinomycete (worked example)"] = [
        ("scoring is version-pinned to 1.9.81 (DO NOT bump scoring numbers)", None,
         "colophon already flags this honestly; structural framework re-checkable, scores are NOT"),
    ]
    return C


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    root = pathlib.Path(a.root).resolve()
    checks = build_checks(root)

    verdicts = {}
    for vol, items in checks.items():
        auto = [ok for _, ok, _ in items if ok is not None]
        if any(ok is False for ok in auto):
            verdicts[vol] = "DRIFT"
        elif any(ok is None for _, ok, _ in items):
            verdicts[vol] = "OK*" if all(ok for ok in auto) else "DRIFT"
        else:
            verdicts[vol] = "OK"

    if a.json:
        emit(json.dumps({v: {"verdict": verdicts[v],
                              "checks": [{"label": l, "auto": ok, "detail": d} for l, ok, d in checks[v]]}
                          for v in checks}, indent=2))
        return 0

    emit(f"Encyclopedia re-grounding check  (engine source: {root})", "  OK = all checkable claims hold · OK* = checkable claims hold, has manual-eyes items · DRIFT = fix prose first\n", sep="\n")
    for vol, items in checks.items():
        emit(f"[{verdicts[vol]:5}] Volume {vol}")
        for label, ok, detail in items:
            mark = "  ✓ " if ok is True else ("  ✗ " if ok is False else "  · ")
            tag = "" if ok is not None else "  (EYES)"
            emit(f"{mark}{label}{tag}" + (f"   [{detail}]" if detail else ""))
        emit()
    drift = [v for v, x in verdicts.items() if x == "DRIFT"]
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
