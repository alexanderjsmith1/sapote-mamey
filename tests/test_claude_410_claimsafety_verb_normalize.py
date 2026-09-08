"""Fail-before / pass-after battery for CLAUDE_410_claimsafety_verb_normalize (v9.7.410).

Target: mamey/claim_safety_gate.py::_normalize_for_detection / lint_text, on the pristine v9.7.409 base.

Evidence: development/round6_v409/CLAIMSAFETY_EVASION_REATTACK.md, Battery B. The .409 detection-only
normalization closed every .408 evasion on the COMPOUND position (Battery A: 31/31 caught, 0/6 false
positives), but the PRODUCTION-VERB position was still defended only by the homoglyph confusable table.
Five evasions were execution-confirmed OPEN on pristine .409 (each returned 0 findings):

    HD1   accented verb            `prodúces streptomycin`
    HD5   leetspeak verb           `pr0duces streptomycin`
    HD15  intra-word emphasis      `pro**duces** streptomycin`
    HD17  literal HTML entity gap  `produces&nbsp;streptomycin`
    HD18  escaped wrapper          `produces \\*streptomycin\\*`

Part A below FAILS on pristine .409 and PASSES with the lane patch. Parts B–E must pass on BOTH (they are
the regression guard: the Battery A strings, the six clean controls, accented organism names, digit-bearing
tokens such as `BGC027` / gene counts, and the original-substring mapping of the emitted finding).

Run: `pytest tests/test_claude_410_claimsafety_verb_normalize.py -q` under the bundle's Python 3.12 target.
"""
import importlib

import pytest

claim_safety_gate = importlib.import_module("mamey.claim_safety_gate")
lint_text = claim_safety_gate.lint_text
_normalize_for_detection = claim_safety_gate._normalize_for_detection


def _flagged(s: str) -> bool:
    return len(lint_text(s)) > 0


def _delegate_available() -> bool:
    try:
        importlib.import_module("claim_safety_linter")
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# PART A — FAIL-BEFORE / PASS-AFTER: the five verb-position evasions still open on .409, each with a
# close variant that exercises the same stage of the fix from a second angle.
# ---------------------------------------------------------------------------

VERB_POSITION_EVASIONS = [
    ("HD1 accented verb (precomposed)", "BGC027 prodúces streptomycin."),
    ("HD1b accented verb (decomposed combining mark)", "BGC027 produ\u0301ces streptomycin."),
    ("HD5 leetspeak 0->o", "BGC027 pr0duces streptomycin."),
    ("HD5b leetspeak 1->i, 3->e", "BGC027 y13lds streptomycin."),
    ("HD5c leetspeak 4->a, 5->s on strict verb", "BGC027 encode5 venezuelin."),
    ("HD15 intra-word bold on verb", "BGC027 pro**duces** streptomycin."),
    ("HD15b intra-word underscore on verb", "BGC027 pro_duces_ streptomycin."),
    ("HD15c intra-word code-span on verb", "BGC027 pro`duces` streptomycin."),
    ("HD17 literal &nbsp; gap", "BGC027 produces&nbsp;streptomycin."),
    ("HD17b numeric entities in gap and compound", "BGC027 produces&#160;strept&#111;mycin."),
    ("HD18 escaped emphasis wrapper", "BGC027 produces \\*streptomycin\\*."),
    ("HD18b escaped underscore wrapper", "BGC027 produces \\_streptomycin\\_."),
    ("HD-mix: accent + intra-word split + entity", "BGC027 pro**dúces**&nbsp;streptomycin."),
]


@pytest.mark.parametrize("name,s", VERB_POSITION_EVASIONS, ids=[c[0] for c in VERB_POSITION_EVASIONS])
def test_A_verb_position_evasions_now_flagged(name, s):
    assert _flagged(s), f"verb-position evasion must flag [{name}]: {s!r}"


def test_A_normalized_detection_copy_repairs_the_verb():
    """The detection copy (what the matchers SEE) reads the plain verb; whitespace count is irrelevant."""
    for s in ("BGC027 prodúces streptomycin.", "BGC027 pr0duces streptomycin.",
              "BGC027 pro**duces** streptomycin.", "BGC027 produces&nbsp;streptomycin."):
        norm, _ = _normalize_for_detection(s)
        assert "produces" in norm.split(), (s, norm)


