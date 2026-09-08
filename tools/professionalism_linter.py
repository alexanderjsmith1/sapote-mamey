#!/usr/bin/env python3
"""
professionalism_linter.py — post-hoc "professionalism" check for Sapote interpretive text
(Mode B cards, synopses, analysis write-ups, hand-offs).

Companion to tools/claim_safety_linter.py. Where that one catches *compound-identity* overclaims,
this catches the *rhetorical* failure modes that read as unprofessional and usually precede a wrong
conclusion: unhedged certainty, a problem/identity asserted with no evidence on the line, and a bare
metric with no denominator.

It is ADVISORY by design (professionalism warnings must never block a write). Exit 1 = findings,
0 = clean, so a CI/hook can surface them; wiring decides whether that is fatal (it should not be).

Rules (each false-positive-hardened; see tests):
  PRO1  unhedged certainty      "clearly/obviously/undoubtedly/definitely..." in interpretive prose
  PRO2  unverified assertion    "is a duplicate / is missing / is wrong / is identical" with NO evidence
                                token on the same line (hash, n=, ANI, %, accession, path, 'verified'...)
  PRO3  metric w/o denominator  a % or large count with no n= / of N / x/y on the line
  PRO4  identity w/o measure    "nearest/closest ... type/species is X" with no ANI/%/similarity number

Usage:  python tools/professionalism_linter.py FILE [FILE ...] [--json]
Import: from tools.professionalism_linter import lint_professionalism
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, json, re, sys
from pathlib import Path

# ---- PRO1: certainty adverbs that overclaim in interpretive text ----
_CERTAINTY = re.compile(
    r"\b(clearly|obviously|undoubtedly|definitely|plainly|certainly|indisputably|"
    r"without a doubt|of course|needless to say|it is obvious|proves that|proven that)\b", re.I)
# safe uses: "clearly labeled/defined/marked/named/visible/documented" are descriptive, not overclaims
_CERTAINTY_SAFE = re.compile(r"\b(clearly|plainly)\s+"
    r"(labell?ed|defined|marked|named|visible|documented|stated|separated|delimited)\b", re.I)

# ---- PRO2: problem / identity asserted with no evidence on the line ----
_ASSERT = re.compile(
    r"\b(?:is|are|was|were|it['’]s|they['’]re)\s+(?:a\s+|an\s+|the\s+)?"
    r"(duplicate|duplicates|defect|defective|broken|wrong|incorrect|missing|absent|identical|"
    r"the same|a bug|contaminated|corrupt|corrupted|invalid)\b", re.I)
# evidence tokens that make an assertion defensible on the same line
_EVIDENCE = re.compile(
    r"(\bn\s*=\s*\d|\b\d+\s*/\s*\d|\bof\s+\d|\bANI\b|\d+(\.\d+)?\s*%|md5|sha256|hash|"
    r"GC[AF]_\d|N[CZ]_[A-Z0-9]+\.\d|\baccession\b|\bbp\b|\bverified\b|\bmeasured\b|"
    r"\bconfirmed by\b|/[\w .-]+/|`[^`]+`)", re.I)

# ---- PRO3: metric without denominator (light; overlaps the denominator guardrail) ----
_METRIC = re.compile(r"\b\d+(\.\d+)?%|\b\d{3,}\s+(BGCs?|genomes?|regions?|strains?|copies|reads|contigs?)\b", re.I)
_DENOM = re.compile(r"n\s*=\s*\d|/\s*\d|\bof\s+\d|\d+\s*/\s*\d|\bper\b")
# a % that is an INTRINSIC pairwise metric (identity/ANI/coverage/GC) is self-denominated -> not PRO3
_SELF_DENOM_PCT = re.compile(
    r"(%\s*(id\b|ident|ANI|AAI|cov|coverage|GC|similarity|complete|contam)"
    r"|\b(id\b|ident\w*|ANI|AAI|cov\w*|coverage|GC|similarity|bootstrap|support|UFBoot|aLRT)"
    r"[^%\n]{0,15}\d+(\.\d+)?\s*%"
    r"|\b\d+(\.\d+)?\s*%\s*(id\b|ident\w*|ANI|AAI|cov\w*|coverage|similarity))", re.I)

# ---- PRO4: nearest/closest identity stated without a similarity number ----
_NEAREST = re.compile(r"\b(nearest|closest)\b[^.\n]{0,40}\b(type|species|relative|match|neighbou?r)\b", re.I)
_NUMBER  = re.compile(r"\d+(\.\d+)?\s*%|\bANI\b|\bAAI\b|\d+\s*/\s*\d+|similarity|identity")

def lint_professionalism(text: str):
    findings = []
    for i, ln in enumerate(text.splitlines(), 1):
        s = ln.strip()
        if not s or s.startswith("#") or s.startswith(">"):  # skip blank / headings / block quotes
            continue
        low = ln
        if _CERTAINTY.search(low) and not _CERTAINTY_SAFE.search(low):
            findings.append((i, "PRO1", "unhedged certainty — hedge (likely/consistent with) or cite evidence", s[:100]))
        if _ASSERT.search(low) and not _EVIDENCE.search(low):
            findings.append((i, "PRO2", "problem/identity asserted with no evidence on the line", s[:100]))
        if (_METRIC.search(low) and not _DENOM.search(low) and not _SELF_DENOM_PCT.search(low)
                and not s.startswith(("|",))):
            findings.append((i, "PRO3", "metric without a denominator (n= / of N / x/y)", s[:100]))
        if _NEAREST.search(low) and not _NUMBER.search(low):
            findings.append((i, "PRO4", "nearest/closest identity stated without a similarity number", s[:100]))
    return findings

def main(argv=None):
    ap = argparse.ArgumentParser(description="Advisory professionalism linter for Sapote write-ups.")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    allf = {}
    for fp in a.files:
        try:
            txt = Path(fp).read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            emit(f"cannot read {fp}: {e}", file=sys.stderr); continue
        f = lint_professionalism(txt)
        if f: allf[fp] = f
    if a.json:
        emit(json.dumps({k: [dict(line=l, rule=r, msg=m, text=t) for l, r, m, t in v]
                          for k, v in allf.items()}, indent=2))
    else:
        for fp, f in allf.items():
            for l, r, m, t in f:
                emit(f"{fp}:{l}: [{r}] {m}\n      {t}")
        n = sum(len(v) for v in allf.values())
        emit(f"\n[professionalism] {n} advisory finding(s) in {len(allf)} file(s)."
              if n else "[professionalism] clean.")
    return 1 if allf else 0

if __name__ == "__main__":
    raise SystemExit(main())
