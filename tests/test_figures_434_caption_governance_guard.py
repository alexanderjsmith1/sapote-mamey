"""FIGURES_434: a rendered figure caption must not carry operator-governance prose.

Captions observed live 2026-09-18 ended with "Screening signal is class-level; no compound,
structure, or potency claim is implied. Judgment deferred to Alex." That is written for the
operator. In a publication figure it reads as hedging and names the operator inside the caption.
"""
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from caption_guard import BLOCKED, CaptionGovernanceError, check_caption, scan_paths  # noqa: E402

REAL_OFFENDER = (
    "ACTIVITY STRIPS. Four states, never coerced: '+' active (best recorded inhibition >=80%). "
    "Screening signal is class-level; no compound, structure, or potency claim is implied. "
    "Judgment deferred to Alex."
)

CLEAN = (
    "Maximum-likelihood 16S rRNA gene phylogeny of 51 owner isolates and 129 type strains. "
    "IQ-TREE, model GTR+F+I+R5, 1000 ultrafast bootstrap replicates; node labels show support >=70. "
    "Isolation source and geography are reported as deposited; tips with no deposited value are "
    "left blank. '+' marks >=80% inhibition, '-' tested and inactive, 'n.t.' not tested."
)


def test_real_offending_caption_is_refused():
    with pytest.raises(CaptionGovernanceError, match="CAPTION_GOVERNANCE_PROSE"):
        check_caption(REAL_OFFENDER)


def test_publication_caption_passes():
    assert check_caption(CLEAN) == []


def test_every_blocked_phrase_is_detected():
    for phrase in BLOCKED:
        assert check_caption(f"Methods sentence. {phrase} trailing.", raises=False), phrase


def test_detection_survives_wrapping_and_case():
    wrapped = "Screening signal is\n  CLASS-Level; judgment\n\tdeferred to the owner."
    hits = check_caption(wrapped, raises=False)
    assert {p for p, _ in hits} >= {"class-level", "judgment deferred"}


def test_threshold_language_is_not_a_false_positive():
    """'>=80% inhibition' is a real method statement and must not trip the guard."""
    assert check_caption("Calls use a >=80% inhibition threshold at a generic 48 h.") == []


def test_findings_carry_a_reason():
    for _, why in check_caption(REAL_OFFENDER, raises=False):
        assert why and isinstance(why, str)


def test_scan_paths_reports_only_offenders(tmp_path):
    bad = tmp_path / "caption_bad.txt"; bad.write_text(REAL_OFFENDER)
    good = tmp_path / "caption_good.txt"; good.write_text(CLEAN)
    result = scan_paths([bad, good])
    assert str(bad) in result and str(good) not in result
