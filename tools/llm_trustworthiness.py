#!/usr/bin/env python3
"""llm_trustworthiness.py — "Is the LLM being trustworthy right now?"  (candidate module, v1 — F02 rework)

A DETERMINISTIC linter that scores the EVIDENCE-DISCIPLINE of a block of LLM-authored text (a Mode-B
card, a report section, a chat answer). It answers "is this WELL-CALIBRATED and EVIDENCE-BACKED?", NOT
"is this TRUE." It cannot verify facts — it flags the linguistic signatures of over-claiming, uncited
assertions, denominator-free metrics, verified-vs-reported conflation, and unhedged causal claims, and
suggests a hedge. Same spirit as the rest of Sapote-Mamey: judgment deferred, class-level, don't overclaim
(including about this module).

WHAT IT IS NOT: not a fact-checker, not an oracle, not a gate that can prove correctness. A LOW score means
"this text asserts more than it visibly supports" — a prompt to add evidence or hedge, not proof of error.
A HIGH score does NOT mean the content is true; a confident lie with a fake citation can still score high.

── v1 REWORK (external audit F02, v9.7.353 REJECT_AS_IS) ────────────────────────────────────────────
The v0 module treated a BARE LOCAL CLUSTER ID (``BGC001``) as an evidence anchor. A local BGC id NAMES
which locus is being discussed — it is a LOCATOR, not PROVENANCE for a claim ABOUT that locus. The bug:
``"BGC001 produces nystatin … confirmed producer"`` matched the evidence pattern via ``BGC001`` → the
sentence counted as "cited" → BOTH the uncited-strong-claim and verified-without-anchor checks were
suppressed → the over-claim scored 100/100 with 0 flags (it green-lit the exact thing it must catch).

Fixes:
  1. Evidence anchors are now TYPED and PROVENANCE-BEARING only (see EVIDENCE): a versioned genome/protein
     accession, a 7-digit MIBiG accession (``BGC0000115`` — NOT a local ``BGCnn``), a Pfam/TIGRFAM id, a
     file:line / data file, an actual check result (``exit N`` / ``n=N``), an explicit "per <table/ledger/
     master/registry/row>" provenance phrase, or a literature id (DOI / PMID / PMC). Matched case-sensitively
     so ordinary prose words (``pass``, ``figure``) do not masquerade as anchors.
  2. An uncited STRONG bioactivity/identity/production claim now costs enough to drop a sentence out of
     EVIDENCE-BACKED on its own; a "confirmed …" verify-word with no anchor stacks on top. The canonical
     over-claim ("BGCnn produces X … confirmed producer") therefore scores OVER-CLAIMING.
  3. A strong claim that is HEDGED ("may produce") or an HONEST non-verification disclosure ("I have not
     verified that BGCnn produces X") is NOT flagged — those are correctly class-level / honest.
Adversarial fixtures pinning all of the above ship in tests/test_llm_trustworthiness.py.

Public API:
    assess_trustworthiness(text, evidence_tokens=None) -> TrustReport
    TrustReport.verdict  -> "EVIDENCE-BACKED" | "HEDGES-NEEDED" | "OVER-CLAIMING"
    TrustReport.flags    -> list[Flag(kind, span, excerpt, suggestion)]
    TrustReport.score    -> 0..100 (calibration score; NOT a truth probability)

CLI:  python llm_trustworthiness.py <file.md|->  [--evidence tok1,tok2]
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import re, sys, argparse
from dataclasses import dataclass, field

# --- signals -------------------------------------------------------------------------------------
HEDGES = re.compile(r"\b(may|might|could|appears?|seems?|likely|possibl[ey]|approximately|~|about|"
                    r"candidate|class-level|judgment deferred|"
                    r"suggest\w*|indicat\w*|reported\w*|predict\w*|estimate\w*|unverified|"
                    r"I did not|not (?:yet )?(?:verified|checked|confirmed)|I don't know|unclear)\b", re.I)
OVERCONF = re.compile(r"\b(clearly|obviously|definitely|certainly|undoubtedly|guaranteed|proven|proof|"
                      r"without a doubt|of course|always|never|100%|fully confirmed)\b", re.I)
# strong biology/identity claims that Sapote-Mamey must keep class-level. `produc\w*` catches
# produces/producer/producing/production (v1: the bare noun "producer" was previously unmatched).
STRONG_CLAIM = re.compile(r"\b(is an? (?:antifungal|antibiotic|antibacterial)|produc(?:e|es|er|ed|ing|tion)|"
                          r"synthesi[sz]es|confirmed (?:to be|as|producer)|identical to|is the (?:same|product)|"
                          r"encodes the (?:biosynthesis of)|active against|inhibits)\b", re.I)
# a metric that ought to carry a denominator
METRIC = re.compile(r"(?<![\w.])(\d{1,3}(?:\.\d+)?\s?%|\b\d+\s+(?:of|out of)\s+\d+\b|\b\d{2,}\b)")
DENOM_NEARBY = re.compile(r"\b(of|/|out of|per|n\s*=|denominator|total)\b", re.I)
# causal assertions
CAUSAL = re.compile(r"\b(because|due to|caused by|as a result of|since it|which is why|the reason)\b", re.I)
# honest self-disclosure of NON-verification: "I have not verified", "we never checked", "I don't know if …".
# These are the OPPOSITE of over-claiming and must not be penalized (v0.1 fix for the negation false-positive).
HONESTY = re.compile(r"\b(?:I|we)\b[\w\s',]{0,24}\b(?:have\s+)?(?:not|never|did\s*not|didn'?t|do\s*not|don'?t|"
                     r"cannot|can'?t|could\s*not|couldn'?t|un(?:able|sure))\b[\w\s',]{0,24}"
                     r"\b(?:verif\w*|confirm\w*|check\w*|validat\w*|test\w*|know|knew|measur\w*|prov\w*)\b", re.I)
# a negation token immediately preceding a verify-word ("... not [yet] verified", "never confirmed")
NEG_BEFORE_VERIFY = re.compile(r"\b(?:not|never|no|without|cannot|can'?t|couldn'?t|didn'?t|don'?t|un)\b"
                              r"[\w\s',]{0,15}$", re.I)

# EVIDENCE anchors = TYPED, PROVENANCE-BEARING tokens ONLY (F02 v1 rework). A bare LOCAL cluster/region
# id (BGC001, NODE_10, region001) NAMES which locus is discussed but is NOT provenance for a claim ABOUT
# it, so it is deliberately EXCLUDED here. Matched case-SENSITIVELY (no re.I) so lowercase prose words
# ("pass", "figure", "table") cannot masquerade as anchors; the genuinely case-insensitive sub-patterns
# (file paths, "per <ledger>" phrases, figure refs) opt in individually via (?i:...).
EVIDENCE = re.compile(
    r"\b[A-Z]{2,4}_?\d{4,}\.\d+\b"                                   # versioned GenBank/RefSeq accession (WP_..., NZ_...)
    r"|\bGC[AF]_\d+\.\d+\b"                                          # assembly accession GCA_/GCF_
    r"|\bBGC\d{7}\b"                                                 # MIBiG accession (exactly 7 digits) — NOT local BGCnn
    r"|\bMIBiG\b|\bPF\d{5}\b|\bTIGR\d{5}\b"                          # database references
    r"|\bexit\s+\d+\b|\bn\s*=\s*\d+\b"                               # actual check result / explicit denominator
    r"|\b10\.\d{4,}/\S+|\bPMID:?\s*\d+\b|\bPMC\d+\b"                 # literature ids (DOI / PMID / PMC)
    r"|(?i:\S+\.(?:py|csv|json|tsv|md|treefile|xlsx|gbk)(?::\d+)?)"  # file / file:line
    r"|(?i:\bfile:line\b)"
    r"|(?i:\bper\s+[a-z][\w\s]*?(?:table|master|manifest|ledger|registry|row|workbook)\b)"  # provenance phrase
    # NB: a bare "figure N" reference is deliberately NOT an anchor (F02 v1) — it points at a display,
    # it is not provenance for a claim, exactly like a bare local BGCnn id.
)
VERIFY_WORD = re.compile(r"\b(verified|confirmed|checked|validated)\b", re.I)

VERDICTS = ("OVER-CLAIMING", "HEDGES-NEEDED", "EVIDENCE-BACKED")


@dataclass
class Flag:
    kind: str
    excerpt: str
    suggestion: str


@dataclass
class TrustReport:
    score: int
    verdict: str
    flags: list = field(default_factory=list)
    n_sentences: int = 0
    def __str__(self):
        head = (f"llm_trustworthiness: score={self.score}/100  verdict={self.verdict}  "
                f"({len(self.flags)} flag(s) over {self.n_sentences} sentence(s))")
        head += "\n  NOTE: this scores EVIDENCE-DISCIPLINE, not factual truth. Low = add evidence or hedge."
        lines = [head]
        for f in self.flags:
            lines.append(f"  [{f.kind}] “{f.excerpt[:90]}”\n      -> {f.suggestion}")
        return "\n".join(lines)


def _sentences(text):
    # crude splitter; good enough for linting prose/cards
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [s.strip() for s in parts if s.strip()]


def assess_trustworthiness(text, evidence_tokens=None):
    """Lint `text`. `evidence_tokens` (optional) = extra strings that count as valid citations
    (e.g. real accessions/paths the caller already knows are present). NOTE: a bare local BGC id is
    NOT a valid anchor here (F02 v1) — pass a real accession/path via evidence_tokens if you have one."""
    extra = re.compile("|".join(re.escape(t) for t in evidence_tokens)) if evidence_tokens else None
    sents = _sentences(text)
    flags = []

    def cited(s):
        return bool(EVIDENCE.search(s) or (extra and extra.search(s)))

    for s in sents:
        hedged = bool(HEDGES.search(s))
        honest = bool(HONESTY.search(s))   # honest "I have not verified/checked/…" — never penalize
        oc = OVERCONF.search(s)
        # 'never'/'always' are weak signals: suppress them inside an honest non-verification disclosure
        # ("I have not verified this and never checked it") so honesty doesn't read as over-claiming.
        if oc and not (oc.group(0).lower() in ("never", "always") and honest):
            flags.append(Flag("OVERCONFIDENT",
                              oc.group(0) + " … " + s,
                              "drop the intensifier or cite what makes it certain"))
        # UNCITED_STRONG_CLAIM: a bare strong bioactivity/identity/production claim with no typed anchor.
        # Suppressed when the sentence is HEDGED ("may produce") or an HONEST non-verification disclosure
        # ("I have not verified that BGCnn produces X") — those are correctly class-level / honest, not over-claims.
        if STRONG_CLAIM.search(s) and not cited(s) and not hedged and not honest:
            flags.append(Flag("UNCITED_STRONG_CLAIM", s,
                              "class-level it (‘candidate/…-family, judgment deferred’) or attach evidence "
                              "(accession/MIBiG-7-digit/file:line) — a bare local BGC id is not evidence"))
        for m in METRIC.finditer(s):
            window = s[max(0, m.start()-40): m.end()+40]
            # v9.7.374 fix: a bare percentage ("87% coverage") is itself a denominator-free
            # metric -- "%" only means /100, it does not disclose the underlying sample size N
            # this project's own convention requires (never-quote-a-metric-without-its-
            # denominator: numerator+denominator+scope). The old unconditional "%" exemption let
            # ANY percentage claim skip this check even with zero nearby n=/of-N context -- the
            # same shape of over-permissive carve-out this module's own F02 rework already fixed
            # once for bare local BGC ids. Percentages with genuine nearby scope (e.g. "87% (n=42)")
            # still pass via DENOM_NEARBY; only a truly bare percentage is now flagged.
            if not DENOM_NEARBY.search(window):
                flags.append(Flag("METRIC_NO_DENOMINATOR", m.group(0) + " … " + s,
                                  "state numerator AND denominator, or say ‘not counted’"))
                break
        if CAUSAL.search(s) and not cited(s) and not hedged:
            flags.append(Flag("UNVERIFIED_CAUSE", s,
                              "cite the basis, or hedge (‘possibly’, ‘I have not verified why’)"))
        # VERIFIED_WITHOUT_ANCHOR: only fires on an UN-negated, un-hedged, uncited verify-claim.
        # "I have not verified this" / "we never confirmed X" are honest disclosures, not over-claims (v0.1 fix).
        if not cited(s) and not honest:
            for vm in VERIFY_WORD.finditer(s):
                if NEG_BEFORE_VERIFY.search(s[max(0, vm.start() - 30):vm.start()]):
                    continue   # negated verify-word ("not [yet] verified") → a hedge, skip
                flags.append(Flag("VERIFIED_WITHOUT_ANCHOR", s,
                                  "say ‘reported/…’ instead of ‘verified’, or show the check (command/exit/PASS)"))
                break

    # score: start at 100, subtract per weighted flag, floor 0. F02 v1: an uncited strong claim (34) drops
    # a sentence out of EVIDENCE-BACKED on its own; stacked with a verify-word (22) it reaches OVER-CLAIMING.
    weights = {"UNCITED_STRONG_CLAIM": 34, "VERIFIED_WITHOUT_ANCHOR": 22, "UNVERIFIED_CAUSE": 14,
               "METRIC_NO_DENOMINATOR": 10, "OVERCONFIDENT": 8}
    score = 100 - sum(weights.get(f.kind, 8) for f in flags)
    score = max(0, min(100, score))
    verdict = "EVIDENCE-BACKED" if score >= 80 else ("HEDGES-NEEDED" if score >= 50 else "OVER-CLAIMING")
    return TrustReport(score=score, verdict=verdict, flags=flags, n_sentences=len(sents))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Lint LLM text for evidence-discipline (NOT truth).")
    ap.add_argument("path", help="file to lint, or '-' for stdin")
    ap.add_argument("--evidence", default="", help="comma-sep extra citation tokens that count as evidence")
    a = ap.parse_args(argv)
    text = sys.stdin.read() if a.path == "-" else open(a.path, encoding="utf-8", errors="replace").read()
    toks = [t.strip() for t in a.evidence.split(",") if t.strip()]
    rep = assess_trustworthiness(text, toks or None)
    emit(rep)
    return 0 if rep.verdict != "OVER-CLAIMING" else 2


if __name__ == "__main__":
    sys.exit(main())
