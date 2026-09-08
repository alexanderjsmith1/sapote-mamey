#!/usr/bin/env python3
"""figure_check.py — HARD pre-render gate for tree FIGURES (the render inputs), sibling to
tree_sanity_check.py (which gates the TREE topology).

Exists because on 2026-09-01 a figure went out with a query tip missing its host marker —
a defect the operator had NOTICED, captioned as a "nit", and shipped anyway. The tree gates cannot
catch this class: they check branches, not what the renderer will draw. This tool checks the render
inputs mechanically, so a missing marker / mangled label / undeclared omission is a refusal, not a
caption footnote. Rule of use: a FAIL here means DO NOT render or send; fix the inputs first.

Checks (each maps to a figure defect that reached a rendered figure at least once):
  F1 MARKER_COVERAGE   every query tip (AS/SID, non-outgroup) has a hostmap entry
                       (2026-09-01: two query tips had none -> figure sent with bare tips)
  F2 KNOWN_CATEGORIES  every hostmap value is a known render category
                       (a typo'd category silently draws NO marker)
  F3 LABEL_HYGIENE     no assembler cruft (SID#_SID#.c#, SID#_tig#, _supercont#, _DNA_),
                       no BARE 'AS'/'AS_sp' tips that lost their strain number
                       (2026-09-01: 11 tips rendered as 'Streptomyces sp AS')
  F4 LABEL_VERBOSITY   tip labels below a length ceiling (default 60 chars)
                       (host clauses like 'Streptomyces-Hymenoptera-Unidentified-New-Jersey')
  F5 OMISSIONS_DECLARED if TREE_SPEC.json (in --spec or beside the treefile's tree dir) declares
                       omitted_strains, the caller MUST acknowledge them via --omitted so the
                       caption names them (Alex convention 2026-09-01)

Usage:
  figure_check.py <labeled.treefile> [--hostmap hostmap.json] [--spec TREE_SPEC.json]
                  [--omitted "AS-NNN (...reason...)"] [--max-label-len 60] [--no-marker-checks]
Exit 0 = PASS (render may proceed) · 2 = FAIL (offenders listed; do NOT render/send).
Importable: check(...) returns (ok, msg) for render tools to call directly.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, json, os, re, sys

KNOWN_CATEGORIES = {"bumblebee", "honeybee", "other bee", "wasp", "ant", "moss",
                    "other substrate", "mushroom", "hymenoptera (unresolved)"}
_CRUFT = [
    (re.compile(r"SID\d+_SID\d+(\.c\d+)?"), "doubled SID + contig token"),
    (re.compile(r"SID\d+_tig\d+"), "SID + assembler contig token"),
    (re.compile(r"_supercont[\d.]+"), "supercont suffix"),
    (re.compile(r"_DNA_"), "raw '_DNA_' header token"),
]
# a tip that mentions AS but carries no strain number = an identity that was LOST upstream
_BARE_AS = re.compile(r"(^|[_ ])AS([_ ]|$)(?!\d)")
_HAS_ID = re.compile(r"(?<![A-Za-z])(AS|SID)[-_ ]?\d+")


def _tips(treefile):
    return re.findall(r"[(,]([^(),:]+):", open(treefile, encoding="utf-8", errors="replace").read())


def check(treefile, hostmap=None, spec=None, omitted="", max_label_len=60, marker_checks=True):
    tips = _tips(treefile)
    host = {}
    if hostmap and os.path.exists(hostmap):
        host = json.load(open(hostmap))
    fails, lines = [], []

    is_og = lambda t: "outgroup" in t.lower()
    queries = [t for t in tips if _HAS_ID.search(t) and not is_og(t)]

    # F1 — every query tip has a marker entry
    if marker_checks and host:
        missing = [t for t in queries if t not in host]
        if missing:
            fails.append(("F1 MARKER_COVERAGE",
                          [f"{t}  (query tip with NO hostmap entry -> renders with no marker)" for t in missing]))
    # F2 — categories are known
    if marker_checks and host:
        bad = sorted({v for v in host.values() if v not in KNOWN_CATEGORIES})
        if bad:
            fails.append(("F2 KNOWN_CATEGORIES",
                          [f"'{v}' is not a render category -> its tips draw NO marker" for v in bad]))
    # F3 — label hygiene
    dirty = []
    for t in tips:
        for rx, why in _CRUFT:
            if rx.search(t):
                dirty.append(f"{t}  ({why})")
        if _BARE_AS.search(t) and not _HAS_ID.search(t):
            dirty.append(f"{t}  (BARE 'AS' -- strain number was LOST upstream; fix at source)")
    if dirty:
        fails.append(("F3 LABEL_HYGIENE", dirty))
    # F4 — verbosity
    long_ = [f"{t}  ({len(t)} chars > {max_label_len})" for t in tips if len(t) > max_label_len]
    if long_:
        fails.append(("F4 LABEL_VERBOSITY", long_))
    # F5 — omissions declared
    if spec is None:
        cand = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(treefile))), "TREE_SPEC.json")
        cand2 = os.path.join(os.path.dirname(os.path.abspath(treefile)), "TREE_SPEC.json")
        spec = cand2 if os.path.exists(cand2) else (cand if os.path.exists(cand) else None)
    if spec and os.path.exists(spec):
        om = json.load(open(spec)).get("omitted_strains") or {}
        unacked = [s for s in om if s not in (omitted or "")]
        if unacked:
            fails.append(("F5 OMISSIONS_DECLARED",
                          [f"{s} is omitted per TREE_SPEC but not acknowledged for the caption "
                           f"(pass --omitted naming it): {om[s][:80]}" for s in unacked]))

    lines.append(f"figure_check: {len(tips)} tips · {len(queries)} query tips · "
                 f"hostmap={'%d entries' % len(host) if host else 'none supplied'}")
    if not fails:
        lines.append("  PASS — render inputs are figure-clean.")
        return True, "\n".join(lines)
    lines.append("  ***** FAIL *****")
    for kind, items in fails:
        lines.append(f"  [{kind}]")
        for it in items:
            lines.append(f"     {it}")
    lines.append("  ACTION: fix the inputs (hostmap/labels/omission ack) and re-run. Do NOT render or "
                 "send a FAILing figure — a known defect is a stop, not a caption footnote.")
    return False, "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="HARD pre-render figure gate (inputs the renderer will draw).")
    ap.add_argument("treefile")
    ap.add_argument("--hostmap")
    ap.add_argument("--spec")
    ap.add_argument("--omitted", default="")
    ap.add_argument("--max-label-len", type=int, default=60)
    ap.add_argument("--no-marker-checks", action="store_true",
                    help="skip F1/F2 for trees that legitimately have no host markers")
    a = ap.parse_args()
    ok, msg = check(a.treefile, hostmap=a.hostmap, spec=a.spec, omitted=a.omitted,
                    max_label_len=a.max_label_len, marker_checks=not a.no_marker_checks)
    emit(msg)
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
