"""Fail-before / pass-after battery for CLAUDE_409_claimsafety_normalize.

Target: mamey/claim_safety_gate.py::lint_text, AFTER the CLAUDE_409_claim_safety_enforce lane's
CS_claim_safety_gate.patch is applied (this lane co-applies on top of it — see PATCH_CARD.md).

Evidence: development/DEEP_AUDIT2_claimsafety_detector.md — 11 adversarial evasions of the HARDENED
detector. This lane closes the tokenization-layer holes the enforce lane never touched: a normalization
pre-pass (NFKC fold, zero-width strip, Unicode confusable map, markdown/quote/bracket wrapper
neutralization) run over a DETECTION-ONLY copy, plus `:`/`(` clause boundaries and passive/
nominalization verb coverage.

Run under the bundle's Python 3.12 target: `pytest tests/TESTS_CLAUDE_409_claimsafety_normalize.py -q`
(place under tests/). The two #5 bioactivity cases need tools/claim_safety_linter.py importable (the H3
delegate); they self-skip if it is not, exactly as the identity cases do not depend on it.

CRITICAL — the NO-FALSE-POSITIVE block (Part C) is the guard on this lane: normalization + broader
matching must NOT begin flagging legitimate hedged/negated capacity language. Every Part C case is a
real or realistic clean/hedged Mode B construct (including the real BGC027 card's own §16 "makes the
*compound* uncharacterised" idiom and §12 hedged class-prior line) and MUST stay clean relative to the
enforce-hardened baseline.
"""
import importlib

import pytest

claim_safety_gate = importlib.import_module("mamey.claim_safety_gate")
lint_text = claim_safety_gate.lint_text


def _flagged(s: str) -> bool:
    return len(lint_text(s)) > 0


def _delegate_available() -> bool:
    try:  # the H3 bioactivity delegate lives in tools/ and pulls in sibling package modules
        importlib.import_module("claim_safety_linter")
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# PART A — FAIL-BEFORE / PASS-AFTER: identity-overclaim evasions that got past the HARDENED detector
# (DEEP_AUDIT2 findings #1, #2, #3, #4, #6, #7). Each was EVADED on enforce-only; each must now flag.
# ---------------------------------------------------------------------------

# #1 (WORST): ordinary markdown emphasis / code / link / quote / paren wrappers on the compound name.
MARKDOWN_WRAPPED = [
    "BGC027 produces *venezuelin* in culture.",
    "BGC027 produces **venezuelin**.",
    "BGC027 produces `venezuelin`.",
    "BGC027 produces _venezuelin_.",
    "BGC027 produces [venezuelin](x).",
    'BGC027 produces "venezuelin".',
    "BGC027 produces (venezuelin).",
    "The mature product is *venezuelin*.",           # copula path
    "BGC027 is **venezuelin**.",                       # copula path
    "BGC027 produces the antibiotic `venezuelin`.",    # typed-object path
    "BGC027 produces the compound known as *tetrachlorizine*.",  # named-as path
]


@pytest.mark.parametrize("s", MARKDOWN_WRAPPED)
def test_A1_markdown_wrapped_identity_now_flagged(s):
    assert _flagged(s), f"markdown-wrapped identity overclaim should flag: {s!r}"


# #2: same-clause safe-phrase laundering via an inline label (`:`) or a trailing parenthetical (`(`).
CLAUSE_LAUNDERED = [
    "similarity anchor: BGC027 produces venezuelin here",
    "BGC027 produces venezuelin (similarity anchor)",
    "capacity consistent with: BGC027 produces venezuelin here",
    "not identity: BGC027 produces venezuelin here",
    "comparator_context: the product is venezuelin",
]


@pytest.mark.parametrize("s", CLAUSE_LAUNDERED)
def test_A2_clause_laundered_identity_now_flagged(s):
    assert _flagged(s), f"colon/parenthetical-laundered overclaim should flag: {s!r}"


# #3 / #4 / #6: Unicode homoglyph / fullwidth / zero-width in the verb, and stray apostrophe wrappers.
UNICODE_AND_APOSTROPHE = [
    "BGC027 prоduces venezuelin",   # #3 Cyrillic o in the verb
    "BGC027 ｐroduces venezuelin",   # #3 fullwidth p in the verb
    "BGC027 pro​duces venezuelin",  # #4 zero-width space in the verb
    "The product is venezuelin's core.", # #6 possessive apostrophe on the compound
    "The cluster encodes 'venezuelin'.", # #6 single-quote-wrapped compound
]


@pytest.mark.parametrize("s", UNICODE_AND_APOSTROPHE)
def test_A3_unicode_and_apostrophe_now_flagged(s):
    assert _flagged(s), f"unicode/apostrophe-obfuscated overclaim should flag: {s!r}"


