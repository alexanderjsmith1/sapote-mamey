"""test_llm_trustworthiness.py — v9.7.354 F02 rework: adversarial + calibration fixtures.

The v0 linter (backed out of .353, external audit F02 REJECT_AS_IS) treated a bare local BGC id as an
evidence anchor, so "BGC001 produces nystatin … confirmed producer" scored 100/100 with 0 flags. These
tests PIN the fix: a bare local BGC id is NOT evidence; the canonical over-claim scores OVER-CLAIMING;
and legitimate hedged / honest / genuinely-anchored text is NOT punished.
"""
import importlib.util
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "llm_trustworthiness.py"
_spec = importlib.util.spec_from_file_location("llm_trustworthiness", TOOL)
llt = importlib.util.module_from_spec(_spec)
sys.modules["llm_trustworthiness"] = llt  # required so @dataclass can resolve cls.__module__
_spec.loader.exec_module(llt)
assess = llt.assess_trustworthiness


def _kinds(rep):
    return {f.kind for f in rep.flags}


# ── THE F02 REGRESSION: the exact over-claim the v0 module green-lit ──────────────────
def test_confirmed_producer_overclaim_is_caught():
    """The audit's own counterexample. v0 scored this 100/100 EVIDENCE-BACKED with 0 flags."""
    rep = assess("BGC001 produces nystatin and is a confirmed producer.")
    assert rep.verdict == "OVER-CLAIMING", f"expected OVER-CLAIMING, got {rep.verdict} ({rep.score})"
    assert rep.score < 50
    assert "UNCITED_STRONG_CLAIM" in _kinds(rep)
    assert "VERIFIED_WITHOUT_ANCHOR" in _kinds(rep)


def test_bare_local_bgc_id_is_not_evidence():
    """A bare BGCnn locator must not satisfy the citation check for a strong claim."""
    rep = assess("BGC031 is an antifungal.")
    assert "UNCITED_STRONG_CLAIM" in _kinds(rep)
    assert rep.verdict != "EVIDENCE-BACKED"


def test_node_and_region_locators_are_not_evidence():
    rep = assess("NODE_10 region001 produces a polyene.")
    assert "UNCITED_STRONG_CLAIM" in _kinds(rep)


# ── TYPED, PROVENANCE-BEARING anchors DO count ───────────────────────────────────────
def test_seven_digit_mibig_accession_is_evidence():
    """A real MIBiG accession (BGC + 7 digits) is provenance; a local BGCnn (2-3 digits) is not."""
    rep = assess("BGC001 shows similarity to the nystatin cluster MIBiG BGC0000115; "
                 "a candidate polyene-family cluster, judgment deferred.")
    assert rep.verdict == "EVIDENCE-BACKED", f"{rep.verdict} {rep.score} {_kinds(rep)}"
    assert "UNCITED_STRONG_CLAIM" not in _kinds(rep)


def test_file_line_anchor_satisfies_verify_claim():
    rep = assess("I verified in scoring.py:527 that the polyene clamp fires.")
    assert "VERIFIED_WITHOUT_ANCHOR" not in _kinds(rep)
    assert rep.verdict == "EVIDENCE-BACKED"


def test_accession_anchor_counts():
    rep = assess("The locus is identical to WP_012345678.1.")
    assert "UNCITED_STRONG_CLAIM" not in _kinds(rep)


# ── HEDGED / HONEST text is NOT punished (must stay usable on real class-level cards) ──
def test_hedged_strong_claim_not_flagged():
    rep = assess("BGC001 may produce a nystatin-like compound; a candidate cluster, judgment deferred.")
    assert "UNCITED_STRONG_CLAIM" not in _kinds(rep)
    assert rep.verdict == "EVIDENCE-BACKED"


def test_honest_non_verification_disclosure_not_penalized():
    rep = assess("I have not verified that BGC001 produces nystatin.")
    assert rep.verdict != "OVER-CLAIMING"
    assert "UNCITED_STRONG_CLAIM" not in _kinds(rep)
    assert "VERIFIED_WITHOUT_ANCHOR" not in _kinds(rep)


def test_clean_class_level_card_scores_well():
    rep = assess("BGC031 is a candidate NRPS-family cluster (per the triage board); judgment deferred. "
                 "Its class assignment is a routing prior, not a measured activity.")
    assert rep.verdict == "EVIDENCE-BACKED"
    assert not rep.flags


# ── secondary calibration signals still fire ─────────────────────────────────────────
def test_metric_without_denominator_flags():
    rep = assess("The set spans 1787 regions across the strains.")
    assert "METRIC_NO_DENOMINATOR" in _kinds(rep)


def test_overconfident_intensifier_flags_but_is_minor():
    rep = assess("This is clearly a candidate cluster, judgment deferred.")
    assert "OVERCONFIDENT" in _kinds(rep)
    # a lone intensifier should not by itself drop text out of EVIDENCE-BACKED
    assert rep.verdict == "EVIDENCE-BACKED"


def test_lowercase_prose_words_are_not_anchors():
    """Case-sensitivity fix: 'pass'/'figure' as ordinary words must not satisfy citation."""
    rep = assess("These results pass review and the figure looks right, and BGC001 produces nystatin.")
    assert "UNCITED_STRONG_CLAIM" in _kinds(rep)
