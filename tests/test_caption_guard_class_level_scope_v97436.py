"""BLIZZARD_BLUE_436: 'class-level' as a caption phrase must distinguish governance hedging
("screening signal is class-level;") from legitimate scientific vocabulary ("class-level
composition of biosynthetic gene clusters"). The flat substring match in BLOCKED could not
tell them apart; reported by Goldenrod (.436), fixed here as a standalone regex check.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from caption_guard import check_caption  # noqa: E402


def test_class_level_as_noun_modifier_is_not_blocked():
    """Goldenrod's three reported false positives must pass clean."""
    for caption in [
        "Class-level composition of biosynthetic gene clusters across 44 isolates.",
        "Class-level phylogenetic placement of 89 public strains.",
        "BGC class-level comparison between cohorts.",
    ]:
        assert check_caption(caption, raises=False) == [], caption


def test_class_level_as_standalone_predicate_is_still_blocked():
    """The original historical offender ('signal is class-level;') must still be caught."""
    hits = check_caption(
        "Screening signal is class-level; no compound, structure, or potency claim is implied.",
        raises=False,
    )
    assert any(p == "class-level" for p, _ in hits)


def test_class_level_followed_by_period_or_comma_is_blocked():
    for caption in ["Class-level.", "The result is class-level, not compound-level."]:
        hits = check_caption(caption, raises=False)
        assert any(p == "class-level" for p, _ in hits), caption


def test_class_level_scope_does_not_regress_wrapping_test():
    """Same fixture as test_detection_survives_wrapping_and_case (.434) — must still pass."""
    wrapped = "Screening signal is\n  CLASS-Level; judgment\n\tdeferred to the owner."
    hits = check_caption(wrapped, raises=False)
    assert {p for p, _ in hits} >= {"class-level", "judgment deferred"}
