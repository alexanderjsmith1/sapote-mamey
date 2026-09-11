"""v9.7.378b (CODEX post-cut correction A) — claim-safety gate overclaim coverage.

Two regressions are locked here:

1. The v9.7.377 filler-word continuation: a production verb followed by a filler/determiner
   ("the", "a", "compound", "metabolite", ...) that then continues to the real compound via
   "named X" / "called X" / "known as X" must be flagged, not conceded as safe.

2. The v9.7.378b direct typed-object construction: "produces the antibiotic streptomycin",
   "produces the compound streptomycin", "produces the metabolite erythromycin" — a compound
   named immediately after a CLASS NOUN with no connector. These slipped through the sealed
   .378 gate (confirmed live by the Codex post-cut audit) because _NAMED_AS_RE only fires on a
   named/called/known-as connector.

Generic capacity phrasing ("produces a polyketide backbone"), class-noun-with-no-name
("produces the compound"), safe-context ("capacity consistent with ..."), and negation-scoped
sentences must remain clean.
"""
from mamey.claim_safety_gate import lint_text


# --- must FLAG: filler-word continuation (v9.7.377 behavior, retained) ---
FLAG_NAMED = [
    "This BGC produces a pigment called violacein.",
    "This BGC produces a novel polyketide named tetrachlorizine.",
    "This BGC produces the compound known as chalcomycin.",
]

# --- must FLAG: direct typed-object construction (v9.7.378b, the fix) ---
FLAG_TYPED = [
    "This BGC produces the antibiotic streptomycin.",
    "This BGC produces the compound streptomycin.",
    "This BGC produces the metabolite erythromycin.",
    "This BGC produces the molecule actinomycin.",
    "This BGC produces the pigment prodigiosin.",
]

# --- must FLAG: direct bare-name construction (pre-existing behavior, guard against regression) ---
FLAG_BARE = [
    "This BGC produces erythromycin.",
]

# --- must stay CLEAN: generic capacity / no specific name / safe context / negation ---
CLEAN = [
    "This BGC produces a polyketide backbone.",
    "This BGC produces the compound.",
    "The region shows capacity consistent with a polyketide.",
    "capacity consistent with the compound streptomycin",
    "No evidence that this BGC produces the antibiotic streptomycin.",
    "This does not support that the BGC produces the metabolite erythromycin.",
    "Architecture consistent with a nonribosomal peptide synthetase pathway.",
]


def test_filler_word_named_continuation_is_flagged():
    for s in FLAG_NAMED:
        assert lint_text(s), f"expected a finding for named/called continuation: {s!r}"


def test_direct_typed_object_overclaim_is_flagged():
    for s in FLAG_TYPED:
        assert lint_text(s), f"expected a finding for direct typed-object overclaim: {s!r}"


def test_bare_direct_name_still_flagged():
    for s in FLAG_BARE:
        assert lint_text(s), f"expected a finding for bare direct name: {s!r}"


def test_generic_and_safe_context_stay_clean():
    for s in CLEAN:
        assert not lint_text(s), f"expected NO finding (generic/safe/negation): {s!r}"


def test_typed_object_names_the_offending_span():
    # the finding should quote the actual claim span so a human can locate it
    out = lint_text("This BGC produces the antibiotic streptomycin.")
    assert any("streptomycin" in f for f in out), out
