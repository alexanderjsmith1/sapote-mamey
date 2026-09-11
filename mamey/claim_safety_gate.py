"""Package-level claim-safety gate.

Runs a small generated-output scan for overclaim phrasing and emits a manifest
status. This is intentionally conservative and post-hoc; it does not replace the
authoring-time claim-safety wording.
"""
from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

# v9.7.374 (AUDIT audit): mirrors seal_package.py's existing pattern for reaching the
# bundled tools/ directory. lint_text() below delegates its bioactivity-phenotype check (H3) to
# tools/claim_safety_linter.py's already-calibrated implementation instead of maintaining a
# second, independently-drifting copy of the same regex logic — see the H3-calibrate history
# (v9.7.216/.323/.331/.336/.354) in that module for why a naive re-implementation here would be
# unsafe to improvise.
_TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

# v9.7.377 (AUDIT audit): the captured-token quantifier was `+` (1-or-more trailing chars),
# which makes single-letter words like the indefinite article "a" fail to match this group at all —
# "produces a pigment called violacein" never matched _PRODUCTION_RE in the first place ("a" cannot
# satisfy `[A-Za-z][A-Za-z0-9'\-]+`, which needs 2+ chars). Widened to `*` so "a" (and any other
# single-char token) can be captured and reach the _SAFE_AFTER / lookahead logic below. Purely
# additive: every string that matched under `+` still matches identically under `*`.
# v9.7.409 (CLAUDE_409/F2 merged with NL14): British `-ise` biosynthesise added; `assembles|elaborates|secretes`
# are in the STRICT group below (bare compound-shaped object only), so "secretes proteins" stays clean.
_PRODUCTION_RE = re.compile(
    r"\b(?:produces|synthesizes|synthesises|biosynthesizes|biosynthesises|yields|makes)"
    r"\s+([A-Z]?[A-Za-z][A-Za-z0-9'\-]*)", re.I)
# v9.7.409 (CLAUDE_409/F2): riskier production verbs fire only under a strict claim-shape: a BARE lowercase
# object (no determiner), not a generic/class/status noun (_looks_like_compound_name), with natural-product
# morphology (_NP_MORPHOLOGY_RE). "encodes venezuelin" fires; "encodes a PKS" / "generates a tree" do not.
_PRODUCTION_STRICT_RE = re.compile(
    r"\b(?:secretes|assembles|elaborates|generates|affords|manufactures|encodes)"
    r"\s+([a-z][a-z0-9'\-]{4,})\b")  # lowercase-initial only, no re.I (a bare compound name)
_NP_MORPHOLOGY_RE = re.compile(
    r"(?:mycin|micin|bactin|actin|statin|kacin|rubicin|cin|ycin|mabin|nolin|"
    r"chelin|bactam|penem|mide|amide|olide|actone|lactone|azole|azolin|"
    r"in|ine|one|ol|ide|osin|toxin|zin|din|tin|pin|nin)$")
# v9.7.409 (CLAUDE_409/F1): bare `similarity` and `-like` dropped from the safe-context whitelist — Mode B
# cards repeat "similarity" constantly, so a raw ±80-char window turned the detector OFF next to almost any
# overclaim ("produces venezuelin; similarity is discussed below." leaked). Proximity is now clause-local
# (see _clause_around); a hedge in a different clause no longer launders a claim.
_SAFE_CONTEXT_RE = re.compile(r"capacity consistent with|similarity anchor|not identity|not product identity|comparator_context", re.I)
# v9.7.409 (CLAUDE_409/F2): copula-identity overclaim, deliberately narrow: BGC/cluster/locus/product subject,
# object must look like a specific compound name; same clause-local safe-context + negation guards.
_COPULA_IDENTITY_RE = re.compile(
    r"\b(?:BGC\d+|cluster|clusters|locus|loci|product|products|compound|compounds|metabolite|"
    r"metabolites|molecule|molecules)\s+(?:is|are|was|were)\s+(?:the\s+|a\s+|an\s+)?"
    r"([A-Za-z][A-Za-z0-9'\-]{4,})", re.I)
_COPULA_NON_NAME = {
    "predicted", "putative", "candidate", "possible", "likely", "unlikely", "plausible",
    "consistent", "compatible", "similar", "identical", "novel", "present", "absent", "unknown",
    "unresolved", "incomplete", "complete", "intact", "truncated", "partial", "edge", "interior",
    "responsible", "characteristic", "indicative", "suggestive", "encoded", "located", "positioned",
    "flanked", "annotated", "observed", "associated", "required", "involved", "expressed",
    "conserved", "distinct", "typical", "atypical", "rare", "common", "high", "low", "moderate",
    "strong", "weak", "short", "larger", "smaller", "adequate", "housekeeping", "similarity",
    "identity", "comparator", "anchor", "class", "family", "type", "group", "backbone", "scaffold",
    "pathway", "polyketide", "peptide", "nonribosomal", "ribosomal", "terpene", "terpenoid",
    "siderophore", "lanthipeptide", "ripp", "enediyne", "hypothesis", "capacity",
    "protein", "proteins", "enzyme", "enzymes", "peptides", "product", "products", "compound",
    "compounds", "metabolite", "metabolites", "molecule", "molecules", "factor", "factors",
    "agent", "agents", "antibiotic", "antibiotics", "siderophores", "pigment", "pigments",
    "toxin", "toxins", "signal", "signals", "precursor", "precursors", "intermediate",
    "intermediates", "machinery", "aglycone", "aglycones", "core", "scaffolds", "structures",
    "cluster", "clusters", "gene", "genes", "region", "regions",
}
_COPULA_CLASS_SUFFIX = ("-like", "-type", "-class", "-family", "-forming", "-related", "-dominant")
# v9.7.412 (round 5, R4): three residual identity shapes the .411 detector missed, each measured at
# ZERO false positives over the 1,559 finished W4 cards before adoption:
#  * a verb split by an HTML comment or a hyphen+newline ("produ<!-- -->ces", "pro-\nduces") —
#    invisible to a word-boundary alternation, and no legitimate card contains either form;
#  * a LABEL or TABLE-CELL product assertion ("Product: venezuelin", "| product | venezuelin |") —
#    the same claim with the verb removed entirely;
#  * a SUBJECT-BOUND "-producing" compound ("BGC001 is venezuelin-producing"). The bare
#    "X-producing" form is NOT used: it matched 4 legitimate lines in the corpus, all describing
#    other organisms or enzymes ("ectoine-producing bacteria", "biliverdin-producing heme
#    oxygenase"), so the subject must be a BGC/cluster/locus for this to fire.
# A word physically SPLIT by an HTML comment or a hyphen+linebreak, where the two halves rejoin into
# a production verb — e.g. "produ<!-- -->ces", "pro-\nduces". Only the split site is examined (never
# the whole de-hyphenated document: ordinary markdown wraps constantly, and re-linting the rejoined
# text wholesale lost the hedge/denial calibration and produced 6 false positives on the W4 corpus).
_SPLIT_SITE_RE = re.compile(r"([A-Za-z]{2,})(?:<!--.*?-->|-[ \t]*\r?\n[ \t]*)([A-Za-z]{2,})", re.S)
_SPLIT_VERBS = {"produces", "synthesizes", "synthesises", "biosynthesizes", "biosynthesises",
                "secretes", "encodes", "yields", "makes", "assembles", "elaborates"}
