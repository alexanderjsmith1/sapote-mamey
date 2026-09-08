"""v9.7.410 hostile audit H23 — accent / leetspeak evasion of the BIOACTIVITY-phenotype check.

The verb lane (CLAUDE_v9.7.410_claimsafety_verb_normalize) repaired `prodúces`, `pr0duces`; the
bioactivity delegate never received that repair, so `actíve against S. aureus` dropped every
phenotype finding while reading perfectly plausibly. Battery mirrors the verb lane's: each
keyword class, each evasion form, plus controls proving organism/compound names are never folded.
"""
from __future__ import annotations

import pytest

from mamey.claim_safety_gate import lint_text, _normalize_for_detection

PLAIN = "BGC001 is active against S. aureus and inhibits growth; MIC 2 µg/mL was measured for the strain."


def _pheno(text: str) -> int:
    return sum(1 for f in lint_text(text) if "bioactivity-phenotype" in f)


def test_plain_sentence_is_caught():
    assert _pheno(PLAIN) >= 1


@pytest.mark.parametrize("evasion", [
    PLAIN.replace("active", "actíve"),          # precomposed accent (the reproduced case)
    PLAIN.replace("active", "actíve"),         # decomposed accent (i + U+0301)
    PLAIN.replace("against", "agaínst"),
    PLAIN.replace("inhibits", "inhíbits"),
    PLAIN.replace("inhibits", "inh1bits"),      # leetspeak
    PLAIN.replace("active", "act1ve"),
    PLAIN.replace("MIC", "MÍC"),
    PLAIN.replace("is active", "ís actíve"),    # frame word AND keyword accented
])
def test_accented_or_leet_bioactivity_keywords_are_still_caught(evasion):
    assert evasion != PLAIN
    assert _pheno(evasion) >= 1, evasion


@pytest.mark.parametrize("adj", ["antibacterial", "antifungal", "cytotoxic", "bactericidal", "bioactive"])
def test_asserted_adjectives_survive_an_accent(adj):
    folded = adj[:2] + "́" + adj[2:]       # combining acute after the 2nd letter
    text = f"BGC007 is potently {folded} and shows strong {adj} activity in the assay."
    assert _pheno(text) >= 1, text


def test_organism_and_compound_names_are_never_folded():
    """Only the matcher vocabulary folds; an accented organism or compound name is left as written,
    so the emitted finding still quotes the author's text."""
    norm, _ = _normalize_for_detection("Bacíllus subtílis and érythromycin", fold_wrappers=False)
    assert norm == "Bacíllus subtílis and érythromycin"


def test_fold_preserves_offset_map_length_invariant():
    text = "is actíve against Stréptococcus"
    norm, idx = _normalize_for_detection(text, fold_wrappers=False)
    assert len(norm) == len(idx)
    assert "active" in norm and "Stréptococcus" in norm
