#!/usr/bin/env python3
"""modeb_evidence_gate.py — deterministic Mode B evidence-governance gate (v9.7.354).

WHY THIS EXISTS. External review (Codex, 2026-08-06) caught a Mode B card that was excellent prose
but an inadmissible promotion: it fused two distinct biosynthetic grammars (tetramate vs tetronate —
an `FkbH + discrete ACP` pair supports glyceryl-S-ACP / TETRONATE chemistry, NOT an HSAF/PTM
"hallmark starter"), promoted itself to "authoritative / good confidence / novel congener /
strongest lead" while admitting no fresh per-gene BLASTP existed, and back-attributed a strain's
measured activity to an unverified locus. This gate turns that review's governance state machine into
a DETERMINISTIC lint so the same class of over-promotion cannot ship silently.

It does NOT judge biology and does NOT prove a card correct. It flags the LINGUISTIC + STRUCTURAL
signatures of over-promotion and forces a card to EARN promotion by clearing an admission gate. Same
spirit as the rest of Sapote-Mamey: judgment deferred, class-level, HOLD over a polished narrative.

State machine enforced (from the review):
  1. A card that claims promotion ("promoted / authoritative / lead / good confidence / novel
     congener / dedicated exporter / near-complete") MUST clear the admission gate:
       - a fresh per-gene BLASTP channel is present (U = 0), AND
       - it separates OBSERVATION / INFERENCE / ALTERNATIVE / FALSIFIER.
     Otherwise status is forced to HOLD and the promotion words are violations.
  2. Never merge chemically distinct motif grammars: an HSAF/PTM/tetramate IDENTITY claim that
     co-occurs with tetronate / `FkbH`+`ACP` signals — without an explicit class-conflict
     adjudication — is a CONFLICT violation.
  3. KCB / BiG-SCAPE / %identity establish family resemblance or cohort divergence only — a
     "novel congener" / "real novelty" read built on them (AS-private 2-member family, one
     megasynthase %id, weak KCB coverage) is a NOVELTY violation. Permitted: "divergent within the
     surveyed cohort; chemical novelty unresolved."
  4. Strain activity is independent of a BGC unless linked by fraction/metabolite correlation PLUS
     genetic or heterologous validation — otherwise a "most consistent with … activity / strongest
     antifungal lead" phrasing is an ACTIVITY_INHERITANCE violation.
  5. Contradiction audit: arithmetic/denominator mismatch, Edge-vs-completeness, assay-type conflation.

Public API:
    assess_modeb_card(text, has_fresh_blastp=None) -> ModeBGateReport
    ModeBGateReport.status      -> "ADMISSIBLE" | "HOLD"
    ModeBGateReport.violations  -> list[Violation(kind, excerpt, remedy)]
    ModeBGateReport.permitted_verdict -> a HOLD-shaped verdict string when status == HOLD

CLI:  python modeb_evidence_gate.py <card.md|->  [--fresh-blastp yes|no]
Exit: 0 if ADMISSIBLE, 2 if HOLD (so a caller can gate on it).
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import re, sys, argparse
from dataclasses import dataclass, field

# Words that assert PROMOTION / high confidence (the review's forbidden-word set while U>0).
PROMOTION = re.compile(r"\b(promoted|authoritative|confirmed|strongest (?:lead|antifungal)|"
                       r"good confidence|high confidence|near[- ]complete|full backbone|"
                       r"novel congener|dedicated (?:export|exporter|self-protection)|definitive|"
                       r"lead card)\b", re.I)
# an explicit HOLD is the honest state
HOLD_DECLARED = re.compile(r"\b(HOLD|PENDING|candidate review|unresolved|not (?:yet )?establish)", re.I)

# fresh per-gene BLASTP evidence present (U = 0)
BLASTP_FRESH = re.compile(r"\b(per-gene BLASTP|exact-current .*BLASTP|fresh .*BLASTP|BLASTP panel .*(?:present|current)|U\s*=\s*0)\b", re.I)
BLASTP_MISSING = re.compile(r"\b(no .*BLASTP|BLASTP .*(?:missing|absent|stale|pending)|without .*BLASTP|U\s*[>=]\s*1)\b", re.I)

# structural sections the review requires for a promoted card
SECTIONS = {"OBSERVATION": re.compile(r"\bobservation\b", re.I),
            "INFERENCE":   re.compile(r"\binference\b", re.I),
            "ALTERNATIVE": re.compile(r"\balternativ", re.I),
            "FALSIFIER":   re.compile(r"\bfalsifier|would (?:overturn|falsify)\b", re.I)}

# motif grammars that must not be silently merged
PTM_IDENTITY = re.compile(r"\b(HSAF|PTM|polycyclic tetramate|tetramate|clifednamide)\b", re.I)
TETRONATE    = re.compile(r"\b(tetronate|FkbH|glycer(?:yl|ate)-S?-?ACP|discrete ACP)\b", re.I)
CONFLICT_OK  = re.compile(r"\b(class[- ]conflict|competing (?:hypothes|grammar|interpretation)|"
                          r"adjudicat|do not (?:yet )?establish|competing tetronate)\b", re.I)
IDENTITY_ASSERT = re.compile(r"\b(is (?:an? )?(?:HSAF|PTM|clifednamide)|the HSAF grammar|"
                             r"=\s*the HSAF|hallmark starter|establishes? (?:an? )?(?:HSAF|PTM|tetramate))\b", re.I)

# novelty from weak evidence
NOVELTY_CLAIM = re.compile(r"\b(novel(?:ty)? (?:read|congener)|real(?: novelty)? at the congener|genuinely novel)\b", re.I)
WEAK_EVIDENCE = re.compile(r"\b(two-member|2-member|AS-private|\d{1,2}/\d{2,} (?:genes|KCB)|"
                           r"one megasynthase|single megasynthase|87\.\d%|weak .*coverage)\b", re.I)

# activity inheritance
ACTIVITY_LINK = re.compile(r"\b(most consistent with .*activity|strongest antifungal|"
                           r"consistent with .*(?:anti-?candida|antifungal) activity|"
                           r"linked to .*activity|explains? .*activity)\b", re.I)
ACTIVITY_VALIDATED = re.compile(r"\b(fraction[- ]correlat|metabolite correlat|heterologous|"
                                r"knockout|gene deletion|genetic validation|MS/MS .*match)\b", re.I)
# v9.7.395: a validation TERM is not validation EVIDENCE when its own clause negates or defers it.
# Pre-fix, a bare term match anywhere in the card cleared the ACTIVITY_INHERITANCE gate — including
# the very sentence ADMITTING the validation is absent ("No heterologous expression or knockout
# data exist") or deferring it ("heterologous expression would be required") — reproduced live.
_VALIDATION_NEGATED_BEFORE = re.compile(
    r"\b(?:no|not|without|absent|lack(?:s|ing)?|pending|nor|missing|awaiting)\b[^.;\n]{0,60}$", re.I)
_VALIDATION_DEFERRED_AFTER = re.compile(
    r"^[^.;\n]{0,60}\b(?:would|needed|required|pending|awaits?|absent|lacking|missing|"
    r"remains? (?:to|un))\b", re.I)


def _validated_activity_link(text: str) -> bool:
    """True only if some validation term appears in an affirmed (non-negated, non-deferred) clause."""
    for m in ACTIVITY_VALIDATED.finditer(text):
        if _VALIDATION_NEGATED_BEFORE.search(text[max(0, m.start() - 80):m.start()]):
            continue
        if _VALIDATION_DEFERRED_AFTER.search(text[m.end():m.end() + 80]):
            continue
        return True
    return False

# contradiction-audit signals
ASSAY_INVIVO = re.compile(r"\b(in vivo|most[- ]active[- ]in[- ]vivo)\b", re.I)
ASSAY_CRUDE  = re.compile(r"\b(crude[- ]extract|whole[- ]cell|disk diffusion)\b", re.I)
EDGE = re.compile(r"\bedge\b", re.I)
COMPLETE = re.compile(r"\b(near[- ]complete|full backbone|complete pathway)\b", re.I)
FRAC = re.compile(r"\b(\d{1,3})\s*/\s*(\d{2,})\b")
DECIMAL_SHARE = re.compile(r"\b0\.(\d{2,3})\b")


@dataclass
class Violation:
    kind: str
    excerpt: str
    remedy: str


@dataclass
class ModeBGateReport:
    status: str
    violations: list = field(default_factory=list)
    permitted_verdict: str = ""
    def __str__(self):
        head = f"modeb_evidence_gate: status={self.status}  ({len(self.violations)} violation(s))"
        lines = [head]
        for v in self.violations:
            lines.append(f"  [{v.kind}] “{v.excerpt[:110]}”\n      -> {v.remedy}")
        if self.status == "HOLD":
            lines.append(f"\n  PERMITTED VERDICT: {self.permitted_verdict}")
        return "\n".join(lines)


def _first(pat, text, default=""):
    m = pat.search(text)
    return m.group(0) if m else default


def assess_modeb_card(text: str, has_fresh_blastp: bool | None = None) -> ModeBGateReport:
    """Lint a Mode B card's TEXT for admissibility. `has_fresh_blastp` (if given) overrides the
    text heuristic for whether an exact-current per-gene BLASTP channel exists (U=0)."""
    v: list[Violation] = []
    promotes = bool(PROMOTION.search(text))

    # evidence closure: is a fresh per-gene BLASTP channel present?
    if has_fresh_blastp is None:
        fresh = bool(BLASTP_FRESH.search(text)) and not bool(BLASTP_MISSING.search(text))
    else:
        fresh = bool(has_fresh_blastp)

    # (1) admission gate — promotion requires U=0 and the four sections
    if promotes and not fresh:
        v.append(Violation("ADMISSION_GATE",
                           _first(PROMOTION, text),
                           "no fresh per-gene BLASTP (U>0): forbidden to promote — status must be HOLD "
                           "PENDING EXACT-CURRENT PER-GENE BLASTP"))
    if promotes:
        missing = [name for name, pat in SECTIONS.items() if not pat.search(text)]
        if missing:
            v.append(Violation("STRUCTURE_MISSING",
                               "missing: " + ", ".join(missing),
                               "a promoted card must separate OBSERVATION / INFERENCE / ALTERNATIVE / FALSIFIER"))

    # (2) motif-grammar conflict — PTM/tetramate identity asserted alongside tetronate/FkbH signals
    # v9.7.395: CONFLICT_OK was searched over the WHOLE document — the same defeat the v9.7.371
    # fix closed for gate (3): its `do not (?:yet )?establish` branch matches routine claim-safety
    # hedging, so one unrelated hedge sentence anywhere in the card silently cleared a real
    # identity-vs-tetronate conflict (reproduced live). The adjudication must sit near the claim;
    # same window shape as gate (3): -60 before the anchoring assertion, +200 after.
    _anchor = IDENTITY_ASSERT.search(text) or (PTM_IDENTITY.search(text) if promotes else None)
    if _anchor and TETRONATE.search(text) and not CONFLICT_OK.search(
            text[max(0, _anchor.start() - 60):_anchor.end() + 200]):
        v.append(Violation("MOTIF_GRAMMAR_CONFLICT",
                           _first(IDENTITY_ASSERT, text) or _first(TETRONATE, text),
                           "tetramate != tetronate: FkbH+ACP supports glyceryl-ACP/tetronate chemistry; "
                           "state competing tetronate/hybrid-PKS/PTM hypotheses, do not synthesize one identity"))

    # (3) novelty from weak evidence
    # v9.7.371 fix: the disclaimer window was left-bounded (-60 chars before the novelty claim)
    # but RIGHT-UNBOUNDED -- text[start-60:] runs to the end of the WHOLE document. HOLD_DECLARED
    # matches "not (?:yet )?establish", which matches this project's own standard claim-safety
    # boilerplate ("does not establish product identity") that appears in essentially every real
    # Mode-B card. Reproduced live: a card asserting real novelty from weak (two-member AS-private,
    # one megasynthase) evidence correctly flagged HOLD/NOVELTY_FROM_WEAK_EVIDENCE on its own; the
    # SAME card with an unrelated disclaimer appended 200+ words later flipped to ADMISSIBLE/no
    # violations -- any card can silently defeat this gate just by containing the standard
    # boilerplate ANYWHERE later in the document, regardless of proximity to the actual claim.
    # Bounding the window on both sides requires the hedge to actually be near the claim.
    if NOVELTY_CLAIM.search(text) and WEAK_EVIDENCE.search(text) and not HOLD_DECLARED.search(
            text[max(0, (_nc := NOVELTY_CLAIM.search(text)).start()-60):_nc.end()+200]):
        v.append(Violation("NOVELTY_FROM_WEAK_EVIDENCE",
                           _first(NOVELTY_CLAIM, text),
                           "family/%identity/BiG-SCAPE show cohort divergence, not chemical novelty; "
                           "permitted: 'divergent within the surveyed cohort; chemical novelty unresolved'"))

    # (4) activity inheritance
    # v9.7.395: was `not ACTIVITY_VALIDATED.search(text)` — see _validated_activity_link.
    if ACTIVITY_LINK.search(text) and not _validated_activity_link(text):
        v.append(Violation("ACTIVITY_INHERITANCE",
                           _first(ACTIVITY_LINK, text),
                           "strain activity is independent of a BGC without fraction/metabolite correlation "
                           "PLUS genetic/heterologous validation; do not back-attribute"))

    # (5) contradiction audit
    if ASSAY_INVIVO.search(text) and ASSAY_CRUDE.search(text):
        v.append(Violation("ASSAY_CONFLATION", _first(ASSAY_CRUDE, text),
                           "a crude-extract whole-cell assay is not 'in vivo activity' — name the assay type"))
    if EDGE.search(text) and COMPLETE.search(text):
        v.append(Violation("EDGE_VS_COMPLETENESS", _first(COMPLETE, text),
                           "'edge' and 'near-complete/full backbone' cannot coexist without a defined "
                           "completeness test — a large backbone is not a complete pathway"))
    frac = FRAC.search(text)
    if frac:
        num, den = int(frac.group(1)), int(frac.group(2))
        for dm in DECIMAL_SHARE.finditer(text):
            share = float("0." + dm.group(1))
            if den and abs((num / den) - share) > 0.05:
                v.append(Violation("ARITHMETIC_MISMATCH",
                                   f"{num}/{den} vs {dm.group(0)}",
                                   f"{num}/{den} = {num/den:.3f}, not {dm.group(0)} — name the denominator each ratio uses"))
                break

    status = "HOLD" if v else "ADMISSIBLE"
    permitted = ""
    if status == "HOLD":
        permitted = ("HOLD — PENDING EXACT-CURRENT PER-GENE BLASTP AND ARCHITECTURE ADJUDICATION. "
                     "Report class-level resemblance / cohort divergence only; do not assert product "
                     "identity, congener novelty, activity linkage, or completeness. Judgment deferred.")
    return ModeBGateReport(status=status, violations=v, permitted_verdict=permitted)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Deterministic Mode B evidence-governance gate (NOT a fact-checker).")
    ap.add_argument("path", help="card file to lint, or '-' for stdin")
    ap.add_argument("--fresh-blastp", choices=["yes", "no"], default=None,
                    help="override: is an exact-current per-gene BLASTP channel present (U=0)?")
    a = ap.parse_args(argv)
    text = sys.stdin.read() if a.path == "-" else open(a.path, encoding="utf-8", errors="replace").read()
    fb = None if a.fresh_blastp is None else (a.fresh_blastp == "yes")
    rep = assess_modeb_card(text, has_fresh_blastp=fb)
    emit(rep)
    return 0 if rep.status == "ADMISSIBLE" else 2


if __name__ == "__main__":
    sys.exit(main())