_AFTER_SPLIT_OBJ_RE = re.compile(r"^\s+([A-Za-z][A-Za-z0-9'\-]{4,})")


_LABEL_PRODUCT_RE = re.compile(r"(?:^|\|)\s*(?:mature\s+|final\s+)?product\s*(?::|\|)\s*\|?\s*([A-Za-z][A-Za-z0-9'\-]{4,})\b", re.I | re.M)
_PRODUCING_COMPOUND_RE = re.compile(r"\b(?:BGC\d+|cluster|clusters|locus|loci|region)\b[^.\n]{0,40}?\bis\s+([A-Za-z][A-Za-z0-9'\-]{4,})-producing\b", re.I)


def _clause_around(text: str, start: int, end: int) -> str:
    """The clause containing the match [start:end), bounded by sentence/clause delimiters. v9.7.409
    (CLAUDE_409/F1): the safe-context test is applied to THIS clause only. (normalize/F2b): `: ` and `(`
    are boundaries too, so an inline label or trailing parenthetical cannot launder the claim."""
    left = text[max(0, start - 400):start]
    lb = max(left.rfind(". "), left.rfind("\n"), left.rfind("? "), left.rfind("! "),
             left.rfind("; "), left.rfind("—"), left.rfind(": "), left.rfind("("))
    cstart = (max(0, start - 400) + lb + 1) if lb >= 0 else max(0, start - 400)
    right = text[end:end + 400]
    cands = [right.find(d) for d in (". ", "\n", "? ", "! ", "; ", "—", ": ", " (") if right.find(d) != -1]
    cend = (end + min(cands)) if cands else min(len(text), end + 400)
    return text[cstart:cend]


def _has_local_negation(text: str, start: int) -> bool:
    """Use the existing production detectors' clause-bounded denial scope.

    A disclaimer in a previous clause must not suppress an independent claim.
    Colons stay inside this scope for denials such as 'Cannot be claimed: that ...'.
    """
    upstream = text[max(0, start - 400):start]
    boundary = max(upstream.rfind(d) for d in (". ", "\n", "? ", "! ", "; ", "—"))
    return bool(_NEGATION_RE.search(upstream[boundary + 1:] if boundary >= 0 else upstream))


def _looks_like_compound_name(token: str) -> bool:
    """v9.7.409 (CLAUDE_409/F2): a lowercase, non-class, non-status word after a copula is likely a
    specific compound name (the signal that separates "is venezuelin" from "is edge-truncated")."""
    t = token.lower()
    if t in _COPULA_NON_NAME or t in _SAFE_AFTER:
        return False
    if t.endswith(_COPULA_CLASS_SUFFIX):
        return False
    return len(t) >= 5 and re.match(r"^[a-z][a-z0-9'\-]+$", t) is not None
_SAFE_AFTER = {"a", "an", "the", "polyketide", "peptide", "metabolite", "metabolites", "compound",
               "compounds", "backbone", "pathway", "class",
               # #3a (v9.7.216): English idiom "makes it/the/them/for/this/that ..." is not a biosynthetic
               # claim — these objects after a production verb are function-words, not compound names.
               "it", "them", "for", "this", "that", "us", "possible", "sense", "sure", "up",
               # v9.7.409: count words after a production verb ("yields zero hits", "yields no alignment")
               # are never a compound name; surfaced as false positives once F1 narrowed the safe context.
               "zero", "no", "none", "one", "two", "three", "several", "many", "few", "fewer", "more"}
# #3b: denial phrases that negate a following production verb ("does not support that X produces Y").
# v9.7.409 CANDIDATE (CLAUDE_409/normalize): the `n't` contractions are written `['\s]?t` so they keep
# matching after the normalization pre-pass folds a straight apostrophe to a space (see
# _normalize_for_detection): `doesn't` in the source becomes `doesn t` in the detection copy, and a
# denial must still suppress the claim it scopes (guarding against a normalization-induced FALSE
# POSITIVE on a legitimately-negated sentence). Purely widening on the negation side — it can only
# suppress, never add, a finding.
_NEGATION_RE = re.compile(r"\b(?:does not|do not|doesn['\s]?t|don['\s]?t|cannot|can['\s]?t|can not|"
                          r"no evidence|not support|"
                          r"not established|rather than|instead of|without|no data|not claim|unable to|"
                          # v9.7.383 (WAC/DSM audit, batch 1): ordinary disclaimer forms. Safe to add ONLY
                          # because negation scope is now clause-bounded (the "; "/"—" splits below) — a
                          # leading "…not proof of novelty;" no longer suppresses a later independent
                          # production claim in the next clause (the false negative a flat vocab add caused).
                          r"not proof|no proof|not a claim|no claim|not evidence|cannot claim|can['\s]?t claim|"
                          r"not asserted|not pinned)\b", re.I)
# v9.7.377 (AUDIT audit): _PRODUCTION_RE only ever captured the SINGLE word immediately after
# the verb. When that word is a filler/determiner already in _SAFE_AFTER ("the", "a", "this",
# "compound", "metabolite", ...), lint_text() used to give up on the whole sentence — even though
# ordinary overclaim prose routinely continues past the filler word to the real compound name via
# "named X" / "called X" / "known as X" ("produces the antibiotic streptomycin" was NOT reachable
# here because the filler noun "antibiotic" isn't itself the compound — but "produces the compound
# known as chalcomycin" / "produces a novel polyketide named tetrachlorizine" slipped through with
# ZERO findings, confirmed live). When the immediate token is a filler word, look ahead a short
# window for that continuation and re-target the check onto the real compound name before conceding
# the sentence is safe.
_NAMED_AS_RE = re.compile(r"\b(?:named|called|known as)\s+([A-Z]?[A-Za-z][A-Za-z0-9'\-]*)", re.I)

# v9.7.378b (CODEX post-cut correction A): the filler-word continuation above only re-targets when
# the real compound follows via "named/called/known as X". A direct typed-object construction —
# "produces the antibiotic streptomycin", "produces the compound streptomycin", "produces the
# metabolite erythromycin" — names the compound immediately after a CLASS NOUN with no connector,
# so _NAMED_AS_RE never fired and the sentence slipped through with zero findings (confirmed live on
# the sealed .378 tier). This rule catches "produces [the/a/an] <class-noun> <specific-name>" while
# leaving generic capacity phrasing ("produces a polyketide backbone", "produces the compound" with
# no trailing name) and the named/called path untouched. The trailing token must be a specific
# candidate name, NOT a generic tail word or a connector (those belong to other paths / are safe).
_TYPED_OBJECT_RE = re.compile(
    r"\b(?:produces|synthesizes|synthesises|yields|makes|biosynthesizes)\s+(?:the|a|an)\s+"
    r"(?:antibiotic|antibiotics|compound|compounds|metabolite|metabolites|pigment|pigments|"
    r"molecule|molecules|product|products|toxin|drug|siderophore)\s+"
    r"([A-Za-z][A-Za-z0-9'\-]{2,})", re.I)