# #7: passive / nominalization production framings outside the old verb allow-list.
PASSIVE_NOMINAL = [
    "venezuelin production by this cluster",
    "venezuelin is produced by BGC027",
    "the biosynthesis of venezuelin",
    "BGC027 gives rise to venezuelin",
    "BGC027 is responsible for producing venezuelin",
    "this locus confers venezuelin biosynthesis",
]


@pytest.mark.parametrize("s", PASSIVE_NOMINAL)
def test_A4_passive_nominalization_now_flagged(s):
    assert _flagged(s), f"passive/nominalization overclaim should flag: {s!r}"


# ---------------------------------------------------------------------------
# PART B — #5: homoglyph / zero-width in a BIOACTIVITY key token. Needs the H3 delegate importable.
# ---------------------------------------------------------------------------

BIOACTIVITY_OBFUSCATED = [
    "The locus is aсtive against MRSA",  # Cyrillic c in "active"
    "The product ki​lls MRSA",           # zero-width space in "kills"
]


@pytest.mark.skipif(not _delegate_available(), reason="tools/claim_safety_linter.py (H3 delegate) not importable")
@pytest.mark.parametrize("s", BIOACTIVITY_OBFUSCATED)
def test_B_bioactivity_obfuscated_now_flagged(s):
    assert _flagged(s), f"obfuscated bioactivity phenotype should flag: {s!r}"


# ---------------------------------------------------------------------------
# PART C — NO FALSE POSITIVES. The round-1 clean/hedged battery + the new machinery's own FP guards.
# Every one of these must stay CLEAN. If any flags, the normalization/broadening is too aggressive.
# ---------------------------------------------------------------------------

CLEAN = [
    # round-1 clean/hedged lane
    ("encodes a PKS", "The locus encodes a PKS."),
    ("similarity 2/19", "shows similarity to venezuelin (2/19 genes)"),
    ("is uncharacterised", "The product is uncharacterised."),
    ("secretes proteins", "The cluster secretes proteins."),
    ("region is a lanthipeptide", "The region is a lanthipeptide."),
    ("predicted to be", "The product is predicted to be a polyketide."),
    ("capacity-consistent hedge", "capacity consistent with a desertomycin-like comparator_context"),
    ("kcb similarity not identity", "KCB is similarity, not identity."),
    # guards on the NEW passive/nominalization machinery — class/generic objects must NOT flag
    ("polyketide biosynthesis", "polyketide biosynthesis genes are present"),
    ("secondary metabolite production", "secondary metabolite production is inferred"),
    ("biosynthesis of this class", "the biosynthesis of this class is conserved"),
    ("gives rise to a lanthipeptide", "this gives rise to a lanthipeptide scaffold"),
    ("production of enzymes", "production of enzymes is annotated"),
    # in-strain-agent gate: a general-knowledge comparator (agent is a taxon, not a locus) must NOT flag
    ("comparator produced-by-taxon", "erythromycin is produced by S. erythraea in the literature"),
    # normalization must not turn the "makes the <noun> <adjective>" idiom into a product claim
    # (real BGC027 card §16: "makes the *compound* uncharacterised, not the *machinery*")
    ("makes-compound-uncharacterised", "this makes the *compound* uncharacterised, not the machinery"),
    # apostrophe->space normalization must NOT break contraction-negation (would be a false positive)
    ("negated contraction", "BGC027 doesn't produce venezuelin."),
    ("negated no-evidence", "There is no evidence that BGC027 produces venezuelin."),
]


@pytest.mark.parametrize("name,s", CLEAN, ids=[c[0] for c in CLEAN])
def test_C_clean_hedged_language_stays_clean(name, s):
    assert not _flagged(s), f"legitimate hedged/negated language must stay clean [{name}]: {s!r}"


# ---------------------------------------------------------------------------
# PART D — the emitted finding text is mapped back to the ORIGINAL substring (detection copy is a
# COPY; packaged output is never altered). The normalized detector must still surface the real text.
# ---------------------------------------------------------------------------

def test_D_emitted_text_is_original_not_normalized():
    findings = lint_text("BGC027 produces *venezuelin*.")
    assert findings, "control markdown-wrapped overclaim should flag"
    joined = " ".join(findings)
    assert "venezuelin" in joined, "emitted finding should name the original compound"


# ---------------------------------------------------------------------------
# PART E — baseline controls unchanged: plain overclaims still flagged; the F1 cross-clause regression
# (enforce lane) still flagged; a plainly clean sentence stays clean.
# ---------------------------------------------------------------------------

def test_E_baseline_controls():
    assert _flagged("BGC027 produces venezuelin."), "plain overclaim must still flag"
    assert _flagged("produces venezuelin; similarity is discussed below."), "F1 cross-clause must still flag"
    assert not _flagged("The BGC027 region encodes a class-IV lanthipeptide synthetase."), "clean sentence"
