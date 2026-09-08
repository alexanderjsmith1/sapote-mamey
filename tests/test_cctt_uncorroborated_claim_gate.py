"""N-05 phase 2: an uncorroborated class-defining CCTT trigger must not raise the class-capacity claim.

Phase 1 flags a class-defining trigger that fired on a class-incompatible BGC (T43-BLA on terpene, T43-PHO on
T3PKS). Phase 2 wires that flag into the scorer: a flagged trigger no longer grants the AB/AF diagnostic bonus,
no longer floors the tier (Inventory→Medium), and no longer exempts the primary-metab guard. It is still
recorded (evidence-conserving) and surfaced for judgment review.
"""
import os, sys
from types import SimpleNamespace as NS
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mamey.scoring import triage_bgcs


def _bgc(bid, products, edge="Full-contig"):
    return NS(bgc_id=bid, products=list(products), mibig_hits=[], kcb_top="Streptomyces sp.",
              kcb_cumulative=None, riq_score=None, edge_status=edge, architecture_confidence="E")


def _scans(per_bgc, uncorrob=None):
    return NS(cctt={"per_bgc": per_bgc, "context_uncorroborated_by_bgc": uncorrob or {}},
              resistance_tiers={"per_bgc": {}})


def _rec(records, bid):
    return next(r for r in records if r.bgc_id == bid)


def test_corroborated_trigger_still_grants_ab_bonus():
    bgc = [_bgc("BGC001", ["NRPS"])]
    with_t = _rec(triage_bgcs(bgc, None, _scans({"BGC001": ["T43-BLA_betalactam"]})), "BGC001").ab_score
    without = _rec(triage_bgcs(bgc, None, _scans({})), "BGC001").ab_score
    assert with_t > without   # not flagged -> bonus applies (unchanged behavior)


def test_uncorroborated_trigger_grants_no_ab_bonus():
    bgc = [_bgc("BGC002", ["terpene"])]
    flagged = _scans({"BGC002": ["T43-BLA_betalactam"]}, {"BGC002": ["T43-BLA_betalactam"]})
    with_uncorr = _rec(triage_bgcs(bgc, None, flagged), "BGC002").ab_score
    without = _rec(triage_bgcs(bgc, None, _scans({})), "BGC002").ab_score
    assert with_uncorr == without   # flagged uncorroborated -> NO bonus


def test_uncorroborated_trigger_does_not_floor_tier():
    # T43-DKP floors (class-defining) but grants no AB/AF bonus, so the floor is isolated from the score.
    bgc = [_bgc("BGC010", ["terpene"])]
    corrob = _rec(triage_bgcs(bgc, None, _scans({"BGC010": ["T43-DKP_cdps"]})), "BGC010").lead_tier
    uncorr = _rec(triage_bgcs(bgc, None, _scans({"BGC010": ["T43-DKP_cdps"]},
                                                {"BGC010": ["T43-DKP_cdps"]})), "BGC010").lead_tier
    assert corrob == "Medium"      # corroborated class diagnostic floors Inventory->Medium
    assert uncorr == "Inventory"   # uncorroborated trigger does not floor


def test_uncorroborated_note_surfaced_in_rationale():
    bgc = [_bgc("BGC002", ["terpene"])]
    flagged = _scans({"BGC002": ["T43-BLA_betalactam"]}, {"BGC002": ["T43-BLA_betalactam"]})
    note = _rec(triage_bgcs(bgc, None, flagged), "BGC002").rationale
    assert "CCTT-UNCORROBORATED" in note and "T43-BLA_betalactam" in note


def test_promiscuous_trigger_unaffected():
    # a halogenase is never flagged uncorroborated; it must keep its (non-flooring) recording behavior
    bgc = [_bgc("BGC020", ["terpene"])]
    r = _rec(triage_bgcs(bgc, None, _scans({"BGC020": ["T43-HAL_halogenase"]})), "BGC020")
    assert r.bgc_id == "BGC020"   # smoke: no crash, HAL handled