# tokens that are NOT a specific compound name: generic tails (class-level), connectors handled by
# _NAMED_AS_RE, and function words. If the token after the class noun is one of these, this is not a
# direct typed-object product-identity claim.
_TYPED_NON_NAME = {"backbone", "pathway", "class", "family", "families", "scaffold", "core",
                   "skeleton", "group", "type", "precursor", "derivative", "derivatives", "moiety",
                   "unit", "like", "biosynthesis", "cluster", "gene", "genes", "product", "products",
                   "compound", "compounds", "metabolite", "metabolites", "named", "called", "known",
                   "that", "which", "with", "from", "via", "and", "or", "is", "was", "of", "in",
                   # v9.7.409 CANDIDATE (CLAUDE_409/normalize): status/descriptor completions of the
                   # English "makes the <noun> <adjective>" idiom (= "renders the compound
                   # uncharacterised"), NOT a produced compound name. The normalization pre-pass folds
                   # the emphasis in "makes the *compound* uncharacterised" (real BGC027 card, §16),
                   # exposing that idiom to this typed-object path; these keep it from misreading the
                   # trailing adjective as a product name. They are never specific-compound names.
                   "uncharacterised", "uncharacterized", "unknown", "unclear", "undefined",
                   "unresolved", "novel", "putative", "predicted", "present", "absent"}

# Label-anchor product-identity construction (no production verb): "KNOWN -> tetrachlorizine",
# "KNOWN: X", "anchor -> X", "characterization = X". A per-gene MIBiG/BLAST anchor labelled onto a
# compound is a CLASS-LEVEL resemblance, never a product identity. (v9.7.354 — the BGC059 defect the
# verb-only rule missed; reuses _SAFE_CONTEXT_RE / _NEGATION_RE so it inherits their guards.)
_ANCHOR_LABEL_RE = re.compile(
    r"\b(?:KNOWN|KNOWN_ANCHORED|characteriz\w*|anchor|identity)\b\s*(?:->|\u2192|:|=)\s*"
    r"([A-Z]?[A-Za-z][A-Za-z0-9'\-]{3,})", re.I)
# A compound immediately qualified as class-level is fine ("-> tetrachlorizine family").
_CLASS_LEVEL_AFTER = re.compile(r"^\s*(?:family|families|class|group|type|-like|like|cluster)\b", re.I)

CANDIDATE_SUFFIXES = (".md", ".txt")
# v9.7.338 (MB-03): the narrative section files compile-report inlines — `<strain>_ecology_section.md`
# and `<strain>_deepdives_section.md` — slipped through the filename filter, so a compiled report could
# ship an ecological-synthesis / deep-dive section that was never scanned. Add ecolog / deep-dive /
# section so those files are picked up by candidate_text_files().
# v9.7.371: the same gap existed for `<strain>_fermentation.md` — compile_report._ferm_section() inlines
# it verbatim into §11 ("Fermentation and wet-lab guidance"), a free-text human-authored channel
# (media, additives, timepoints, extraction, detection) that can drift into overclaim exactly like the
# ecology/deep-dive sections this filter was widened for at MB-03, but "fermentation" was never added.
CANDIDATE_NAME_RE = re.compile(
    r"mode[_ -]?b|report|technical|layperson|bench|summary|directed[_ -]?pks|ecolog|deep[_ -]?dive|section|fermentation",
    re.I)

# ---------------------------------------------------------------------------
# v9.7.409 CANDIDATE (CLAUDE_409/normalize): detection-copy normalization pre-pass.
#
# DEEP_AUDIT2 finding #1 (WORST): every identity regex captures an object that must START with an
# ASCII letter (`[A-Z]?[A-Za-z]...`). The scanned corpus is markdown, where a compound name is most
# naturally written *venezuelin* / **venezuelin** / `venezuelin` / _venezuelin_ / [venezuelin](x) /
# "venezuelin" / (venezuelin). A leading wrapper char puts a non-letter at that position, so the
# group never matches and NO path even reaches its safe-context / negation guards — the detector is
# silently OFF. Findings #3/#4/#5/#6 are the same blind spot via a non-ASCII lookalike, a zero-width
# char, or a stray apostrophe in the verb / bioactivity / compound token.
#
# Fix: before ANY regex runs, build a DETECTION-ONLY copy of the text that
#   (1) drops zero-width / format characters (ZWSP, ZWNJ, ZWJ, WJ, BOM, soft hyphen),
#   (2) maps common Unicode confusables (Cyrillic / Greek / fullwidth look-alikes) to ASCII,
#   (3) NFKC-folds each character (fullwidth -> ASCII, ligatures, compatibility forms),
#   (4) neutralizes markdown-emphasis / quote wrappers (`* _ ` ~ " ' “ ” ‘ ’`) to a SPACE, and
#       bracket wrappers (`( ) [ ] { } < >`) to a NEWLINE — a newline is BOTH a token separator
#       (so `produces\n venezuelin` still matches, closing `(venezuelin)` / `[venezuelin](x)`) AND a
#       clause boundary (so a TRAILING parenthetical `venezuelin (similarity anchor)` cannot launder
#       the claim — DEEP_AUDIT2 #2's parenthetical half).
# Crucially the emitted finding text is mapped back to the ORIGINAL substring (idx_map), so this
# NEVER alters any scientific / packaged output — it only changes what the matcher SEES.
_ZERO_WIDTH = {
    "​", "‌", "‍", "⁠", "﻿", "­", "᠎", "‎", "‏",
}
# Emphasis / quote wrappers -> single space (keep the two sides as separate tokens on the same line).
_WRAP_TO_SPACE = set("*_`~\"'“”‘’´")
# Bracket wrappers -> newline (token separator AND clause boundary; see _clause_around).
_WRAP_TO_NEWLINE = set("()[]{}<>")
# Common confusables: non-ASCII look-alikes an author (or an adversary) can substitute for a Latin
# letter. Deliberately focused on letters that appear in the production/bioactivity verbs and in
# compound names (DEEP_AUDIT2 #3/#4/#5 examples: Cyrillic о in "prоduces", Cyrillic с in "aсtive").
_CONFUSABLE = {
    # Cyrillic -> Latin
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P", "С": "C",
    "Т": "T", "Х": "X", "У": "Y", "І": "I", "Ј": "J", "Ѕ": "S",
    "а": "a", "в": "b", "е": "e", "к": "k", "м": "m", "н": "h", "о": "o", "р": "p", "с": "c",
    "т": "t", "х": "x", "у": "y", "і": "i", "ј": "j", "ѕ": "s", "ԁ": "d", "һ": "h", "ԛ": "q",
    "ԝ": "w", "ѵ": "v", "ɡ": "g", "ո": "n", "ս": "u",
    # Greek -> Latin
    "Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H", "Ι": "I", "Κ": "K", "Μ": "M", "Ν": "N",
    "Ο": "O", "Ρ": "P", "Τ": "T", "Υ": "Y", "Χ": "X",
    "α": "a", "ο": "o", "ρ": "p", "ν": "v", "τ": "t", "ι": "i", "κ": "k", "χ": "x", "γ": "y",
    "ε": "e", "ρ".upper(): "P",
}

