#!/usr/bin/env python3
"""
claim_safety_linter.py — post-hoc claim-safety linter for Sapote interpretive text
(Mode B cards, synopses, layperson guides). Sprint-1 idea from the ChatGPT patch chat,
hardened against false positives.

The engine enforces claim-safety during generation; this is a *post-hoc* check that
catches overclaims that slipped through — a card that says "produces kirromycin" instead
of "biosynthetic capacity consistent with a kirromycin-like compound", or that names a
KCB anchor without the similarity-anchor ceiling.

It deliberately does NOT flag claim-safe constructions:
  - "produces a polyketide backbone"      (class-level capacity, not a compound identity)
  - "biosynthetic capacity consistent with kirromycin-like ..."
  - "kirromycin-like KCB similarity anchor"

Usage:
  python tools/claim_safety_linter.py card.md [--json]
  # or import: from tools.claim_safety_linter import lint_claim_safety
Exit 0 = clean, 1 = overclaim(s) found.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import json
import re
import sys
from pathlib import Path

# Class-level / capacity words that are SAFE to follow "produces". A compound name after
# "produces" is an identity overclaim; a class word is fine.
_SAFE_AFTER_PRODUCES = {
    "a", "an", "the", "this", "these", "its", "their",
    "polyketide", "peptide", "nonribosomal", "ribosomal", "terpene", "terpenoid",
    "siderophore", "lanthipeptide", "ripp", "ripps", "backbone", "backbones",
    "compounds", "metabolites", "metabolite", "scaffolds", "scaffold", "class",
    "secondary", "natural",
}

# Identity verbs split by strength (v9.7.125b, after the AS-XXX dogfood found a 100% FP rate
# on the bare copula in authored prose):
#   PRODUCTION verbs ("produces X") genuinely assert that the cluster makes compound X.
#   The COPULA ("is/are X") is overwhelmingly descriptive in prose ("is interior", "are routing")
#   and only asserts identity when X is an actual compound name.
_PRODUCTION_RE = re.compile(
    r"\b(?:produces|synthesizes|synthesises|yields|makes|biosynthesizes|assembles|elaborates|secretes)\s+([A-Za-z][A-Za-z0-9'\-]+)",
    re.IGNORECASE,
)
_COPULA_RE = re.compile(
    r"\b(?:is|are)\s+([A-Za-z][A-Za-z0-9'\-]+)",
    re.IGNORECASE,
)

# Descriptive / status / function words that follow a copula in scientific prose and are NEVER
# compound identities. Closed-class safety net for when no per-strain compound set is supplied.
# Derived from the AS-XXX batch-1 false-positive corpus (all 63 were words of this kind).
_DESCRIPTIVE_AFTER_COPULA = {
    "edge-status", "interior", "full-contig", "edge-truncated", "edge", "truncated",
    "assumed", "attributed", "captured", "complete", "present", "absent", "unknown",
    "unresolved", "inferred", "likely", "unlikely", "plausible", "diagnostic", "routing",
    "shared", "shared-reference-geometry", "typical", "atypical", "often", "sometimes",
    "genuine", "genuinely", "addressed", "also", "among", "appropriate", "correspondingly",
    "detected", "explicitly", "itself", "otherwise", "short", "worth", "warranted",
    "class-incompatible", "nrps-dominant", "protease-resistant", "consistent", "compatible",
    "responsible", "characteristic", "indicative", "suggestive", "limited", "partial",
    "located", "positioned", "flanked", "encoded", "annotated", "predicted", "observed",
    "associated", "required", "involved", "expressed", "conserved", "distinct", "similar",
    "novel", "rare", "common", "high", "low", "moderate", "strong", "weak", "claimed",
}

# KCB ceiling language that must accompany any KCB / knownclusterblast mention.
_ANCHOR_HINTS = (
    "similarity anchor", "similarity, not identity", "not a product identity",
    "product identity unresolved", "-like", "capacity consistent with",
    "kcb = similarity", "similarity not identity",
    # PATCH-045 (v9.7.128): abbreviated cards use shorter ceiling/no-KCB vocabulary that the
    # original list missed (18/18 false positives on AS-XXX abbreviated cards). These cover the
    # "no KCB at all" case and explicit ceiling phrases that already disclaim identity.
    "reference-dark", "reference dark", "no kcb", "kcb: none", "kcb none",
    "genomic ref", "boundary_concentrated", "cross_class", "zero interpretive weight",
    "candidate family similarit", "candidate-family similarit", "misanchor",
    "below the floor", "below floor", "below the 5,000 floor", "below 5,000 floor",
    "class context only", "concordant",
)

# Words that signal the sentence is already framed as capacity, exempting an identity verb.
_CAPACITY_FRAME = ("capacity consistent with", "-like", "consistent with a", "resembl", "anchor")
# v9.7.217 (#3 reopen): a DENIED production ("does not support that X produces Y") is not an overclaim.
# The robust cnames path early-returned `t in cnames` with no negation check, so correct §14 denials
# flagged MEDIUM. Guard both hit-testers with this before the cnames membership return.
_NEGATION_RX = re.compile(r"\b(?:does not|do not|doesn't|don't|cannot|can't|can not|no evidence|"
                          r"not support|not assert|does not assert|not claim|not that|rather than|instead of)\b", re.I)

# Local comparator/anchor and rejection frames can qualify an identity phrase.
# The two report paths share _identity_context so another clause cannot supply
# a hedge or denial for the matched claim.
_IDENTITY_FRAME_RX = re.compile(
    r"comparator|class anchor|family anchor|similarity anchor|similarity,?\s*not identity|"
    r"\bnot identity\b|\breject|overturn|not claimed|not transferred|downgrad|-like|resembl|"
    r"consistent with",
    re.IGNORECASE)


def _identity_context(text: str, start: int, end: int) -> str:
    """Keep hedge and denial evidence in the matched claim's clause.

    Preserve long local comparator frames, but do not borrow them across
    sentence boundaries, semicolons, or comma-led coordinating clauses.
    """
    boundary = re.compile(r"[;!?\n]|\.(?=\s)|—|,\s*(?:and|but|yet|while|whereas)\b", re.I)
    lo, hi = 0, len(text)
    for delimiter in boundary.finditer(text):
        if delimiter.end() <= start:
            lo = delimiter.end()
        elif delimiter.start() >= end:
            hi = delimiter.start()
            break
    return text[lo:hi]


_STANDARD_DISCLAIMER_LINE_RE = re.compile(
    r"^\s*>?\s*(?:Claim-safety:|KCB comparisons are similarity signals, not identity\.|Bioactivity links are mechanistic hypotheses requiring experimental validation\.)(?:\s|$)",
    re.IGNORECASE,
)


def _remove_standard_disclaimer_lines(text: str) -> str:
    """Remove generated safety boilerplate before linting.

    The boilerplate is itself the identity ceiling. Flagging it as an
    identity_overclaim creates noisy false positives on generated Mode B cards.
    """
    return "\n".join(
        line for line in text.splitlines()
        if not _STANDARD_DISCLAIMER_LINE_RE.search(line)
    )


# Emphasis / quote wrappers that sit INSIDE a sentence and carry no segmentation meaning for this
# module. Deleted (not spaced) so `produces **venezuelin**` reads as `produces venezuelin` while every
# period, bracket and backtick stays exactly where it was.
_EMPHASIS_RE = re.compile(r"(?<![A-Za-z0-9])([*_]{1,3})(?=\S)(.+?)(?<=\S)\1(?![A-Za-z0-9])", re.S)
_QUOTE_CHARS = str.maketrans("", "", '"\u201c\u201d\u2018\u2019')


def normalize_for_claim_detection(text: str) -> str:
    """v9.7.410 (CLAUDE_410 claimsafety linter normalize): return a DETECTION-ONLY copy of `text`
    with markdown/quote/bracket wrappers neutralized, zero-width characters dropped, and Unicode
    look-alikes folded to ASCII.

    Why this exists: `.409` landed `_normalize_for_detection` in mamey/claim_safety_gate.py, but the
    two entry points in THIS module — `lint_claim_safety` and `lint_claim_safety_report` — never got
    it, and they are the ones the seal gate runs. `mamey/seal_package.py::_gate_claim_safety` calls
    `lint_claim_safety`, so an overclaim written as `produces **venezuelin**`, with a Cyrillic `о`, or
    with a zero-width space inside the verb passed the SEAL while the gate's own `lint_text` caught
    the identical sentence. This function closes that divergence by delegating to the gate's
    already-calibrated implementation rather than adding a third, independently-drifting copy.

    Degrades to the raw text if mamey is not importable (bare `python tools/claim_safety_linter.py`
    from outside the bundle) — the linter then behaves exactly as it did in `.409`, never worse.
    """
    try:
        import sys as _sys
        from pathlib import Path as _Path
        _root = str(_Path(__file__).resolve().parents[1])
        if _root not in _sys.path:
            _sys.path.insert(0, _root)
        from mamey.claim_safety_gate import _normalize_for_detection
    except Exception:  # pragma: no cover - standalone / partial checkout
        return text
    # fold_wrappers=FALSE, deliberately. The gate's own docstring records why: this module "carries
    # its own calibrated hedge / sentence-boundary logic, and rewriting its brackets/emphasis would
    # corrupt that segmentation". Confirmed here — with fold_wrappers=True the shared normalizer turns
    # `)` into a newline, which truncates the sentence-scoped hedge window and made two shipped
    # documents fire falsely: the rendered citation-audit report ("is  tools" out of a file path) and
    # docs/reference/modeb_exemplars/nrps_exemplar.md, whose sentence says the region does **not**
    # make tetronasin and whose "similarity" hedge fell outside the truncated sentence.
    #
    # So take ONLY the de-obfuscation half — invisible-char strip and Unicode look-alike fold — and
    # handle emphasis/quote wrappers separately below, since those are the ones that actually hide a
    # compound name and neither carries segmentation meaning for this module's matchers.
    norm, _idx_map = _normalize_for_detection(text, fold_wrappers=False)
    norm = _EMPHASIS_RE.sub(r"\2", norm)
    return norm.translate(_QUOTE_CHARS)


# Compound-CLASS names (not specific-compound identities). These commonly follow "are"/"is"
# as "are angucycline-class" or "is an anthracycline-type" — class capacity, not identity.
# Calibration (v9.7.124, 343 real triage rows): every identity false-positive was a class name
# of this kind. A bare class name after an identity verb is capacity language, not an overclaim.
_COMPOUND_CLASS_NAMES = {
    "angucycline", "anthracycline", "aminoglycoside", "glycopeptide", "lipopeptide",
    "macrolide", "polyene", "polyketide", "tetracycline", "ansamycin", "enediyne",
    "butenolide", "betalactone", "thiopeptide", "lanthipeptide", "lassopeptide",
    "ionophore", "aminocoumarin", "nucleoside", "phosphonate", "furanone",
}

# Class-forming suffixes: a token ending in one of these is a class label, not a compound name.
_CLASS_SUFFIXES = ("-class", "cycline", "-type", "-like")


def _looks_like_compound(token: str) -> bool:
    """Heuristic: a lowercase non-class word after an identity verb is likely a compound name."""
    t = token.lower()
    if t in _SAFE_AFTER_PRODUCES:
        return False
    if t in _COMPOUND_CLASS_NAMES:
        return False  # a compound-class name is capacity language, not an identity
    if t.endswith(_CLASS_SUFFIXES):
        return False  # "angucycline", "macrolide-type", "kirromycin-like" → class, not identity
    # class suffixes that are not compound identities
    if t.endswith(("pks", "nrps", "ripp", "peptide")) and t not in ("bottromycin",):
        return False
    # plausible compound name: length >= 4, alphabetic-ish
    return len(t) >= 4 and re.match(r"^[a-z][a-z0-9'\-]+$", t) is not None


def lint_claim_safety(text: str, compound_names: set | None = None) -> list[str]:
    """Return a list of claim-safety findings (empty = clean).

    compound_names: optional set of the strain's actual KCB/MIBiG compound names. When supplied,
    an identity verb only flags if the following token is a real compound name — the exact signal
    that separates "is colibrimycin" (overclaim) from "is Edge-status" (descriptive). This is the
    robust path (recommended; the AS-XXX dogfood showed the heuristic alone is insufficient).
    When omitted, falls back to the production-verb + stop-list heuristic.
    """
    text = _remove_standard_disclaimer_lines(text)
    # v9.7.410 (CLAUDE_410 claimsafety linter normalize): fold obfuscation BEFORE any matcher runs,
    # using the gate's shared implementation. Disclaimer stripping stays on the ORIGINAL text above
    # so wrapper-folding can never split a boilerplate line and resurrect it as a finding.
    text = normalize_for_claim_detection(text)
    errors = []
    compound_load_error = getattr(compound_names, "load_error", None)
    if compound_load_error:
        errors.append(
            "compound-name evidence unreadable: "
            f"{compound_load_error.get('error_type', 'Error')}: "
            f"{compound_load_error.get('error', 'unknown read failure')} "
            "(robust claim-safety check unavailable)"
        )
    cnames = {c.lower() for c in compound_names} if compound_names else None

    def _flag(match, is_production: bool = False) -> bool:
        token = match.group(1)
        t = token.lower()
        context = _identity_context(text, match.start(), match.end())
        if _NEGATION_RX.search(context):
            return False  # denied production is not an overclaim (#3)
        context = context.lower()
        if any(frame in context for frame in _CAPACITY_FRAME):
            return False  # already framed as capacity/similarity
        # Clause-local hedge/rejection frame — a comparator/anchor name or
        # an explicitly rejected name is not an overclaim even when the frame sits before the copula.
        if _IDENTITY_FRAME_RX.search(context):
            return False
        if cnames is not None:
            if t in cnames:
                return True
            # BC2-CS-MULTIWORD (v9.7.395): lint_claim_safety_report()'s _identity_hit() builds a
            # multi-word probe (captured token + a short tail window) and tests substring
            # membership against cnames, so "is phosphonoacetic acid" matches the multi-word
            # compound "phosphonoacetic acid" even though the identity-verb regex only captures
            # the single leading token "phosphonoacetic". lint_claim_safety() — the function
            # actually wired into the BLOCKING seal gate (seal_package.py::_gate_claim_safety)
            # and judgment_store.py's write-time self-lint — never got this fix: it only tested
            # the bare single-word token, so a real multi-word compound-identity overclaim
            # ("BGC001 is phosphonoacetic acid") reached a sealed package as zero identity-
            # overclaim findings, while the report-only path caught it. Mirror the same probe
            # here so both entry points share one detection surface for the same input.
            tail = text[match.end():match.end() + 60]
            probe = (token + tail).lower().split(".")[0]
            if any(re.match(re.escape(cn) + r"(?![\w-])", probe) for cn in cnames):
                return True
            # CS-01 (v9.7.336): this used to `return t in cnames` for BOTH verb classes, which
            # inverted the check — supplying the strain's real compound list exempted every
            # compound NOT on the board, so a hallucinated name was the LEAST likely thing to be
            # caught ("produces zorbamycin / synthesizes vancomycin" linted clean).
            # The fix is verb-class-aware, and it is measured, not assumed:
            #   * PRODUCTION verbs (produces/synthesizes/yields) are inherently identity
            #     assertions. Fall through to the shape heuristic — this is where the escape was.
            #   * COPULA (is/are) is far noisier; the board really is the only discriminator
            #     between "is colibrimycin" and "is Edge-status". Removing the gate there fired
            #     192 findings on the 10 shipped claim-safe exemplars ("is that", "are read",
            #     "is expected"), so the gate is RETAINED for copula.
            if not is_production:
                return False
        # heuristic (also the fall-through for a production verb whose token is not on the board)
        if not _looks_like_compound(token):
            return False
        if t in _DESCRIPTIVE_AFTER_COPULA:
            return False
        return True

    # 1a) PRODUCTION verbs ("produces X") — strong assertion; flag a compound-shaped token.
    for m in _PRODUCTION_RE.finditer(text):
        if _flag(m, is_production=True):
            errors.append(f"possible identity overclaim: '{m.group(0)}' "
                          f"(use capacity/similarity framing)")

    # 1b) COPULA ("is/are X") — descriptive in prose. With a compound set, flag only real compounds.
    #     Without one, require the token to be compound-shaped AND not a known descriptive word.
    for m in _COPULA_RE.finditer(text):
        token = m.group(1)
        t = token.lower()
        # the copula is far noisier; with no compound set, only flag clearly compound-shaped tokens
        if cnames is None and t in _DESCRIPTIVE_AFTER_COPULA:
            continue
        if _flag(m):
            errors.append(f"possible identity overclaim: '{m.group(0)}' "
                          f"(use capacity/similarity framing)")

    # 2) KCB mentioned without ceiling language — PROSE ONLY (skip machine-data lines).
    _prose_lines = []
    for line in text.splitlines():
        if "|" in line:
            continue
        if re.search(r"\bBGC\d{6,}\b", line):
            continue
        _prose_lines.append(line)
    prose = "\n".join(_prose_lines).lower()
    if "knownclusterblast" in prose or re.search(r"\bkcb\b", prose):
        if not any(h in prose for h in _ANCHOR_HINTS):
            errors.append("KCB mentioned without similarity-anchor / identity-ceiling language")

    # 3) Bioactivity-PHENOTYPE overclaim (H3, v9.7.374 coverage-gap fix) — a per-BGC/locus/
    #    cluster activity assertion ("shows antibacterial activity against X", "is a confirmed
    #    producer ... inhibits Y") is a claim-safety violation independent of any compound name,
    #    so the compound-scoped identity-verb checks above cannot see it. This scan previously
    #    existed ONLY inside lint_claim_safety_report() (the report-only `mamey claim-safety`
    #    CLI path). lint_claim_safety() — the function actually wired into the BLOCKING seal gate
    #    (mamey/seal_package.py::_gate_claim_safety) and into judgment_store.py's write-time
    #    self-lint — had no bioactivity-phenotype awareness at all: a real bioactivity-phenotype
    #    overclaim reached a sealed package with zero findings and zero visibility (not even a
    #    WARN row). Uses a distinct message prefix ("possible bioactivity-phenotype overclaim",
    #    not "possible identity overclaim") so callers that branch on the FAIL-eligible prefix
    #    (seal_package.py's _gate_claim_safety) keep bucketing this WARN, matching the
    #    calibration-phase severity lint_claim_safety_report() already uses for this rule — this
    #    fix restores visibility, it does not newly block a seal. Same guard order as
    #    lint_claim_safety_report()'s bioactivity check: negation, §30-question, capacity-frame,
    #    hedge, extract-level, header/table-label, bare-adjective-without-assertion-frame.
    _s30 = _section30_span(text)
    for m in _BIOACTIVITY_RE.finditer(text):
        sent_start = max(0, text.rfind(".", 0, m.start()) + 1)
        sent_end = text.find(".", m.end())
        sent = text[sent_start:sent_end + 1 if sent_end >= 0 else len(text)].strip()
        ctx = sent.lower()
        if _NEGATION_RX.search(ctx) or _BIOACT_NEG_EXTRA.search(ctx):
            continue
        if _s30 and _s30[0] <= m.start() < _s30[1] and _clause_ends_with_question(text, m):
            continue
        if any(frame in ctx for frame in _CAPACITY_FRAME):
            continue
        if _HEDGE_RX.search(ctx):
            continue
        if any(h in ctx for h in _EXTRACT_LEVEL_HINTS):
            continue
        line = _bioact_line(text, m)
        if _bioact_is_header_or_label(line):
            continue
        token = m.group(0)
        if _BIOACTIVITY_ADJ_RE.fullmatch(token) and not _BIOACTIVITY_ASSERTION_RE.search(sent) \
                and not _bioact_adjective_is_asserted(text, m):
            continue
        errors.append(f"possible bioactivity-phenotype overclaim: '{token}' in \"{sent[:150]}\" "
                      f"(bioactivity is extract-level context only, not a per-BGC/locus claim)")

    return errors


def main():
    ap = argparse.ArgumentParser(description="Post-hoc claim-safety linter for Sapote text.")
    ap.add_argument("path", help="markdown / text file to lint")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    text = Path(a.path).read_text(encoding="utf-8")
    errors = lint_claim_safety(text)
    if a.json:
        emit(json.dumps({"path": a.path, "clean": not errors, "findings": errors}, indent=2))
    else:
        if errors:
            emit(f"claim-safety: {len(errors)} finding(s) in {a.path}")
            for e in errors:
                emit(f"  ✗ {e}")
        else:
            emit(f"claim-safety: clean — {a.path}")
    sys.exit(0 if not errors else 1)



# ── v9.7.123 (SM-P1-004): CSV report + severity tiers ─────────────────────────

# Sections that always produce HIGH-severity findings (intro/summary sections)
_HIGH_SECTIONS = frozenset({"§1", "§8", "§2", "section 1", "section 8"})
# Sections that are INFO-severity (enrichment / layperson / beyond core Mode B)
_INFO_SECTIONS_RE = re.compile(r'§(?:1[0-9]|[2-9][0-9])', re.I)

# Context phrase that marks a sentence as already citing context/capacity even in §1/§8
_CONTEXT_PHRASES = ("context word", "context phrase")  # extensible


def _severity(section: str, misanchor_flag: str) -> str:
    """Assign severity tier based on section and misanchor flag.

    HIGH  — §1 or §8, OR any section with a non-blank Misanchor_Flag
    MEDIUM — §3–§7 (core Mode B interpretation)
    INFO   — §10+ (enrichment/layperson sections)
    """
    sec_norm = (section or "").strip().lower()
    # Misanchor_Flag set → always HIGH regardless of section
    if misanchor_flag and misanchor_flag.strip():
        return "HIGH"
    # §1 / §8 → always HIGH
    if sec_norm in _HIGH_SECTIONS or sec_norm in ("§1", "§8"):
        return "HIGH"
    # §10+ (enrichment) → INFO
    if _INFO_SECTIONS_RE.match(sec_norm):
        return "INFO"
    # §3–§7 core interpretation → MEDIUM
    return "MEDIUM"


# H3 (bioactivity-phenotype overclaim): "Bioactivity is extract-level only — never a per-BGC
# phenotype claim." A card asserting a BGC / locus / cluster shows / kills / inhibits / is
# active-against, or is a "confirmed producer", is a phenotype overclaim regardless of whether a
# compound is named — so the compound-scoped _PRODUCTION_RE / _COPULA_RE checks miss it entirely.
# Emitted as WARN (calibration phase per the punch card: "warn then calibrate"); not compound-
# scoped; exempt when negated, capacity-framed, hedged, or extract-level (the allowed form).
_BIOACTIVITY_RE = re.compile(
    r"\b(?:antibacterial|antifungal|antimicrobial|antibiotic|cytotoxic|anticancer|"
    r"bactericidal|fungicidal|bacteriostatic|fungistatic|"
    r"active\s+against|activity\s+against|inhibit(?:s|ed|ory|ion)?|kills?|killing|"
    r"zone\s+of\s+inhibition|\bMIC\b|bioactiv\w*|"
    r"confirmed\s+producer|is\s+a\s+producer|is\s+the\s+producer)\b",
    re.IGNORECASE,
)
# extract-level bioactivity is the ALLOWED form ("the crude extract shows antibacterial activity")
_EXTRACT_LEVEL_HINTS = ("extract", "fermentation broth", "culture supernatant", "whole-cell", "whole cell")
# hedge / hypothesis framing that de-fangs a phenotype assertion
_HEDGE_RX = re.compile(
    r"\b(?:may|might|could|would|potential(?:ly)?|candidate|hypothes\w+|"
    r"suggest\w*|predicted|putative|expected|if\s+active|target\s+hypothesis)\b", re.I)

# H3-calibrate (v9.7.323): _BIOACTIVITY_RE over-fired on bare adjectives with no assertion frame —
# section headers ("§13 Antibacterial / antifungal relevance"), table labels ("| Antibacterial score |"),
# class descriptions ("bioactive pigment"), and discovery-lead phrases ("a novel antibacterial lead").
# Split the vocabulary: ASSERTION terms are inherently phenotype claims (verbs/metrics); ADJECTIVE terms
# are a claim ONLY when asserted of a subject (copula / intensifier / followed by an activity noun).
# Bare adjectives on a header or table-label line are never a claim.
_BIOACTIVITY_ASSERTION_RE = re.compile(
    r"\b(?:active\s+against|activity\s+against|inhibit(?:s|ed|ory|ion)?|kills?|killing|"
    r"zone\s+of\s+inhibition|\bMIC\b|confirmed\s+producer|is\s+a\s+producer|is\s+the\s+producer)\b",
    re.I)
_BIOACTIVITY_ADJ_RE = re.compile(
    r"\b(?:antibacterial|antifungal|antimicrobial|antibiotic|cytotoxic|anticancer|"
    r"bactericidal|fungicidal|bacteriostatic|fungistatic|bioactiv\w*)\b", re.I)
# an adjective is an assertion when a copula/intensifier precedes it, or an activity noun follows it
_ADJ_FRAME_BEFORE = re.compile(
    r"\b(?:is|are|was|were|be|been|appears?|remains?|shows?|shown|exhibit(?:s|ed)?|display(?:s|ed)?|"
    r"demonstrat\w+|potent|potently|strong(?:ly)?|marked(?:ly)?|significant(?:ly)?|highly)\b[^.\n|]{0,40}$",
    re.I)
_ADJ_FRAME_AFTER = re.compile(r"^[^.\n|]{0,25}\b(?:activity|action|effect|potency|efficacy)\b", re.I)
# v9.7.374 (audit lane claim-safety-gate audit): the shared _NEGATION_RX only recognizes
# compound negation phrases ("does not", "do not", "cannot", ...) — it has no bare copula
# negation ("is not X" / "are not X" / "was not X" / "were not X", or their contractions). A
# genuine claim-safe denial phrased with the bare copula ("Siderophores are not themselves the
# antibacterial/antifungal principle; their relevance is indirect...", verbatim from the shipped
# siderophore Mode B exemplar) false-positived as a bioactivity_phenotype finding — live-
# reproduced against the UNMODIFIED shipped lint_claim_safety_report() before any other change
# in this patch. Scoped to _BIOACT_NEG_EXTRA (bioactivity-phenotype check only) rather than
# widening the shared _NEGATION_RX, so the identity-overclaim path (already heavily calibrated
# across CS-01/CS-P01/CS-P02/#3) is untouched.
_BIOACT_NEG_EXTRA = re.compile(
    r"\bargues?\s+against\b|\bno\s+confirmed\b|\bnot\s+a\s+confirmed\b|"
    r"\b(?:is|are|was|were)\s+not\b|\bisn't\b|\baren't\b|\bwasn't\b|\bweren't\b",
    re.I)


def _bioact_line(text: str, m) -> str:
    ls = text.rfind("\n", 0, m.start()) + 1
    le = text.find("\n", m.end())
    return text[ls:(le if le >= 0 else len(text))]


def _bioact_is_header_or_label(line: str) -> bool:
    if line.lstrip().startswith("#"):
        return True  # markdown section header
    if "|" in line and re.search(r"\b(?:score|relevance|landscape|class|label|column|axis|category)\b", line, re.I):
        return True  # table label / column header cell, not a sentence
    return False


def _bioact_adjective_is_asserted(text: str, m) -> bool:
    after = text[m.end():m.end() + 40]
    # an activity noun right after is a phenotype assertion ("antibacterial activity against …")
    if _ADJ_FRAME_AFTER.search(after):
        return True
    # attributive use — the adjective modifies a following common noun — is a class/description, NOT
    # a phenotype claim. Two attributive forms are exempt:
    #   plain-space form  ("bioactive pigment", "antifungal chemotype", "antibacterial lead"), and
    #   CS-P02 (v9.7.331) hyphenated compound-adjective form ("antifungal-routed programme",
    #     "antifungal-primary lead") — where the token matches up to the hyphen and a compound
    #     modifier + a following noun follow. Previously the hyphen defeated the exemption and these
    #     fired whenever a copula preceded; now the modifier-of-a-noun reading is exempt.
    # True predicatives ("is antifungal", "antifungal activity") still fire: bare "is antifungal" has
    # no following noun (falls through to the copula check) and an activity noun is caught above.
    hyph = re.match(r"-[a-z]+\s+([a-z][a-z-]+)", after)      # "-routed programme"
    nxt = re.match(r"\s+([a-z][a-z-]+)", after)               # " chemotype"
    attributive_noun = None
    if hyph:
        attributive_noun = hyph.group(1)
    elif nxt and nxt.group(1) != "against":
        attributive_noun = nxt.group(1)
    if attributive_noun and not _ADJ_FRAME_AFTER.search(" " + attributive_noun):
        return False  # modifies a plain following noun → attributive class/description, not a claim
    # predicative use ("BGC is antibacterial." / "is bactericidal against …") is a claim iff a
    # copula/intensifier precedes it.
    before = text[max(0, m.start() - 45):m.start()]
    return bool(_ADJ_FRAME_BEFORE.search(before))


# CS-P03 (v9.7.331): suppress bioactivity_phenotype inside §30 decision-tree QUESTIONS only. A §30
# question ("does the locus contribute antibacterial/antifungal activity?") interrogates a
# phenotype, it does not assert one; declaratives elsewhere still fire.
_SECTION_HEADING_RE = re.compile(r"(?m)^#{1,6}\s*§?\s*(\d{1,2})\b")


def _section30_span(text: str):
    """Character span (start, end) of the §30 body — heading end to the next section heading, a
    horizontal rule, or EOF. None if there is no §30 heading."""
    start = None
    for mt in _SECTION_HEADING_RE.finditer(text):
        if start is not None:
            return (start, mt.start())
        if mt.group(1) == "30":
            start = mt.end()
    if start is None:
        return None
    rule = re.search(r"(?m)^---\s*$", text[start:])
    return (start, start + rule.start()) if rule else (start, len(text))


def _clause_ends_with_question(text: str, m) -> bool:
    """True if the clause containing match m terminates with '?' before any '.'/'!'/'→'/newline —
    i.e. the match sits inside an interrogative clause."""
    for ch in text[m.end():m.end() + 400]:
        if ch in ".!?\n" or ch == "→":
            return ch == "?"
    return False


def lint_claim_safety_report(
    text: str,
    card_id: str = "",
    section: str = "",
    misanchor_flag: str = "",
    compound_names: set | None = None,
) -> list[dict]:
    """Run claim-safety checks and return structured CSV rows.

    Each row: card_id | section | sentence | violation_type | misanchor_flag | severity

    Uses the same split-verb logic as lint_claim_safety() (v9.7.125b): production verbs flag a
    compound-shaped token; the copula only flags real compound names (when a compound set is
    supplied) or compound-shaped non-descriptive tokens (heuristic fallback).
    """
    text = _remove_standard_disclaimer_lines(text)
    # v9.7.410 (CLAUDE_410 claimsafety linter normalize): same fold as lint_claim_safety above, so the
    # CSV-report surface (`mamey claim-safety`, the H3 delegate in claim_safety_gate.lint_text) cannot
    # disagree with the plain-findings surface about whether an obfuscated sentence is an overclaim.
    text = normalize_for_claim_detection(text)
    rows: list[dict] = []
    sev = _severity(section, misanchor_flag)
    compound_load_error = getattr(compound_names, "load_error", None)
    if compound_load_error:
        rows.append({
            "card_id": card_id,
            "section": section,
            "sentence": "Compound-name triage evidence is unreadable; robust claim-safety check unavailable.",
            "violation_type": "compound_name_evidence_unreadable",
            "misanchor_flag": misanchor_flag,
            "severity": "HIGH",
            "path": compound_load_error.get("path", ""),
            "error_type": compound_load_error.get("error_type", "Error"),
            "error": compound_load_error.get("error", "unknown read failure"),
        })
    lower = text.lower()
    cnames = {c.lower() for c in compound_names} if compound_names else None

    def _sentence_for(m):
        sent_start = max(0, text.rfind(".", 0, m.start()) + 1)
        sent_end = text.find(".", m.end())
        return text[sent_start:sent_end + 1 if sent_end >= 0 else len(text)].strip()

    def _identity_hit(m, is_copula: bool) -> bool:
        token = m.group(1)
        t = token.lower()
        context = _identity_context(text, m.start(), m.end())
        if _NEGATION_RX.search(context):
            return False  # denied production is not an overclaim (#3)
        context = context.lower()
        if any(frame in context for frame in _CAPACITY_FRAME):
            return False
        # Same clause-local hedge/rejection scope as the plain findings path.
        if _IDENTITY_FRAME_RX.search(context):
            return False
        if cnames is not None:
            # Finding 2 (multi-word): the single captured token misses multi-word names
            # ("phosphonoacetic acid", "heat-stable antifungal factor"). Build a probe from the
            # captured token + the window to sentence end, and test whether ANY derived name occurs
            # in it (substring, lowercased). Negation/capacity guards above still apply.
            tail = text[m.end():m.end() + 60]
            probe = (token + tail).lower().split(".")[0]
            if any(re.match(re.escape(cn) + r"(?![\w-])", probe) for cn in cnames):
                return True
            # CS-01 (v9.7.336): this used to `return any(...)` unconditionally, which INVERTED the
            # check — `claim-safety --package` derives the board and calls it "the robust check
            # path", but that path exempted every compound NOT on the board, so a hallucinated name
            # was the LEAST likely thing to be caught. Verb-class-aware fix, measured on the 10
            # shipped exemplars: PRODUCTION verbs fall through to the shape heuristic (0 new
            # findings there); COPULA keeps the board gate, because removing it fired 192 findings
            # on claim-safe prose ("is that", "are read", "is expected").
            if is_copula:
                return False
        if is_copula and t in _DESCRIPTIVE_AFTER_COPULA:
            return False
        if not _looks_like_compound(token):
            return False
        if t in _DESCRIPTIVE_AFTER_COPULA:
            return False
        return True

    # 1. Identity-verb overclaims — production verbs + copula, split logic
    for rx, is_cop in ((_PRODUCTION_RE, False), (_COPULA_RE, True)):
        for m in rx.finditer(text):
            if not _identity_hit(m, is_cop):
                continue
            rows.append({
                "card_id": card_id,
                "section": section,
                "sentence": _sentence_for(m)[:200],
                "violation_type": "identity_overclaim",
                "misanchor_flag": misanchor_flag,
                "severity": sev,
            })

    # 2. KCB mentioned without ceiling language — prose only (skip machine-data lines)
    _prose = "\n".join(
        ln for ln in text.splitlines()
        if "|" not in ln and not re.search(r"\bBGC\d{6,}\b", ln)
    ).lower()
    if "knownclusterblast" in _prose or re.search(r'\bkcb\b', _prose):
        if not any(h in _prose for h in _ANCHOR_HINTS):
            rows.append({
                "card_id": card_id,
                "section": section,
                "sentence": (text[:120] + "…" if len(text) > 120 else text).strip(),
                "violation_type": "kcb_no_ceiling",
                "misanchor_flag": misanchor_flag,
                "severity": sev,
            })

    # 3. Bioactivity-PHENOTYPE overclaim (H3) — a per-BGC/locus/cluster activity assertion or a
    #    "producer" status claim. Bioactivity is extract-level only; never a per-BGC phenotype.
    #    Not compound-scoped (the _PRODUCTION_RE / _COPULA_RE checks above cannot see it). WARN
    #    band (non-blocking, calibration phase). Exempt: negated, capacity-framed, hedged, or
    #    extract-level sentences.
    _s30 = _section30_span(text)
    for m in _BIOACTIVITY_RE.finditer(text):
        sent = _sentence_for(m)
        ctx = sent.lower()
        if _NEGATION_RX.search(ctx) or _BIOACT_NEG_EXTRA.search(ctx):
            continue
        # CS-P03 (v9.7.331): a §30 decision-tree QUESTION interrogates a phenotype, it does not
        # assert one — suppress a match inside an interrogative clause within §30 only.
        if _s30 and _s30[0] <= m.start() < _s30[1] and _clause_ends_with_question(text, m):
            continue
        if any(frame in ctx for frame in _CAPACITY_FRAME):
            continue
        if _HEDGE_RX.search(ctx):
            continue
        if any(h in ctx for h in _EXTRACT_LEVEL_HINTS):
            continue  # extract-level bioactivity is the allowed form
        # H3-calibrate: skip headers / table-label cells, and require an assertion frame for a
        # BARE adjective (antibacterial/…); assertion terms (kills / MIC / producer / …) still flag.
        line = _bioact_line(text, m)
        if _bioact_is_header_or_label(line):
            continue
        token = m.group(0)
        if _BIOACTIVITY_ADJ_RE.fullmatch(token) and not _BIOACTIVITY_ASSERTION_RE.search(sent) \
                and not _bioact_adjective_is_asserted(text, m):
            continue  # bare adjective with no assertion frame — a label/class name, not a claim
        rows.append({
            "card_id": card_id,
            "section": section,
            "sentence": sent[:200],
            "violation_type": "bioactivity_phenotype",
            "misanchor_flag": misanchor_flag,
            "severity": "WARN",
        })

    return rows


def write_claim_safety_csv(rows: list[dict], out_path) -> None:
    """Append claim-safety findings to a CSV report file."""
    import csv
    from pathlib import Path
    cols = ["card_id", "section", "sentence", "violation_type", "misanchor_flag", "severity"]
    out = Path(out_path)
    write_header = not out.exists()
    with out.open("a", newline="", encoding="utf-8") as f:
        w = _SafeDictWriter(f, fieldnames=cols, extrasaction="ignore")
        if write_header:
            w.writeheader()
        w.writerows(rows)


# v9.7.153 (Part-2 Finding 3): the CLI defaulted every invocation onto the heuristic
# path, since lint_claim_safety_report's compound_names parameter had no way to be
# supplied from the command line. On a real, carefully-claim-safety-reviewed report
# this produced 244 findings (~241 false positives); supplying the package's own
# real compound names dropped that to 3 legitimate findings. The right fix isn't a
# bare --compound-names flag a person has to remember to fill in correctly every
# time — it's deriving the candidate set from data the package already has.
_UNRESOLVED_TOKENS = {"unresolved", "n/a", "na", "none", "no kcb", ""}


class CompoundNameEvidence(set):
    """Set-compatible compound names carrying a typed source-read failure.

    The truth value remains true when ``load_error`` is present so the unchanged CLI passes this
    evidence object into the linter instead of collapsing it into the missing/empty-board fallback.
    Normal missing or empty boards still return an ordinary empty set.
    """

    def __init__(self, values=(), *, load_error: dict | None = None):
        super().__init__(values)
        self.load_error = load_error

    def __bool__(self):
        return set.__len__(self) > 0 or self.load_error is not None


def derive_compound_names_from_package(package_dir) -> set[str]:
    """Auto-derive a claim-safety compound-name set from a package's own anchored
    KCB candidates, so `claim-safety --package <dir>` can default onto the robust
    path instead of requiring a hand-typed --compound-names list.

    Source: every non-excluded BGC row's `KCB_top` field in
    `<strain>_4_triage_board.csv`. The field is written as
    "{accession} | {product} | knownclusterblast #{rank}" when a resolved MIBiG
    reference exists (see antismash_evidence.py); the product token (field index 1)
    is the compound name. Rows where KCB_top doesn't have that three-part pipe shape
    (e.g. a raw, unresolved clusterblast self-hit line, or an empty/"No KCB" value)
    are skipped rather than guessed at — a wrong compound name in the candidate set
    is worse than a missing one, since it would suppress a genuine overclaim finding.

    Returns an empty set if the triage board is missing or yields no resolvable names.  An
    unreadable board returns a set-compatible ``CompoundNameEvidence`` carrying ``load_error``;
    downstream linters convert that state into an explicit finding instead of silently using the
    weaker heuristic path.
    """
    import csv as _csv
    from pathlib import Path as _Path

    pkg = _Path(package_dir)
    triage_paths = sorted(pkg.glob("*_4_triage_board.csv"))
    if not triage_paths:
        return set()

    names: set[str] = set()
    try:
        with triage_paths[0].open(encoding="utf-8") as f:
            for row in _csv.DictReader(f):
                kcb_top = (row.get("KCB_top") or "").strip()
                parts = [p.strip() for p in kcb_top.split("|")]
                if len(parts) != 3:
                    continue
                product = parts[1]
                if product.lower() in _UNRESOLVED_TOKENS:
                    continue
                # A KCB product token can be a slash-joined multi-compound string
                # (e.g. "bombyxamycin A/bombyxamycin B", "cervimycin D/cervimycin C").
                # Add the full token AND each slash-split variant AND each variant's
                # base name (strip a trailing single-letter/roman/number designator),
                # so "synthesizes bombyxamycin" matches even when the stored token is
                # "bombyxamycin A/bombyxamycin B". Widening a denylist is safe: worst
                # case is flagging a genuine capacity sentence, which the negation/
                # capacity-frame guards already exempt.
                import re as _re
                variants = {product}
                for piece in product.split("/"):
                    piece = piece.strip()
                    if not piece:
                        continue
                    variants.add(piece)
                    base = _re.sub(r"\s+([A-Z]|[IVX]+|\d+)$", "", piece).strip()
                    if base:
                        variants.add(base)
                for v in variants:
                    if v.lower() not in _UNRESOLVED_TOKENS:
                        names.add(v)
    except (OSError, UnicodeDecodeError, _csv.Error) as exc:
        return CompoundNameEvidence(load_error={
            "path": str(triage_paths[0]),
            "error_type": type(exc).__name__,
            "error": str(exc),
        })
    return names



# ── v9.7.380 (AUDIT-380-01): the __main__ guard must be the LAST statement ──
# Previously this block sat at line ~313, ahead of _section30_span() (defined ~line 454).
# Running the file as a script therefore executed main() before that def was reached, and
# lint_claim_safety() died with NameError: name '_section30_span' is not defined.
if __name__ == "__main__":
    main()
