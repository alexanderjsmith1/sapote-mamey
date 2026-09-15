"""v9.7.430 — `gut` must not make an insect source clinical, and must still classify animal guts.

`tools/_phylo_metadata.py` listed bare `gut` in the `clinical/animal-associated` alternation, which
precedes `insect-associated` in `_CATEGORY_RULES`. Any isolation source containing "gut" therefore
classified as clinical regardless of host — so "termite gut", "bee gut", "ant gut" and "insect gut"
were coloured and labelled clinical on the tree reference series, for a cohort that is
insect-associated.

THIS FILE DELIBERATELY GUARDS THREE FAILURE MODES, NOT ONE. Two obvious repairs each fix the
reported bug and introduce a different one; both were measured against this probe set before the
landed fix was chosen:

  * delete bare "gut" from the clinical rule  -> "mouse gut", "rat gut", "chicken gut", "fish gut",
    "porcine gut", "murine gut contents", "gut", "gut microbiome" match NO rule at all (8 sources
    lose their category entirely). Guarded by test_non_insect_animal_gut_stays_clinical.
  * move "insect-associated" above the clinical rule -> genuinely clinical sources that merely
    mention an insect are stolen ("blood of a patient with insect bite", "clinical specimen, insect
    vector", "infected bee" -> insect-associated; 6 sources change).
    Guarded by test_clinical_wins_when_an_insect_word_is_incidental.

A future change that swaps one hole for another therefore breaks this file rather than passing it.
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _module():
    spec = importlib.util.spec_from_file_location(
        "_phylo_metadata_under_test", ROOT / "tools" / "_phylo_metadata.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["_phylo_metadata_under_test"] = module
    spec.loader.exec_module(module)
    return module


def _category(text: str) -> str:
    """First matching rule, the same walk normalize_isolation_source performs."""
    for category, pattern in _module()._CATEGORY_RULES:
        if re.search(pattern, (text or "").lower()):
            return category
    return ""


# ── the reported defect ──────────────────────────────────────────────────────
@pytest.mark.parametrize("source", [
    "termite gut", "bee gut", "ant gut", "insect gut", "gut of a termite", "arthropod gut",
])
def test_insect_gut_is_insect_not_clinical(source):
    assert _category(source) == "insect-associated", (
        f"{source!r} classified as {_category(source)!r} — bare 'gut' is outranking the insect rule "
        "again")


# ── failure mode of the 'just delete gut' repair ─────────────────────────────
@pytest.mark.parametrize("source", [
    "mouse gut", "rat gut", "chicken gut", "fish gut", "porcine gut", "murine gut contents",
    "gut", "gut microbiome",
])
def test_non_insect_animal_gut_stays_clinical(source):
    assert _category(source) == "clinical/animal-associated", (
        f"{source!r} classified as {_category(source)!r} — deleting 'gut' outright drops non-insect "
        "animal guts out of every rule; the term must be re-scoped below the insect rule, not removed")


# ── failure mode of the 'reorder the insect rule' repair ─────────────────────
@pytest.mark.parametrize("source", [
    "blood of a patient with insect bite", "clinical specimen, insect vector",
    "human tissue, insect house", "infected bee", "patient bitten by an ant",
    "insect cell culture, infected",
])
def test_clinical_wins_when_an_insect_word_is_incidental(source):
    assert _category(source) == "clinical/animal-associated", (
        f"{source!r} classified as {_category(source)!r} — an explicit clinical term must still "
        "outrank an incidental insect mention; do not hoist the whole insect rule above clinical")


# ── the curated bee/wasp distinctions must still outrank everything ──────────
@pytest.mark.parametrize("source,expected", [
    ("wasp gut", "wasp"), ("Bombus gut", "bumblebee"), ("honeybee gut", "honeybee"),
    ("attine ant gut", "attine ant"), ("Apis mellifera gut", "honeybee"),
    ("solitary bee gut", "solitary bee"),
])
def test_curated_host_rules_still_precede_gut(source, expected):
    assert _category(source) == expected


# ── explicit clinical/animal terms are untouched ─────────────────────────────
@pytest.mark.parametrize("source", [
    "human gut", "animal gut", "bovine gut", "clinical isolate", "patient blood", "infected tissue",
    "liver", "pus", "faeces",
])
def test_explicit_clinical_terms_unchanged(source):
    assert _category(source) == "clinical/animal-associated"


# ── environmental categories are untouched ───────────────────────────────────
@pytest.mark.parametrize("source,expected", [
    ("soil", "soil/rock/sediment"), ("rhizosphere", "plant-associated"),
    ("moss", "bryophyte/lichen-associated"), ("seawater", "aquatic"),
    ("activated sludge", "built environment"), ("fungal garden", "fungal-associated"),
])
def test_environmental_rules_unchanged(source, expected):
    assert _category(source) == expected


# ── the ordering invariant itself, asserted rather than left to the comment ──
def test_gut_rule_sits_below_the_insect_rule():
    """The fix is positional. If someone re-sorts _CATEGORY_RULES this is the tripwire."""
    categories = [c for c, _ in _module()._CATEGORY_RULES]
    patterns = [p for _, p in _module()._CATEGORY_RULES]
    insect = categories.index("insect-associated")
    gut_rule = next(i for i, p in enumerate(patterns) if p == r"\bgut\b")
    assert gut_rule > insect, "the bare-gut rule must stay BELOW insect-associated"
    clinical = categories.index("clinical/animal-associated")
    assert clinical < insect, "the explicit clinical rule must stay ABOVE insect-associated"
    assert "|gut|" not in patterns[clinical], "bare 'gut' must not be back in the clinical alternation"


def test_normalize_isolation_source_agrees_with_the_rule_walk():
    """The public entry point, not just the private table — the thing figures actually call."""
    m = _module()
    assert m.normalize_isolation_source("termite gut")["display_category"] == "insect-associated"
    assert m.normalize_isolation_source("mouse gut")["display_category"] == "clinical/animal-associated"
    assert m.normalize_isolation_source("human gut")["display_category"] == "clinical/animal-associated"