# ---------------------------------------------------------------------------
# PART B — Battery A (the 31 .408-class overclaim strings the .409 pre-pass already catches) must stay
# caught. Reconstructed from CLAIMSAFETY_EVASION_REATTACK.md's Battery A table.
# ---------------------------------------------------------------------------

BATTERY_A = [
    # P1–P8 plain / typed / copula / strict / passive-nominal
    "BGC027 produces streptomycin.",
    "BGC027 produces the antibiotic streptomycin.",
    "The mature product is venezuelin.",
    "BGC027 encodes venezuelin.",
    "the biosynthesis of venezuelin",
    "venezuelin production by this cluster",
    "venezuelin is produced by BGC027",
    "BGC027 gives rise to venezuelin",
    # M1–M9 markdown wrappers on the compound
    "BGC027 produces **streptomycin**.",
    "BGC027 produces _streptomycin_.",
    "BGC027 produces *streptomycin*.",
    "BGC027 produces `streptomycin`.",
    "BGC027 produces the antibiotic **streptomycin**.",
    "BGC027 produces [venezuelin](https://example.org).",
    "The product is **venezuelin**.",
    'BGC027 produces "streptomycin".',
    "BGC027 produces (streptomycin).",
    # H1 / H2 homoglyphs
    "BGC027 prоduces streptomycin.",   # Cyrillic о in the verb
    "BGC027 produces strеptomycin.",   # Cyrillic е in the compound
    # Z1–Z3 zero-width / soft hyphen
    "BGC027 produces strep\u200btomycin.",
    "BGC027 produces\u200b streptomycin.",
    "BGC027 produces strep\u00adtomycin.",
    # E1–E3 exemption poisoning
    "a desertomycin-like comparator; BGC027 produces streptomycin.",
    "a candidate cluster; BGC027 produces streptomycin.",
    "the extract was tested; BGC027 produces streptomycin.",
    # T1 / T2 typed-object
    "BGC027 produces the metabolite erythromycin.",
    "BGC027 produces the compound chalcomycin.",
    # boundary cases the re-attack listed as CAUGHT on .409
    "BGC027 produces strept0mycin.",          # digit inside the COMPOUND
    "BGC027 ｐroduces streptomycin.",          # fullwidth verb (NFKC)
    "BGC027 produces\u00a0streptomycin.",      # real NBSP
    "BGC027 produces strep**tomycin**.",       # emphasis splitting the compound
]


@pytest.mark.parametrize("s", BATTERY_A)
def test_B_battery_A_still_caught(s):
    assert _flagged(s), f"Battery A overclaim must still flag: {s!r}"


BIOACTIVITY_BATTERY = [
    "BGC001 shows antibacterial activity against Staphylococcus aureus.",
    "BGC001 is **active against** MRSA.",
    "The locus is aсtive against MRSA.",  # Cyrillic с
]


@pytest.mark.skipif(not _delegate_available(), reason="tools/claim_safety_linter.py (H3 delegate) not importable")
@pytest.mark.parametrize("s", BIOACTIVITY_BATTERY)
def test_B_bioactivity_battery_still_caught(s):
    assert _flagged(s), f"bioactivity overclaim must still flag: {s!r}"


# ---------------------------------------------------------------------------
# PART C — NO FALSE POSITIVES. The six Battery A controls, the .409 CLEAN block, and the new stages'
# own guards: accented organism / place names, digit-bearing identifiers, literal ampersands,
# backslashes that are not markdown escapes, snake_case identifiers.
# ---------------------------------------------------------------------------