# ---------------------------------------------------------------------------
# v9.7.410 (CLAUDE_410/verb_normalize): the .409 pre-pass above hardened the COMPOUND position; the
# PRODUCTION-VERB position was still defended only by the homoglyph table (round6_v409/
# CLAIMSAFETY_EVASION_REATTACK.md, Battery B — execution-confirmed, all 5 returned 0 findings):
#   HD1  `prodúces streptomycin`      precomposed Latin diacritic in the verb (NFKC-stable, not a confusable)
#   HD5  `pr0duces streptomycin`      ASCII digit 0 for o (no digit is in _CONFUSABLE)
#   HD15 `pro**duces** streptomycin`  intra-word emphasis: the wrapper->space fold SPLIT the verb
#   HD17 `produces&nbsp;streptomycin` literal HTML entity = no whitespace between verb and object
#   HD18 `produces \*streptomycin\*`  backslash-escaped wrapper: `\` is a non-letter at the object start
# One mangled verb character reproduces the .408 "detector silently OFF" failure, relocated to the verb.
#
# Fix, still DETECTION-ONLY (every stage carries the per-char map back to the original offsets, and
# every emitted finding still goes through _orig_span, so packaged output is never altered):
#   Stage A (both fold modes): decode HTML entities (`&nbsp;` -> U+00A0 -> NFKC space; `&#8203;` ->
#     zero-width -> dropped) and strip a backslash that escapes a markdown punctuation char, BEFORE
#     the existing zero-width / confusable / NFKC per-char pass. Both are lexical repairs of the text an
#     author visibly meant; they add no vocabulary.
#   Stage B (identity matchers only): a run of emphasis/code wrappers sitting strictly INSIDE a word
#     (letter/digit on both sides: `pro**duces**`, `pro_duces`, `pro`duces`) is DELETED, so the two
#     halves rejoin, and only then are the remaining wrappers folded to space / newline exactly as in
#     .409. Quote/apostrophe wrappers are NOT in the intra-word set — `venezuelin's` must keep splitting
#     to `venezuelin s` (the possessive case the .409 battery relies on).
#   Stage C (identity matchers only): token-scoped verb repair. For each word token that is not plain
#     ASCII letters, compute an accent-folded form (NFKD, combining marks removed) and, when the token
#     mixes letters and digits, a leetspeak-folded form (0->o, 1->l or i, 3->e, 4->a, 5->s, 7->t). The
#     token is rewritten ONLY if a folded form is one of the production/passive/nominal keywords the
#     matchers look for (_VERB_FOLD_TARGETS). This gate is what keeps the fold from touching anything
#     else: `BGC027` never becomes `BGCo2t` (so `BGC\d+` in _COPULA_IDENTITY_RE still matches), gene
#     counts stay digits, and an accented organism / compound name is left exactly as written — the
#     compound position already matches whatever token follows the verb, so folding it would add
#     nothing and is deliberately not done.
_HTML_ENTITY_RE = re.compile(r"&(?:#[0-9]{1,7}|#[xX][0-9a-fA-F]{1,6}|[A-Za-z][A-Za-z0-9]{1,31});")
# A backslash that escapes a markdown-significant punctuation char (CommonMark's escapable set).
_MD_ESCAPE_RE = re.compile(r"\\(?=[\\`*_{}\[\]()#+\-.!|~<>\"'])")
# Emphasis / code wrapper run strictly inside a word (letter or digit on BOTH sides).
_INTRAWORD_WRAP_RE = re.compile(r"(?<=[^\W_])[*_`~]+(?=[^\W_])")
# Word tokens for Stage C: letters, digits, and combining marks (so a DECOMPOSED accent, e.g. `u` +
# U+0301, stays inside the token instead of splitting it).
_WORD_TOKEN_RE = re.compile(r"(?:[^\W_]|[\u0300-\u036f])+")
_DIGIT_CONFUSABLE = {"0": "o", "3": "e", "4": "a", "5": "s", "7": "t"}  # `1` -> l / i tried both
# The keywords every identity matcher above keys on (production verbs, strict verbs, passive
# participles, nominalizations, the named/called connectors). Lower-case; compared case-insensitively.
_VERB_FOLD_TARGETS = frozenset({
    "produces", "synthesizes", "synthesises", "biosynthesizes", "biosynthesises", "yields", "makes",
    "secretes", "assembles", "elaborates", "generates", "affords", "manufactures", "encodes",
    "produced", "made", "assembled", "elaborated", "generated", "manufactured", "synthesized",
    "synthesised", "biosynthesized", "biosynthesised", "secreted",
    "production", "biosynthesis", "synthesis", "producing", "making", "synthesizing", "synthesising",
    "assembling", "gives", "rise", "confers", "responsible", "named", "called", "known",
})


def _decode_entities_and_escapes(text: str) -> tuple[list[str], list[int]]:
    """Stage A front half: return (chars, idx) with HTML entities decoded (each decoded char maps to
    the entity's `&`) and markdown backslash-escapes dropped. Non-entity `&...;` text is kept verbatim."""
    import html as _html
    chars: list[str] = []
    idx: list[int] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "&":
            m = _HTML_ENTITY_RE.match(text, i)
            if m:
                decoded = _html.unescape(m.group(0))
                if decoded != m.group(0):
                    for dch in decoded:
                        chars.append(dch)
                        idx.append(i)
                    i = m.end()
                    continue
        elif ch == "\\" and _MD_ESCAPE_RE.match(text, i):
            i += 1  # drop the escaping backslash; the escaped char is processed normally next
            continue
        chars.append(ch)
        idx.append(i)
        i += 1
    return chars, idx


