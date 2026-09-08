"""Guards for the curated compound-family rule table (BLIZZARD_BLUE_01).

The table is ordered and first-match-wins, so curation has two failure classes that are invisible
at review time and silent at runtime:

  1. a NEW key that an EARLIER rule already matches as a substring is DEAD — it never fires, and the
     anchor is silently classified by the earlier rule instead (this is the `SapB` failure class);
  2. a NEW rule inserted ahead of a shipped one would CHANGE a shipped classification.

These tests make both loud. They also lock the one evidence-driven correction in the table so a
future edit cannot quietly flip it back.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from mamey.compound_family_report import classify, load_rules

RULES_PATH = Path(__file__).resolve().parents[1] / "mamey" / "data" / "compound_family_rules.json"
N_SHIPPED_BASE = 38  # the pre-curation table; the curated additions are appended after these

EVIDENCE_TIERS = {
    "in_bundle_title",       # key appears in the TITLE of an in-bundle PubMed record
    "in_bundle_abstract",    # key appears only in the abstract (corpus has a mis-join defect)
    "family_membership",     # no in-bundle record; assigned by membership in a shipped family
    "cohort_guard",          # justified by the engine's own guard output, not by literature
    # The corpus record backing this key is contaminated (it swallowed an adjacent entry's
    # abstract), so the supporting TEXT is real but its PMID attribution is known-wrong. The
    # receipt must carry pmid_unreliable and NO pmid, so nothing can cite it as a source.
    "corpus_text_unattributed",
}


@pytest.fixture(scope="module")
def doc():
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def test_loader_parses_the_curated_table(doc):
    rules = load_rules()
    assert len(rules) == len(doc["rules"])
    for keys, (family, target_class, moa) in rules:
        assert keys and family and target_class and moa


def test_no_key_is_shadowed_by_an_earlier_rule(doc):
    """A key matched as a substring by an earlier rule can never fire — it is dead weight that
    silently misattributes its anchor. Report every one with the rule that swallows it."""
    flat = [(i, k) for i, r in enumerate(doc["rules"]) for k in r["keys"]]
    dead = [
        f"rule {i} key {k!r} is shadowed by rule {j} key {k2!r}"
        for i, k in flat
        for j, k2 in flat
        if j < i and k2.lower() in k.lower()
    ]
    assert not dead, "dead keys (never reachable under first-match-wins):\n  " + "\n  ".join(dead)


def test_curated_additions_are_append_only(doc):
    """Additions go AFTER the shipped rules, so first-match-wins guarantees no shipped
    classification can change. Anything else must be a deliberate, reviewed edit."""
    added = doc["rules"][N_SHIPPED_BASE:]
    assert added, "expected curated rules appended after the shipped base"
    assert all("evidence" in r for r in added), "every curated rule must carry an evidence receipt"


def test_every_curated_rule_has_a_typed_evidence_receipt(doc):
    for i, r in enumerate(doc["rules"][N_SHIPPED_BASE:], start=N_SHIPPED_BASE):
        ev = r.get("evidence")
        assert isinstance(ev, dict), f"rule {i} ({r['family']}) has no evidence receipt"
        assert ev.get("tier") in EVIDENCE_TIERS, f"rule {i} tier {ev.get('tier')!r} not recognised"
        if ev["tier"] == "corpus_text_unattributed":
            assert not ev.get("pmid"), (
                f"rule {i} has a known-wrong attribution and must NOT expose a citable pmid")
            assert ev.get("pmid_unreliable"), f"rule {i} must record which PMID was rejected"
            assert "NOT the correct citation" in ev.get("caution", ""), (
                f"rule {i} must say plainly that the attribution is wrong")
        elif ev["tier"].startswith("in_bundle"):
            assert ev.get("pmid"), f"rule {i} claims in-bundle evidence but cites no PMID"
        else:
            assert ev.get("basis"), f"rule {i} has no in-bundle record and must state its basis"


def test_target_classes_stay_within_the_shipped_enum(doc):
    allowed = set(doc["target_class_order"])
    for r in doc["rules"]:
        assert r["target_class"] in allowed, f"{r['family']} -> {r['target_class']!r} is not in the enum"


def test_housekeeping_tokens_do_not_route_to_an_activity_class():
    for token in ("geosmin", "2-methylisoborneol", "ectoine", "melanin"):
        family, target_class, _ = classify(token)
        assert target_class in {"housekeeping", "other"}, f"{token} -> {target_class}"


def test_pactamide_reports_both_antifungal_and_cytotoxic():
    """Locked correction, in BOTH directions.

    In-bundle PMID 27966343 reports pactamides A-F with potent cytotoxicity against human cancer
    cell lines. The HSAF/PTM family also carries antifungal capacity (HSAF = heat-stable antifungal
    factor). These are not exclusive - most antifungals carry some cytotoxicity - so the anchor
    must report BOTH:

      * a bare 'AF' over-claims, ignoring the reported cytotoxicity of the named congener;
      * a bare 'cytotoxic' silently drops the BGC off every antifungal-facing report, which is a
        loss of information on an Exceptional-tier flagship (AS-677 BGC016).
    """
    family, target_class, _ = classify("pactamide A/pactamide B/pactamide C")
    assert "tetramate macrolactam" in family.lower()
    assert target_class == "AF/cytotoxic", (
        f"pactamide must report both signals, got {target_class!r}")
    assert "AF" in target_class, "must remain visible to antifungal-facing reports"
    assert "cytotoxic" in target_class, "must not hide the reported cytotoxicity"


def test_mis_anchor_watch_rule_cannot_inflate_antifungal_capacity():
    """chainin/isochainin anchors carry the cohort polyene mis-anchor flag (KS=0); the rule exists
    to keep them OUT of AF."""
    for token in ("chainin", "isochainin"):
        _, target_class, _ = classify(token)
        assert target_class != "AF", f"{token} routed to AF — the mis-anchor guard is not holding"


@pytest.mark.parametrize(
    "anchor,expect_class",
    [
        ("cyphomycin", "AF"),
        ("nystatin", "AF"),               # shipped base rule — must be unchanged by curation
        ("vancomycin", "AB"),             # shipped base rule — must be unchanged by curation
        ("nocobactin NA", "siderophore"),
        ("SF2768", "siderophore"),
        ("phosphonoacetic acid", "other"),
    ],
)
def test_spot_check_routing(anchor, expect_class):
    assert classify(anchor)[1] == expect_class


def test_unmapped_anchor_falls_through_explicitly():
    family, target_class, moa = classify("a-compound-that-is-not-in-the-map")
    assert "unmapped" in family.lower()
    assert target_class == "other"
    assert "manual" in moa.lower()
