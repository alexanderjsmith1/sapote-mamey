"""CLAUDE_410 claimsafety_linter_normalize — the tools/ linter must fold obfuscation the same way
the gate does, because the SEAL runs the tools/ linter, not the gate.

`.409` landed `_normalize_for_detection` in `mamey/claim_safety_gate.py`, so `lint_text` catches an
overclaim written as `produces **venezuelin**`, with a Cyrillic `о`, with a zero-width space inside
the verb, or in fullwidth characters. The two entry points in `tools/claim_safety_linter.py` never
got it — and `mamey/seal_package.py::_gate_claim_safety` calls `lint_claim_safety`, so on pristine
`.409` every one of those obfuscations passes the seal's claim-safety gate while the gate's own
`lint_text` catches the identical sentence.

This lane routes both tools/ entry points through the gate's own normalizer (one shared surface, no
third copy) in its `fold_wrappers=False` mode — de-obfuscation only, punctuation untouched — plus a
narrow emphasis/quote strip. The gate's own docstring records why the full fold is wrong here: this
module "carries its own calibrated hedge / sentence-boundary logic, and rewriting its
brackets/emphasis would corrupt that segmentation". Confirmed on two shipped documents, see
test_segmentation_is_preserved_for_the_hedge_window below.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

# Imported at module level: both exist in .409, so every behavioural test below FAILS (rather than
# erroring at collection) on the pristine tree, which is what makes the fail-before meaningful.
# `normalize_for_claim_detection` is new in this lane and is imported lazily where it is used.
from claim_safety_linter import (  # noqa: E402
    lint_claim_safety,
    lint_claim_safety_report,
)

COMPOUND = {"venezuelin"}

# Each is the SAME claim as the plain form; only the encoding of the verb or the compound differs.
OBFUSCATED_OVERCLAIMS = {
    "plain": "Strain RB68 produces venezuelin.",
    "markdown_emphasis": "Strain RB68 produces **venezuelin**.",
    "cyrillic_lookalike": "Strain RB68 prоduces venezuelin.",
    "zero_width_in_verb": "Strain RB68 pro​duces venezuelin.",
    "fullwidth": "Strain RB68 ｐroduces venezuelin.",
    "quoted_compound": 'Strain RB68 produces "venezuelin".',
}

# Legitimate, claim-safe prose. None of these may become a finding — a normalizer that invents
# findings is worse than one that misses them, because the owner learns to ignore the linter.
MUST_STAY_CLEAN = [
    "The cluster has the capacity to produce a venezuelin-like compound.",
    "There is no evidence that RB68 produces venezuelin.",
    "This does not support that the strain produces venezuelin.",
    "Similarity to the venezuelin BGC does not establish identity.",
    "Pre-authoring channel reconciliation is `tools/bgc_reconcile.py`; run it first.",
    "The entry point is `mamey/cli.py` and the gate is `mamey/claim_safety_gate.py`.",
]


@pytest.mark.parametrize("name", sorted(OBFUSCATED_OVERCLAIMS))
def test_lint_claim_safety_catches_obfuscated_overclaim(name: str) -> None:
    """Fails on pristine .409 for every case except `plain`."""
    assert lint_claim_safety(OBFUSCATED_OVERCLAIMS[name], COMPOUND), name


@pytest.mark.parametrize("name", sorted(OBFUSCATED_OVERCLAIMS))
def test_lint_claim_safety_report_catches_obfuscated_overclaim(name: str) -> None:
    """The CSV-report surface must agree with the plain-findings surface."""
    assert lint_claim_safety_report(
        OBFUSCATED_OVERCLAIMS[name], compound_names=COMPOUND
    ), name


@pytest.mark.parametrize("text", MUST_STAY_CLEAN)
def test_no_false_positives_introduced(text: str) -> None:
    assert lint_claim_safety(text, COMPOUND) == [], text
    assert lint_claim_safety_report(text, compound_names=COMPOUND) == [], text


def test_seal_gate_and_authoring_gate_agree_on_every_case() -> None:
    """The divergence this lane closes: the seal path (tools/ linter) and the authoring path
    (mamey/claim_safety_gate.lint_text) must not disagree about whether a sentence is an overclaim.
    On pristine .409 the gate catches all six and the linter catches one."""
    from mamey.claim_safety_gate import lint_text

    for name, text in OBFUSCATED_OVERCLAIMS.items():
        gate = bool(lint_text(text))
        seal = bool(lint_claim_safety(text, COMPOUND))
        assert gate == seal is True, f"{name}: gate={gate} seal_linter={seal}"


def test_seal_gate_actually_calls_the_normalized_linter() -> None:
    """Guards the wiring, not just the function: if _gate_claim_safety is ever repointed at an
    unnormalized copy, the cases above would keep passing while the seal went blind again."""
    src = (ROOT / "mamey" / "seal_package.py").read_text(encoding="utf-8")
    assert "from claim_safety_linter import lint_claim_safety" in src


def test_segmentation_is_preserved_for_the_hedge_window() -> None:
    """The regression that forced fold_wrappers=False.

    With the full fold, `)` becomes a newline. That truncates the sentence this module scopes its
    hedge/rejection check over (`_sentence_around` breaks on newlines), so a sentence whose
    "similarity" hedge sits before the parenthetical loses it and fires falsely. Two shipped
    documents hit it: the rendered citation-audit report, and docs/reference/modeb_exemplars/
    nrps_exemplar.md — whose §8 sentence says the region does **not** make tetronasin.

    A file path in backticks must likewise never be read as a compound name.
    """
    from claim_safety_linter import normalize_for_claim_detection

    normalized = normalize_for_claim_detection("reconciliation is `tools/bgc_reconcile.py`; ok")
    assert "is  tools" not in normalized
    # Brackets and periods survive normalization, so the sentence stays one sentence.
    # The real §8 sentence from docs/reference/modeb_exemplars/nrps_exemplar.md. Its hedge token is
    # "comparator" (_IDENTITY_FRAME_RX), which sits BEFORE the parenthetical — so folding `)` to a
    # newline cuts the hedge out of the sentence and the trailing "makes tetronasin" fires.
    hedged = ("This is a **comparator/product divergence**: the KCB score reflects shared "
              "backbone-fragment similarity (KCB compares cluster gene content, and polyether and "
              "NRPS clusters can share tailoring/transport genes), **not** that this region makes "
              "tetronasin.")
    norm = normalize_for_claim_detection(hedged)
    assert "(" in norm and ")" in norm, "brackets must not be folded — they carry segmentation here"
    assert "comparator" in norm.split("makes tetronasin")[0], "the hedge must stay in the sentence"
    # Assert on the identity finding specifically: this fragment is one sentence lifted out of the
    # card, so the document-scoped "KCB mentioned without identity-ceiling language" rule fires on it
    # regardless — that rule is satisfied elsewhere in the real file, checked below.
    found = lint_claim_safety(hedged, {"tetronasin"})
    assert not any("tetronasin" in f for f in found), found

    # And the whole shipped exemplar, which is what the .409 suite guards.
    exemplar = (ROOT / "docs" / "reference" / "modeb_exemplars" / "nrps_exemplar.md")
    if exemplar.is_file():
        found = lint_claim_safety(exemplar.read_text(encoding="utf-8"), {"tetronasin"})
        assert not any("tetronasin" in f for f in found), found
    # A real claim next to a code span is still caught.
    assert lint_claim_safety(
        "See `tools/x.py`. Strain RB68 produces venezuelin.", COMPOUND
    )


def test_normalizer_degrades_to_raw_text_without_mamey(monkeypatch) -> None:
    """Bare `python tools/claim_safety_linter.py` outside the bundle must keep working: if the gate
    is unimportable the linter behaves exactly as .409 did, never worse and never crashing."""
    import builtins

    real_import = builtins.__import__

    def _blocked(name, *args, **kwargs):
        if name.startswith("mamey"):
            raise ImportError("simulated: mamey not importable")
        return real_import(name, *args, **kwargs)

    from claim_safety_linter import normalize_for_claim_detection

    monkeypatch.setattr(builtins, "__import__", _blocked)
    text = "Strain RB68 produces venezuelin."
    assert normalize_for_claim_detection(text) == text