# v9.7.410 hostile audit H23: the bioactivity-phenotype delegate (tools/claim_safety_linter.py,
# reached through `fold_wrappers=False`) got Stage A only, so its keywords had NO accent/leet repair —
# `actíve against S. aureus` (precomposed í) dropped both phenotype findings while `prodúces` was
# caught. Same token-scoped, keyword-gated fold, keyed on the linter's own vocabulary
# (_BIOACTIVITY_RE / _BIOACTIVITY_ASSERTION_RE / _BIOACTIVITY_ADJ_RE plus the frame words the
# assertion check reads). Organism / compound names never fold: they are not in this set.
_BIOACTIVITY_FOLD_TARGETS = frozenset({
    "antibacterial", "antifungal", "antimicrobial", "antibiotic", "cytotoxic", "anticancer",
    "bactericidal", "fungicidal", "bacteriostatic", "fungistatic", "bioactive", "bioactivity",
    "active", "activity", "against", "inhibit", "inhibits", "inhibited", "inhibitory", "inhibition",
    "kill", "kills", "killing", "zone", "mic", "confirmed", "producer",
    "is", "are", "was", "were", "shows", "shown", "exhibits", "exhibited", "displays", "displayed",
    "potent", "potently", "strongly", "markedly", "significantly", "highly",
})


def _fold_verb_token(token: str, targets: frozenset = _VERB_FOLD_TARGETS) -> str | None:
    """Stage C: the folded form of `token` if (and only if) it folds to a matcher keyword; else None."""
    if token.isascii() and token.isalpha():
        return None  # plain ASCII word: nothing to repair
    # accent fold: NFKD then drop combining marks (`ú` -> `u`)
    acc = "".join(c for c in unicodedata.normalize("NFKD", token) if not unicodedata.combining(c))
    cands = [acc]
    if any(c.isdigit() for c in acc) and any(c.isalpha() for c in acc):
        base = "".join(_DIGIT_CONFUSABLE.get(c, c) for c in acc)
        cands.append(base.replace("1", "l"))
        cands.append(base.replace("1", "i"))
    for cand in cands:
        if cand != token and cand.isascii() and cand.lower() in targets:
            return cand
    return None


def _apply_token_fold(s: str, smap: list[int], targets: frozenset) -> tuple[str, list[int]]:
    """Stage C engine: rewrite only the word tokens that fold to one of `targets`, carrying the
    per-character map back to the original offsets (a replacement of different length reuses the
    last mapped index, exactly as before)."""
    c_out: list[str] = []
    c_map: list[int] = []
    pos = 0
    for m in _WORD_TOKEN_RE.finditer(s):
        repl = _fold_verb_token(m.group(0), targets)
        if repl is None:
            continue
        c_out.append(s[pos:m.start()])
        c_map.extend(smap[pos:m.start()])
        span = smap[m.start():m.end()]
        c_out.append(repl)
        c_map.extend(span[min(k, len(span) - 1)] for k in range(len(repl)))
        pos = m.end()
    if pos == 0:
        return s, smap
    c_out.append(s[pos:])
    c_map.extend(smap[pos:])
    return "".join(c_out), c_map


def _normalize_for_detection(text: str, fold_wrappers: bool = True) -> tuple[str, list[int]]:
    """Return (norm, idx_map): a detection-only copy of `text` plus a per-character map back to the
    original offsets. norm[j] originated at text[idx_map[j]]. See the module block above for what is
    folded. Length-varying only where a zero-width char is dropped or NFKC expands a character; every
    other transform is 1:1, so most offsets are identity. The map lets a match on `norm` be reported
    as its ORIGINAL substring, keeping the emitted finding faithful to the file on disk.

    `fold_wrappers=True` (the identity matchers) additionally neutralizes markdown/quote wrappers to a
    space and bracket wrappers to a newline. `fold_wrappers=False` (the H3 bioactivity delegate) does
    ONLY the invisible-char strip and the Unicode look-alike fold, leaving punctuation exactly where
    it was — the delegate carries its own calibrated hedge / sentence-boundary logic, and rewriting
    its brackets/emphasis would corrupt that segmentation (observed: it turned a hedged class-prior
    line and an explicit "no measured activity ... is claimed" denial into false positives). The mild
    fold still de-obfuscates a homoglyph/zero-width bioactivity token (DEEP_AUDIT2 #5) without
    disturbing any legitimately-hedged bioactivity prose.

    v9.7.410 (CLAUDE_410/verb_normalize): staged. Stage A (both modes) = entity decode + backslash-
    escape strip, then the .409 zero-width / confusable / NFKC pass. Stage B/C (fold_wrappers only) =
    intra-word wrapper deletion, then the .409 wrapper->space/newline fold, then token-scoped verb
    repair (accent + leetspeak fold, applied ONLY to tokens that fold to a matcher keyword). See the
    v9.7.410 block above for why each stage is scoped the way it is."""
    # ---- Stage A: entities / escapes, then the .409 per-char pass (no wrapper folding yet) ----
    src_chars, src_idx = _decode_entities_and_escapes(text)
    a_out: list[str] = []
    a_map: list[int] = []
    for ch, i in zip(src_chars, src_idx):
        if ch in _ZERO_WIDTH:
            continue  # (1) drop invisible/format chars entirely
        mapped = _CONFUSABLE.get(ch, ch)  # (2) confusable -> ASCII
        folded = unicodedata.normalize("NFKC", mapped)  # (3) NFKC per char (fullwidth, ligatures)
        for fch in folded:
            if fch in _ZERO_WIDTH:
                continue
            a_out.append(fch)
            a_map.append(i)
    if not fold_wrappers:
        # v9.7.410 (H23): bioactivity delegate — no wrapper folding (its sentence segmentation needs
        # the punctuation), but the same keyword-gated accent/leet repair on ITS vocabulary.
        return _apply_token_fold("".join(a_out), a_map, _BIOACTIVITY_FOLD_TARGETS)
    # ---- Stage B: delete intra-word wrapper runs, then fold the remaining wrappers as in .409 ----
    a_str = "".join(a_out)
    drop = set()
    for m in _INTRAWORD_WRAP_RE.finditer(a_str):
        drop.update(range(m.start(), m.end()))
    b_out: list[str] = []
    b_map: list[int] = []
    for j, fch in enumerate(a_out):
        if j in drop:
            continue
        if fch in _WRAP_TO_SPACE:
            fch = " "
        elif fch in _WRAP_TO_NEWLINE:
            fch = "\n"
        b_out.append(fch)
        b_map.append(a_map[j])
    b_str = "".join(b_out)
    # ---- Stage C: token-scoped verb repair (accent fold + leetspeak fold, keyword-gated) ----
    return _apply_token_fold(b_str, b_map, _VERB_FOLD_TARGETS)


def _orig_span(text: str, idx_map: list[int], a: int, b: int) -> str:
    """Map a normalized span [a:b) back to the ORIGINAL substring for the emitted finding message."""
    if not idx_map or a >= len(idx_map):
        return ""
    a = max(0, a)
    start = idx_map[a]
    end = (idx_map[b - 1] + 1) if b > a and (b - 1) < len(idx_map) else (start + 1)
    return text[start:end]