CLEAN = [
    # the six Battery A controls (N1–N6)
    ("N1 clause-local similarity hedge", "shows similarity to venezuelin (2/19 genes); similarity anchor only"),
    ("N2 negation", "There is no evidence that BGC027 produces venezuelin."),
    ("N3 capacity frame", "capacity consistent with a desertomycin-like comparator_context"),
    ("N4 extract-level bioactivity", "The crude extract showed activity in the plate assay."),
    ("N5 class-level backbone", "BGC027 produces a polyketide backbone."),
    ("N6 secretes proteins", "The cluster secretes proteins."),
    # .409 CLEAN block
    ("encodes a PKS", "The locus encodes a PKS."),
    ("is uncharacterised", "The product is uncharacterised."),
    ("region is a lanthipeptide", "The region is a lanthipeptide."),
    ("predicted to be", "The product is predicted to be a polyketide."),
    ("kcb similarity not identity", "KCB is similarity, not identity."),
    ("polyketide biosynthesis", "polyketide biosynthesis genes are present"),
    ("comparator produced-by-taxon", "erythromycin is produced by S. erythraea in the literature"),
    ("makes-compound-uncharacterised", "this makes the *compound* uncharacterised, not the machinery"),
    ("negated contraction", "BGC027 doesn't produce venezuelin."),
    # NEW-stage guards
    ("accented organism names", "Isolated from Amycolatopsis méditerranei; Streptomyces Ångström-12 encodes a PKS."),
    ("accented place / host names", "Kitasatospora sp. AS-40 was isolated in São Paulo from Blåbær-associated soil."),
    ("digit-bearing identifiers untouched", "BGC027, ctg1_5031 and 10 of 19 genes are shared; K-mer 31."),
    ("literal ampersands", "R&D on 2 BGCs; AT&T; Tom &amp; Jerry; salt &lt; 3%."),
    ("non-markdown backslashes", "C:\\Users\\path and \\alpha values were recorded."),
    ("snake_case identifiers", "see claim_safety_status.json and the ecology_section file."),
    ("clean sentence", "The BGC027 region encodes a class-IV lanthipeptide synthetase."),
]


@pytest.mark.parametrize("name,s", CLEAN, ids=[c[0] for c in CLEAN])
def test_C_clean_language_stays_clean(name, s):
    assert not _flagged(s), f"legitimate language must stay clean [{name}]: {s!r}"


def test_C_digit_identifiers_are_not_folded_in_detection_copy():
    """Stage C is keyword-gated: `BGC027` must NOT become `BGCo2t` (the copula path keys on BGC\\d+)."""
    norm, _ = _normalize_for_detection("BGC027 is venezuelin; 10 of 19 genes; ctg1_5031")
    assert "BGC027" in norm and "10 of 19" in norm and "ctg15031" in norm, norm
    assert _flagged("BGC027 is venezuelin."), "copula path on a BGC\\d+ subject must still fire"


def test_C_possessive_apostrophe_still_splits():
    """Quote/apostrophe wrappers are NOT intra-word-deleted: `venezuelin's` keeps the .409 behaviour."""
    assert _flagged("The product is venezuelin's core.")


# ---------------------------------------------------------------------------
# PART D — the emitted finding is the ORIGINAL substring (detection copy never leaks into output).
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("s,frag", [
    ("BGC027 pr0duces streptomycin.", "pr0duces"),
    ("BGC027 prodúces streptomycin.", "prodúces"),
    ("BGC027 pro**duces** streptomycin.", "pro**duces**"),
    ("BGC027 produces&nbsp;streptomycin.", "produces&nbsp;streptomycin"),
    ("BGC027 produces \\*streptomycin\\*.", "\\*streptomycin"),
])
def test_D_emitted_text_is_original_not_normalized(s, frag):
    findings = lint_text(s)
    assert findings, s
    assert frag in " ".join(findings), (frag, findings)


def test_D_mild_fold_keeps_wrappers_and_verb_tokens_untouched():
    """The H3 delegate's mild fold gains only entity decode + escape strip; wrappers and verb repair stay off."""
    mild, _ = _normalize_for_detection("pro**duces** \\*x\\* &amp; pr0duces&nbsp;y", fold_wrappers=False)
    assert mild == "pro**duces** *x* & pr0duces\u00a0y".replace("\u00a0", " "), mild


# ---------------------------------------------------------------------------
# PART E — idx_map integrity: every normalized offset maps to a valid original offset, monotonically.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("s", [c[1] for c in VERB_POSITION_EVASIONS] + BATTERY_A + [c[1] for c in CLEAN])
def test_E_idx_map_is_valid_and_monotone(s):
    norm, idx = _normalize_for_detection(s)
    assert len(norm) == len(idx)
    assert all(0 <= i < len(s) for i in idx)
    assert all(a <= b for a, b in zip(idx, idx[1:]))
