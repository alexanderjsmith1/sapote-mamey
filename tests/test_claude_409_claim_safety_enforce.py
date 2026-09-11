"""CLAUDE_409 — claim-safety CORE lint enforcement (F1/F2/F3).

Fail-before / pass-after battery for the three fixes in this lane:

  F1  claim_safety_gate: clause-local safe-context (a nearby "similarity"/"-like" in a DIFFERENT
      clause no longer launders an overclaim); bare `similarity`/`-like` dropped from the whitelist.
  F2  claim_safety_gate + modeb_structure_gate: production-verb list widened (secrete/assemble/
      elaborate/generate/afford/manufacture/encode + British -ise/-yse), plus a guarded copula-
      identity path ("the mature product is venezuelin", "BGC027 is venezuelin").
  F3  authored_verify.verify_modeb_command: on a card that declares the FINISHED / publication
      profile, CLAIM_SAFETY / KCB_IDENTITY_RISK WARN is promoted to a blocking ERROR, so
      verify-modeb REFUSES (rc 1) an overclaiming finished deliverable. Draft cards keep WARN.

BEFORE this lane (sealed .408) every assertion marked "was PASS/LEAK" holds the opposite; the
docstrings on each test say which. Part A runs on any Python; Parts B/C import the full engine and
need the bundle's target interpreter (Python 3.12 — the sealed tree uses 3.12-only f-string syntax
that does not byte-compile on 3.9).

Run:  pytest tests/TESTS_CLAUDE_409_claim_safety_enforce.py -q
"""
import sys
import types
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(_ROOT / "tools"))


# =========================================================================================
# Part A — mamey/claim_safety_gate.py :: lint_text   (F1 + F2; pure, runs anywhere)
# =========================================================================================
from mamey.claim_safety_gate import lint_text


def _flagged(s: str) -> bool:
    return len(lint_text(s)) > 0


# ---- F1: the ±80-char safe-context bypass is closed --------------------------------------
@pytest.mark.parametrize("text", [
    # was LEAK on .408: a "similarity" in the *next* clause silenced the claim.
    "BGC027 produces venezuelin; similarity is discussed below.",
    # was LEAK on .408: a trailing "-like" comma-clause silenced the claim.
    "The strain produces streptomycin, a lanthipeptide-like agent.",
])
def test_F1_adjacent_safeword_no_longer_launders_overclaim(text):
    assert _flagged(text), f"F1 regression — overclaim laundered by a distant safe word: {text!r}"


# ---- F2: verb allow-list widened + copula identity --------------------------------------
@pytest.mark.parametrize("text", [
    "The cluster secretes venezuelin.",        # was LEAK
    "The cluster assembles streptomycin.",     # was LEAK
    "The cluster elaborates streptocollin.",   # was LEAK
    "BGC027 encodes venezuelin.",              # was LEAK
    "BGC027 synthesises venezuelin.",          # British -ise, was LEAK in the structure gate
    "The mature product is venezuelin.",       # copula, was LEAK
    "BGC027 is venezuelin.",                   # copula, was LEAK
    "BGC027 produces venezuelin.",             # baseline (already caught on .408) — must stay caught
])
def test_F2_new_verbs_and_copula_are_caught(text):
    assert _flagged(text), f"F2 regression — production/identity overclaim leaked: {text!r}"


# ---- Regression: legitimately hedged / descriptive prose must stay CLEAN -----------------
@pytest.mark.parametrize("text", [
    # test_claim_safety_ci_gate pinned cases (must remain PASS):
    "BGC001 encodes biosynthetic capacity consistent with a desertomycin-like comparator_context.",
    "BGC001 encodes biosynthetic capacity consistent with a desertomycin-like pathway. "
    "KCB is similarity, not identity.",
    # test_claim_safety_gate_filler_word_overclaim pinned CLEAN cases:
    "This BGC produces a polyketide backbone.",
    "This BGC produces the compound.",
    "capacity consistent with the compound streptomycin",
    "No evidence that this BGC produces the antibiotic streptomycin.",
    "This does not support that the BGC produces the metabolite erythromycin.",
    # test_wac01375 scope-aware disclaimer CLEAN cases:
    "This is not proof that the strain produces rifamycin.",
    "We cannot claim that the cluster produces streptomycin.",
    "This does not mean the strain makes rifamycin.",
    # copula false-positive guards (descriptive/class copulas):
    "The cluster is complete.",
    "The product is predicted to be a class-III lanthipeptide.",
    "KCB is similarity, not identity.",
    # anchor class-level qualifier stays clean:
    "anchor -> tetrachlorizine family (2/17 genes)",
])
def test_regression_hedged_and_descriptive_stay_clean(text):
    assert not _flagged(text), f"false positive on claim-safe text: {text!r}"


