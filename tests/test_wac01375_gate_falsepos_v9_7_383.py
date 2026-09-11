"""v9.7.383 — gate false-positives surfaced by the WAC-01375 audit.

Disposition authority: Codex WAC01375_30_WEAKNESSES triage (2026-08-27). Two gate defects were
confirmed; only ONE is folded here, because the other's naive fix opened a claim-safety hole.

FOLDED — §35 protocluster heading exclusion (PATCH_01, adversarially tested below).
NOT FOLDED — negation vocabulary expansion (PATCH_02). Reverted: adding "not proof" to the flat
`_NEGATION_RE` suppressed a LATER independent production claim across a semicolon
("...not proof of novelty; the strain produces rifamycin.") — a claim-safety FALSE NEGATIVE,
worse than the false positive it fixed. The proper fix is scope-aware negation (batch 1); the
requirement is encoded as an xfail below so the fix has a ready spec.
"""
import pytest

from mamey import modeb_structure_gate as msg
from mamey import claim_safety_gate as csg

_PAT = r"(\d+)\s*protoclusters?"


# ---- §35 heading exclusion (FOLDED — must pass) -----------------------------------------

def test_section35_heading_contributes_no_count():
    card = "## §35 Protocluster decomposition\n<!-- §35 Protocluster decomposition. -->\nText.\n"
    assert 35 not in msg._self_numbers(card, _PAT)


def test_real_prose_count_still_detected():
    assert 2 in msg._self_numbers("The region has 2 protoclusters.", _PAT)


def test_conflicting_prose_counts_still_both_seen():
    # the INTERNAL_CONTRADICTION gate must still fire on genuinely inconsistent prose
    got = msg._self_numbers("This region has 2 protoclusters. Later it says 4 protoclusters.", _PAT)
    assert {2, 4} <= got


def test_comparator_sentence_still_excluded():
    # a MIBiG/contrastive comparator count must not be read as this region's self-count
    card = "The closest MIBiG hit BGC0001234 has 9 protoclusters. This region has 2 protoclusters."
    got = msg._self_numbers(card, _PAT)
    assert 9 not in got and 2 in got


# ---- negation scope (NOT FOLDED — xfail spec for batch 1) --------------------------------

def _over(s):
    return [x for x in csg.lint_text(s) if "overclaim" in x.lower() or "production" in x.lower()]


def test_real_production_claim_still_flagged():
    # baseline that must hold regardless of the negation work
    assert _over("The strain produces rifamycin.")


@pytest.mark.parametrize("sentence", [
    # a leading negation in an EARLIER clause must not suppress a later independent claim
    "This result is interesting, not proof of novelty; the strain produces rifamycin.",
    "It is not proof of novelty — the strain produces rifamycin.",
    "There is no proof here. The strain produces streptomycin.",
])
def test_adversarial_negation_does_not_suppress_later_claim(sentence):
    assert _over(sentence), f"claim-safety FALSE NEGATIVE — overclaim slipped through: {sentence!r}"


@pytest.mark.parametrize("sentence", [
    # scope-aware negation (batch 1): a disclaimer whose negation governs the production verb is safe
    "This is not proof that the strain produces rifamycin.",
    "We cannot claim that the cluster produces streptomycin.",
    "This does not mean the strain makes rifamycin.",
])
def test_scoped_disclaimer_is_claim_safe(sentence):
    assert not _over(sentence), f"claim-safe disclaimer wrongly flagged: {sentence!r}"
