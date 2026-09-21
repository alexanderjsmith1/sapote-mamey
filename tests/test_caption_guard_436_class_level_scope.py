"""caption_guard: "class-level" must separate the governance use from the scientific one.

Both directions are pinned here because fixing one without the other has already happened
once: a proposed fix that replaced the bare phrase with "class-level hypotheses only" removed
the false positive but let "Screening signal is class-level" -- the caption actually observed
live on 2026-09-18 -- pass clean.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from caption_guard import check_caption  # noqa: E402

# Predicative: the phrase states the ceiling of the claim. Governance prose.
GOVERNANCE = [
    "Figure 4. Screening signal is class-level.",
    "Figure 5. Activity shown is class-level only.",
    "Screening signal is class-level; no compound, structure, or potency claim is implied.",
    "Results are class-level hypotheses only.",
    "Observations are class-level hypothesis statements.",
    # Missed by the standalone-predicate regex alone (a lowercase word follows):
    "Exact locus bound to node and region; class-level read only.",
    # Missed by the predicative-substring keys alone (no "is"/"are" adjacency):
    "Activity is reported class-level.",
]

# Attributive: "class-level <noun>" describes what was measured. Legitimate caption text,
# and the cohort BGC-class figures are expected deliverables.
SCIENTIFIC = [
    "Figure 3. Class-level distribution of BGCs across 44 actinomycete isolates.",
    "Class-level phylogenetic placement of 89 public strains.",
    "BGC class-level comparison between cohorts.",
    "Class-level breakdown by genus.",
]


def test_predicative_class_level_is_refused():
    for caption in GOVERNANCE:
        assert check_caption(caption, raises=False), f"governance prose passed: {caption!r}"


def test_attributive_class_level_is_allowed():
    for caption in SCIENTIFIC:
        hits = check_caption(caption, raises=False)
        assert hits == [], f"false positive on legitimate caption: {caption!r} -> {hits}"


def test_bare_phrase_is_not_a_key():
    """Guards against a well-meaning revert to the broad substring."""
    from caption_guard import BLOCKED

    assert "class-level" not in BLOCKED, (
        "the bare phrase blocks legitimate attributive captions; use the predicative keys"
    )