# v9.7.409 CANDIDATE (CLAUDE_409/normalize): DEEP_AUDIT2 #7 — passive / nominalization production
# framings that no verb allow-list caught. Each pattern captures group(1) = the object compound and
# is gated downstream by BOTH _looks_like_compound_name AND _NP_MORPHOLOGY_RE (so only a token
# SHAPED like a specific natural-product name fires) plus the same clause-local safe-context and
# clause-scoped negation guards as the verb path. That double gate keeps ordinary genomics prose
# clean: "polyketide/lanthipeptide biosynthesis", "secondary metabolite production", "the
# biosynthesis of this class", "gives rise to a siderophore" all fail the morphology-name gate.
# The passive agent is required to be an in-strain locus (cluster/BGC/locus/region/pathway/gene/it)
# so a general-knowledge "erythromycin is produced by S. erythraea" background line is not flagged.
_PASSIVE_NOMINAL_RES = (
    # "the biosynthesis of venezuelin", "production of venezuelin", "synthesis of venezuelin"
    re.compile(r"\b(?:biosynthesis|production|biosynthesises|synthesis)\s+of\s+"
               r"([A-Za-z][A-Za-z0-9'\-]{4,})", re.I),
    # "venezuelin production by <locus>", "venezuelin biosynthesis by <locus>"
    re.compile(r"\b([A-Za-z][A-Za-z0-9'\-]{4,})\s+(?:production|biosynthesis)\s+by\b", re.I),
    # "venezuelin is produced/made/assembled/synthesised/elaborated/generated by <locus>"
    re.compile(r"\b([A-Za-z][A-Za-z0-9'\-]{4,})\s+(?:is|are|was|were)\s+"
               r"(?:produced|made|assembled|elaborated|generated|manufactured|"
               r"synthesized|synthesised|biosynthesized|biosynthesised|secreted)\s+by\b", re.I),
    # "gives rise to venezuelin", "give rise to venezuelin"
    re.compile(r"\bgives?\s+rise\s+to\s+([A-Za-z][A-Za-z0-9'\-]{4,})", re.I),
    # "confers venezuelin biosynthesis", "responsible for producing venezuelin"
    re.compile(r"\bconfers\s+([A-Za-z][A-Za-z0-9'\-]{4,})\s+(?:biosynthesis|production)\b", re.I),
    re.compile(r"\bresponsible\s+for\s+(?:producing|making|synthesi[sz]ing|assembling)\s+"
               r"([A-Za-z][A-Za-z0-9'\-]{4,})", re.I),
)
# For the nominalization/passive forms whose captured compound is FOLLOWED by an agent, require that
# agent to be an in-strain locus (not a taxon), so background comparators do not flag.
_INSTRAIN_AGENT_RE = re.compile(
    r"^\s*(?:the\s+|this\s+|a\s+|an\s+)?(?:BGC\d+|cluster|clusters|locus|loci|region|regions|"
    r"pathway|pathways|gene|genes|operon|operons|biosynthetic|it|this)\b", re.I)


