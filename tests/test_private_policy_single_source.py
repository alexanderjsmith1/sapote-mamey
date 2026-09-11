"""v9.7.237: the private-strain rule has ONE source of truth (cohort_figures.is_private). Hand-copied
regex/string re-implementations went stale after the 2026-07-06 PI decision (AS cohort public) — that
staleness was the P01 live bug (intake refused PUBLIC for AS-815). Pin both the rule and its prose."""
import pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def test_canonical_rule():
    from mamey.cohort_figures import is_private
    assert is_private("AS-815") is False and is_private("AS-705") is False   # public per PI decision
    assert is_private("AJS-9") is True and is_private("PENDING-1") is True

def test_release_tier_agrees_with_figure_tier():
    from mamey.dedup_and_guard import derive_release
    from mamey.cohort_figures import is_private
    for sid in ("AS-705", "AS-815", "AJS-9", "PENDING-1"):
        assert (derive_release(sid) == "PRIVATE") == is_private(sid), f"tiers disagree on {sid}"

def test_intake_harness_imports_the_rule_rather_than_copying_it():
    src = (ROOT / "tools" / "intake_harness.py").read_text(encoding="utf-8")
    assert "is_private" in src, "intake_harness must import the canonical predicate"

def test_no_prose_still_calls_AS_private():
    """The three stale help/docstring/legend strings that told readers AS- is private."""
    for rel in ("mamey/cli.py", "mamey/cohort_figures.py"):
        src = (ROOT / rel).read_text(encoding="utf-8")
        assert "PRIVATE (AS-/AJS-" not in src, f"stale AS-is-private prose in {rel}"
