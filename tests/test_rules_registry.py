"""Tests for the standing-rules registry and the retired-claim linter (W8/W30).

These tests are the guard: if someone deletes a rule from the registry, or the linter
stops catching a retired claim, the build fails here.
"""
import mamey.rules as R


def test_registry_loads_and_is_unique():
    reg = R.load_registry()
    ids = [r.id for r in reg]
    assert len(ids) == len(set(ids)), "duplicate rule ids in registry"
    # the rules we never want to silently lose:
    assert {"NAPAA", "BRYO-HGT-001", "HGLE-KS-PREV-001", "SACCHARIDE"} <= set(ids)


def test_napaa_is_neutral_not_blocking():
    # build -q policy: NAPAA is detected but NEUTRAL (common, adjacent to real BGCs) -> not lead-blocking
    hits = R.lint_text("BGC04 is a strong NAPAA lead for the comparative panel")
    assert any(h.rule_id == "NAPAA" for h in hits)                 # still detected
    assert not any(h.rule_id == "NAPAA" and h.lead_blocking for h in hits)  # but does not block


def test_retired_bryo_is_flagged():
    assert R.has_blocking_hit("we recover BRYO-HGT-001 in the moss strains")


def test_hgle_aliases_all_match():
    # build -q: hglE-KS / PREV-001 / hexacosalactone are still DETECTED, but noted (not lead-blocking)
    for txt in ["hglE-KS cluster", "PREV-001 signal", "hexacosalactone capacity"]:
        hits = R.lint_text(txt)
        assert any(h.rule_id == "HGLE-KS-PREV-001" for h in hits), f"missed alias in: {txt}"
        assert not R.has_blocking_hit(txt), f"hglE should be noted, not blocking: {txt}"


def test_false_positive_guard_polysaccharide():
    # 'polysaccharide' must NOT trip the bare 'saccharide' exclusion
    hits = [h for h in R.lint_text("a lipopolysaccharide biosynthesis region") if h.rule_id == "SACCHARIDE"]
    assert hits == [], "guard failed: polysaccharide wrongly flagged as saccharide"


def test_bare_saccharide_still_flagged():
    assert R.has_blocking_hit("BGC11 saccharide cluster")


def test_enediyne_is_warn_not_block():
    hits = [h for h in R.lint_text("enediyne KCB hit on NODE_42") if h.rule_id == "ENEDIYNE-KCB"]
    assert hits and all(not h.lead_blocking for h in hits), "enediyne should warn (BSL-2 gate), not block"


def test_clean_text_has_no_hits():
    assert R.lint_text("BGC07 shows NRPS biosynthetic capacity on NODE_18") == []