def lint_text(text: str) -> list[str]:
    findings: list[str] = []
    # v9.7.409 CANDIDATE (CLAUDE_409/normalize): run every matcher below over a DETECTION-ONLY copy
    # (`norm`) with markdown/quote/bracket wrappers neutralized, zero-width chars dropped, and Unicode
    # look-alikes folded to ASCII — closing DEEP_AUDIT2 #1/#3/#4/#5/#6, where a wrapper or lookalike at
    # the compound's first character made the whole identity family blind. All slicing (clause windows,
    # negation look-back, class-after peeks) is on `norm` so the folds are seen consistently; the
    # emitted finding is mapped back to the ORIGINAL text (`_orig_span`), so packaged output is never
    # altered — only what the detector reads.
    norm, idx_map = _normalize_for_detection(text or "")
    for m in _PRODUCTION_RE.finditer(norm):
        token = m.group(1)
        finding_end = m.end()
        if token.lower() in _SAFE_AFTER:
            # v9.7.377 (AUDIT audit): the immediate word after the verb is a filler/
            # determiner ("the", "a", "compound", "metabolite", ...) — previously that ended the
            # check for this sentence entirely. Ordinary overclaim prose keeps going past the
            # filler to the real compound name via "named X" / "called X" / "known as X" ("produces
            # the compound known as chalcomycin", "produces a novel polyketide named
            # tetrachlorizine") — look ahead a short window for that continuation before conceding
            # the sentence is safe; re-target every check below onto the real candidate it finds.
            tail = norm[finding_end:finding_end + 60]
            named_m = _NAMED_AS_RE.search(tail)
            if not named_m:
                continue
            token = named_m.group(1)
            if token.lower() in _SAFE_AFTER:
                continue
            finding_end = finding_end + named_m.end()
            # "known as the tetrachlorizine family" is class-level, not a product claim — same
            # guard _ANCHOR_LABEL_RE already applies below for the label-anchor construction.
            after = norm[finding_end:finding_end + 12]
            if _CLASS_LEVEL_AFTER.search(after):
                continue
        # v9.7.409 (CLAUDE_409/F1): clause-local safe-context, not a raw ±80-char window.
        if _SAFE_CONTEXT_RE.search(_clause_around(norm, m.start(), finding_end)):
            continue
        # #3b (v9.7.216): a fixed ±80 window misses "does not support that BGC010 produces colibrimycin"
        # (the denial sits 100+ chars upstream). Look back to the start of the sentence (up to 400 chars)
        # for a negation that scopes this verb; if present, it's a denial, not an overclaim.
        s0 = max(0, m.start() - 400)
        upstream = norm[s0:m.start()]
        sent_start = max(upstream.rfind(". "), upstream.rfind("\n"), upstream.rfind("? "), upstream.rfind("! "),
                         upstream.rfind("; "), upstream.rfind("—"))  # ; and — bound negation to its clause
        sentence_before = upstream[sent_start + 1:] if sent_start >= 0 else upstream
        if _NEGATION_RE.search(sentence_before):
            continue
        findings.append(f"possible product-identity overclaim: {_orig_span(text, idx_map, m.start(), finding_end)!r}")
    # v9.7.409 CANDIDATE (CLAUDE_409/F2): the riskier production verbs (secrete/assemble/elaborate/
    # generate/afford/manufacture/encode) — flagged ONLY for a bare object that both is compound-
    # shaped and carries natural-product morphology, so "encodes venezuelin" fires but "encodes a PKS"
    # / "secretes proteins" / "assembles tables" / "encodes azole-RiPP capacity" stay clean. Same
    # clause-local safe-context and clause-scoped negation guards as the permissive path.
    for m in _PRODUCTION_STRICT_RE.finditer(norm):
        token = m.group(1)
        if not _looks_like_compound_name(token) or not _NP_MORPHOLOGY_RE.search(token.lower()):
            continue
        after = norm[m.end():m.end() + 12]
        if _CLASS_LEVEL_AFTER.search(after):
            continue
        if _SAFE_CONTEXT_RE.search(_clause_around(norm, m.start(), m.end())):
            continue
        s0 = max(0, m.start() - 400)
        upstream = norm[s0:m.start()]
        sent_start = max(upstream.rfind(". "), upstream.rfind("\n"),
                         upstream.rfind("? "), upstream.rfind("! "),
                         upstream.rfind("; "), upstream.rfind("—"))
        sentence_before = upstream[sent_start + 1:] if sent_start >= 0 else upstream
        if _NEGATION_RE.search(sentence_before):
            continue
        findings.append(f"possible product-identity overclaim: {_orig_span(text, idx_map, m.start(), m.end())!r}")
    for m in _ANCHOR_LABEL_RE.finditer(norm):
        after = norm[m.end():m.end() + 12]
        if _CLASS_LEVEL_AFTER.search(after):
            continue  # "-> X family" is class-level, not a product claim
        # v9.7.409 (CLAUDE_409/F1): clause-local safe-context, not a raw ±80-char window.
        if _SAFE_CONTEXT_RE.search(_clause_around(norm, m.start(), m.end())):
            continue
        s0 = max(0, m.start() - 400)
        upstream = norm[s0:m.start()]
        sent_start = max(upstream.rfind(". "), upstream.rfind("\n"),
                         upstream.rfind("? "), upstream.rfind("! "),
                         upstream.rfind("; "), upstream.rfind("—"))  # ; and — bound negation to its clause
        sentence_before = upstream[sent_start + 1:] if sent_start >= 0 else upstream
        if _NEGATION_RE.search(sentence_before):
            continue
        findings.append(f"possible anchor-as-product-identity overclaim: {_orig_span(text, idx_map, m.start(), m.end())!r}")
    # v9.7.378b (CODEX post-cut correction A): direct typed-object product-identity claims —
    # "produces the antibiotic streptomycin" and kin — where the compound name follows a class noun
    # with no named/called/known-as connector. Reuses the same _SAFE_CONTEXT_RE / _NEGATION_RE guards
    # so "capacity consistent with ... the compound X" and denial-scoped sentences stay clean.
    for m in _TYPED_OBJECT_RE.finditer(norm):
        name = m.group(1)
        if name.lower() in _TYPED_NON_NAME:
            continue  # generic tail ("polyketide backbone") or connector ("pigment called X") — not a direct name
        # v9.7.409 (CLAUDE_409/F1): clause-local safe-context, not a raw ±80-char window.
        if _SAFE_CONTEXT_RE.search(_clause_around(norm, m.start(), m.end())):
            continue
        s0 = max(0, m.start() - 400)
        upstream = norm[s0:m.start()]
        sent_start = max(upstream.rfind(". "), upstream.rfind("\n"),
                         upstream.rfind("? "), upstream.rfind("! "),
                         upstream.rfind("; "), upstream.rfind("—"))  # ; and — bound negation to its clause
        sentence_before = upstream[sent_start + 1:] if sent_start >= 0 else upstream
        if _NEGATION_RE.search(sentence_before):
            continue
        findings.append(f"possible product-identity overclaim: {_orig_span(text, idx_map, m.start(), m.end())!r}")
    # v9.7.409 CANDIDATE (CLAUDE_409/F2): copula-identity overclaims ("The mature product is
    # venezuelin", "BGC027 is venezuelin"). Narrow by construction — a product-noun/BGC subject plus
    # a compound-shaped object — and guarded by the SAME clause-local safe-context and clause-scoped
    # negation checks as the verb path, so "KCB is similarity, not identity" and "the product is
    # predicted ..." stay clean.
    # v9.7.412 (R4): split-verb, label/table and subject-bound "-producing" identity shapes.
    # (a) a production verb physically split by an HTML comment / hyphen-linebreak, examined at the
    #     split site only. Runs on the RAW text: the normalisation pre-pass folds bracket wrappers to
    #     a newline, which is the very separator this rule looks for.
    for m in _SPLIT_SITE_RE.finditer(text or ""):
        if (m.group(1) + m.group(2)).lower() not in _SPLIT_VERBS:
            continue
        obj = _AFTER_SPLIT_OBJ_RE.match((text or "")[m.end():])
        if not obj:
            continue
        token = obj.group(1)
        if not _looks_like_compound_name(token) or not _NP_MORPHOLOGY_RE.search(token.lower()):
            continue
        if _SAFE_CONTEXT_RE.search(_clause_around(text or "", m.start(), m.end() + obj.end())):
            continue
        if _has_local_negation(text or "", m.start()):
            continue
        findings.append("possible obfuscated production verb: "
                        f"{(text or '')[m.start():m.end() + obj.end()]!r}")
    # (b) label/table and subject-bound producing-compound identity, on the normalised copy.
    for _rx, _label in ((_LABEL_PRODUCT_RE, "label/table product identity"),
                        (_PRODUCING_COMPOUND_RE, "producing-compound identity")):
        _hay = norm
        for m in _rx.finditer(_hay):
            token = m.group(1)
            if not _looks_like_compound_name(token) or not _NP_MORPHOLOGY_RE.search(token.lower()):
                continue
            if _SAFE_CONTEXT_RE.search(_clause_around(_hay, m.start(), m.end())):
                continue
            if _has_local_negation(_hay, m.start()):
                continue
            findings.append(f"possible {_label}: {_orig_span(text, idx_map, m.start(), m.end())!r}")

    for m in _COPULA_IDENTITY_RE.finditer(norm):
        name = m.group(1)
        # Require both a non-generic shape AND natural-product morphology, so "is venezuelin" /
        # "is bottromycin" fire while "is uncharacterised" / "is the strongest lead" stay clean.
        if not _looks_like_compound_name(name) or not _NP_MORPHOLOGY_RE.search(name.lower()):
            continue
        after = norm[m.end():m.end() + 12]
        if _CLASS_LEVEL_AFTER.search(after):
            continue  # "is the tetrachlorizine family" is class-level, not a product claim
        if _SAFE_CONTEXT_RE.search(_clause_around(norm, m.start(), m.end())):
            continue
        s0 = max(0, m.start() - 400)
        upstream = norm[s0:m.start()]
        sent_start = max(upstream.rfind(". "), upstream.rfind("\n"),
                         upstream.rfind("? "), upstream.rfind("! "),
                         upstream.rfind("; "), upstream.rfind("—"))
        sentence_before = upstream[sent_start + 1:] if sent_start >= 0 else upstream
        if _NEGATION_RE.search(sentence_before):
            continue
        findings.append(f"possible product-identity overclaim: {_orig_span(text, idx_map, m.start(), m.end())!r}")
    # v9.7.409 CANDIDATE (CLAUDE_409/normalize): DEEP_AUDIT2 #7 — passive / nominalization production
    # framings ("the biosynthesis of venezuelin", "venezuelin production by this cluster", "venezuelin
    # is produced by BGC027", "gives rise to venezuelin"). Each captured object is double-gated by
    # _looks_like_compound_name AND _NP_MORPHOLOGY_RE (specific-compound name shape only) and by the
    # same clause-local safe-context + clause-scoped negation guards; agent-bearing forms additionally
    # require an in-strain locus after "by" so a general-knowledge comparator ("erythromycin is
    # produced by S. erythraea") stays clean.
    for _rx in _PASSIVE_NOMINAL_RES:
        for m in _rx.finditer(norm):
            name = m.group(1)
            if not _looks_like_compound_name(name) or not _NP_MORPHOLOGY_RE.search(name.lower()):
                continue
            if m.group(0).rstrip().lower().endswith(" by"):
                # agent-bearing passive/nominalization — require an in-strain locus as the agent
                if not _INSTRAIN_AGENT_RE.search(norm[m.end():m.end() + 48]):
                    continue
            if _SAFE_CONTEXT_RE.search(_clause_around(norm, m.start(), m.end())):
                continue
            s0 = max(0, m.start() - 400)
            upstream = norm[s0:m.start()]
            sent_start = max(upstream.rfind(". "), upstream.rfind("\n"),
                             upstream.rfind("? "), upstream.rfind("! "),
                             upstream.rfind("; "), upstream.rfind("—"))
            sentence_before = upstream[sent_start + 1:] if sent_start >= 0 else upstream
            if _NEGATION_RE.search(sentence_before):
                continue
            findings.append(f"possible product-identity overclaim: {_orig_span(text, idx_map, m.start(), m.end())!r}")
    # v9.7.374 (AUDIT audit): this module previously had NO bioactivity-phenotype check at
    # all (_PRODUCTION_RE/_ANCHOR_LABEL_RE are identity-overclaim only) — confirmed live: a
    # sentence like "The BGC001 cluster shows antibacterial activity against Staphylococcus
    # aureus" returned zero findings here even though the project's own claim-safety rule
    # ("bioactivity is strain-level context unless wet-lab evidence exists") exists specifically
    # to catch it, and manifest["claim_safety_status"] (written from this function's caller,
    # packaging.py::write_manifest) is the field CLAUDE.md documents as the authoritative
    # handoff to the judgment kernel. Delegate to the already-calibrated H3 check rather than
    # re-deriving it, to avoid a THIRD independently-drifting copy of the same logic (a second
    # copy — tools/claim_safety_linter.py::lint_claim_safety() vs lint_claim_safety_report() —
    # was already a live gap; see AUDIT_374_claim_safety_gate_tools_bioactivity_gate_missing).
    try:
        from claim_safety_linter import lint_claim_safety_report as _lint_report
        # v9.7.409 (CLAUDE_409/normalize N3): MILD fold (invisible-char strip + look-alike fold only,
        # wrappers intact) so a homoglyph/zero-width in a bioactivity token cannot slip the H3 check.
        mild, _mild_map = _normalize_for_detection(text or "", fold_wrappers=False)
        for row in _lint_report(mild):
            if row.get("violation_type") == "bioactivity_phenotype":
                findings.append(f"possible bioactivity-phenotype overclaim: {row.get('sentence', '')!r}")
    except Exception as exc:
        # v9.7.409 B3 (SF-2): this was `pass` -- a crashed or missing bioactivity check made the
        # gate report PASS on text it never scanned (clean-by-crash). Emit a finding instead so
        # claim_safety_status can never be clean when the scan did not run; packaging still does
        # not crash. Fail CLOSED, like the receipt door's GATE_UNAVAILABLE sentinel.
        findings.append(f"CLAIM_SAFETY_LINTER_UNAVAILABLE: bioactivity-phenotype check did not run "
                        f"({type(exc).__name__}: {exc}); claim-safety scan incomplete")
    return findings