@pytest.mark.parametrize("text", [
    # test_wac01375 adversarial: a leading negation in an EARLIER clause must NOT suppress a
    # later independent production claim.
    "This result is interesting, not proof of novelty; the strain produces rifamycin.",
    "There is no proof here. The strain produces streptomycin.",
])
def test_regression_earlier_negation_does_not_mask_later_claim(text):
    assert _flagged(text), f"claim-safety FALSE NEGATIVE — overclaim slipped through: {text!r}"


# =========================================================================================
# Part B — mamey/modeb_structure_gate.py :: _claim_safety_findings  (F2 at authoring time)
# =========================================================================================
def _msg():
    return pytest.importorskip(
        "mamey.modeb_structure_gate",
        reason="full engine import (needs the bundle's Python 3.12 target interpreter)")


def _cs_codes(card):
    g = _msg()
    return {f.get("code") for f in g._claim_safety_findings(card)}


@pytest.mark.parametrize("card", [
    "The mature product is venezuelin.\n",   # copula — was LEAK in the structure gate
    "The compound is venezuelin.\n",         # copula — was LEAK
    "This BGC synthesises venezuelin.\n",     # British -ise — was LEAK in the structure gate
    "The cluster secretes venezuelin.\n",     # widened verb — was LEAK
])
def test_F2_structure_gate_catches_copula_and_new_verbs(card):
    assert "CLAIM_SAFETY" in _cs_codes(card), f"structure gate missed: {card!r}"


@pytest.mark.parametrize("card", [
    # test_cut_209 pinned CLEAN (negated / conditional / capacity):
    "Cannot claim BGC039 (NODE_9 · r001) produces SapB or any named compound.",
    "If this BGC produces an active compound, an antibacterial role is plausible.",
    "Biosynthetic capacity consistent with a class-III lanthipeptide.",
    # copula false-positive guards:
    "The cluster is complete.\n",
    "The region is a lanthipeptide.\n",
    "The cluster architecture is complete:\n",
    "The scaffold is intact.\n",
    # test_claim_safety_multiline_denial_v97257 denial list (governed list item):
    "The evidence does not support:\n(1) that BGC019 produces frankiamicin\n",
])
def test_regression_structure_gate_clean(card):
    assert "CLAIM_SAFETY" not in _cs_codes(card), f"false positive: {card!r}"


@pytest.mark.parametrize("card", [
    "§8 Assessment\nBGC019 produces frankiamicin.\n",                        # cut_209 / 257 real claim
    "The strain produces daptomycin and synthesizes a polyketide.",          # cut_209 flags produces
    "The cluster architecture is complete:\n(1) BGC019 produces frankiamicin\n",  # list, no denial intro
])
def test_regression_structure_gate_real_claim_still_fires(card):
    assert "CLAIM_SAFETY" in _cs_codes(card), f"real claim not flagged: {card!r}"


# =========================================================================================
# Part C — authored_verify.verify_modeb_command  (F3: finished-profile BLOCK)
# =========================================================================================
def _av():
    return pytest.importorskip(
        "mamey.authored_verify",
        reason="full engine import (needs the bundle's Python 3.12 target interpreter)")


def _run_verify(monkeypatch, tmp_path, *, finished: bool):
    """Drive verify_modeb_command with lint_card stubbed to a single CLAIM_SAFETY WARN, so the
    test isolates the F3 promotion (structure/depth are not the variable under test)."""
    av = _av()
    card = "# Card\n" + ("FINISHED_FULL48_CURRENT_EVIDENCE\n" if finished else "DRAFT\n") \
        + "The mature product is venezuelin.\n"
    f = tmp_path / "card.md"
    f.write_text(card, encoding="utf-8")

    monkeypatch.setattr(av, "lint_card", lambda *a, **k: [
        {"severity": "WARN", "code": "CLAIM_SAFETY", "section": 8,
         "message": "'the mature product is venezuelin' is product-identity language."}
    ])
    # No package context, no §4 coverage gap — keep everything but the claim finding neutral.
    monkeypatch.setattr(av, "_bgc_context_from_package", lambda *a, **k: None)
    monkeypatch.setattr(av, "_coverage_unverified_reason", lambda *a, **k: None)

    args = types.SimpleNamespace(
        file=str(f), package=None, bgc=None, no_strict_depth=False,
        interp=False, interp_strict=False, report_json=None, summary_only=False)
    return av.verify_modeb_command(args)


def test_F3_finished_profile_overclaim_is_blocked(monkeypatch, tmp_path):
    # was PASS (rc 0) on .408 — CLAIM_SAFETY is WARN and verify-modeb failed only on ERROR.
    rc = _run_verify(monkeypatch, tmp_path, finished=True)
    assert rc == 1, "F3: an overclaiming FINISHED-profile card must FAIL verify-modeb (rc 1)"


def test_F3_draft_profile_overclaim_stays_warn(monkeypatch, tmp_path):
    # Draft cards keep the pre-.409 advisory behaviour: WARN, still rc 0. Scope is finished-only.
    rc = _run_verify(monkeypatch, tmp_path, finished=False)
    assert rc == 0, "F3: a DRAFT card must keep WARN behaviour (rc 0), not be newly blocked"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