def candidate_text_files(package_dir: str | Path) -> tuple[list[Path], list[str]]:
    """Every claim-safety-relevant file under `package_dir`, plus any directory this walk
    could not descend into.

    v9.7.401 (BC2): replaced `root.rglob("*")`, which silently swallows a per-directory
    OSError -- an unreadable subdirectory's contents are simply absent from the scan, with no
    signal. Reproduced live against the real pristine function: an overclaim-carrying report
    (`produces the antibiotic streptomycin`) hidden inside a permission-locked subdirectory of
    a package is completely invisible -- `run_claim_safety_gate()` returns zero candidate
    files and reports `claim_safety_status: "NOT_REQUESTED"` (sounding even MORE benign than a
    false "PASS" would). This is the highest-stakes instance of this round's recurring
    `rglob()`-silent-coverage-gap pattern found so far: `manifest["claim_safety_status"]` is,
    per this module's own comment history, "the field CLAUDE.md documents as the authoritative
    handoff to the judgment kernel" for overclaim detection. A missing top path (root does not
    exist) returns `([], [])`, matching `rglob()`'s own silent-empty behavior for a missing
    path -- unlike `rglob()`, `os.walk(..., onerror=...)` calls `onerror` even for a missing
    top path, so this distinction must be made explicitly.
    """
    root = Path(package_dir)
    if not root.exists():
        return [], []
    files: list[Path] = []
    unreadable: list[str] = []

    def _onerror(exc: OSError) -> None:
        unreadable.append(getattr(exc, "filename", None) or str(exc))

    for dirpath, dirnames, filenames in os.walk(root, onerror=_onerror):
        for name in filenames:
            if Path(name).suffix.lower() in CANDIDATE_SUFFIXES and CANDIDATE_NAME_RE.search(name):
                files.append(Path(dirpath) / name)
    return sorted(files), unreadable


def run_claim_safety_gate(package_dir: str | Path) -> dict[str, Any]:
    root = Path(package_dir)
    files, unreadable = candidate_text_files(root)
    findings: list[dict[str, Any]] = []
    for d in unreadable:
        # v9.7.401 (BC2): a directory this scan could not enter means the scan is INCOMPLETE --
        # any claim-safety-relevant file inside it (which may carry a real overclaim) was never
        # examined. Surface that as its own finding rather than silently reporting fewer files
        # checked, so the manifest's claim_safety_status can never read as clean/not-applicable
        # when part of the package was genuinely unscanned.
        findings.append({"path": d, "error": "directory unreadable — claim-safety scan incomplete, contents unexamined"})
    for p in files:
        rel = str(p.relative_to(root))
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            findings.append({"path": rel, "error": f"read failed: {type(exc).__name__}: {exc}"})
            continue
        for f in lint_text(text):
            findings.append({"path": rel, "finding": f})
    status = "NOT_REQUESTED" if not files and not unreadable else ("PASS" if not findings else "FAIL")
    return {
        "schema_version": "claim_safety_gate_v1",
        "claim_safety_status": status,
        "files_checked": [str(p.relative_to(root)) for p in files],
        "finding_count": len(findings),
        "findings": findings,
    }


def write_claim_safety_receipt(package_dir: str | Path) -> Path:
    root = Path(package_dir)
    payload = run_claim_safety_gate(root)
    path = root / "claim_safety_status.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
