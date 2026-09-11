"""Regression: TIER_1 floor excludes lone tailoring-enzyme markers (v9.7.19 tuning).

From the per_bgc-bridge blast-radius audit: the "float a Tier-1 diagnostic to >=Medium" floor must rescue
KCB-dark gene-only CLASS leads, but a lone halogenase / fluorinase-chlorinase is a MODIFICATION, not a class
call, and was flooring ~half of all floored BGCs. Tuning: tailoring-only markers do not floor on their own;
a class-defining marker that co-occurs still does; AF/AB diagnostic bonuses are untouched.
"""
import os
import sys
from types import SimpleNamespace as NS

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mamey.scoring import triage_bgcs


def _bgc(bid):
    # low-scoring region (product "other", KCB-dark) -> Inventory absent any floor
    return NS(bgc_id=bid, products=["other"], mibig_hits=[], kcb_top=None, kcb_cumulative=None,
              riq_score=None, edge_status="Full-contig", architecture_confidence="E",
              closest_candidate_kcb_product="UNRESOLVED", closest_product_provenance="UNRESOLVED")


def _scans(per_bgc):
    return NS(cctt={"per_bgc": per_bgc}, resistance_tiers={"per_bgc": {}})


def _tier(bid, triggers):
    recs = triage_bgcs([_bgc(bid)], None, _scans({bid: triggers}))
    return recs[0].lead_tier


def test_lone_halogenase_does_not_floor():
    assert _tier("H1", ["T43-HAL_halogenase"]) == "Inventory"


def test_lone_fluorinase_chlorinase_does_not_floor():
    assert _tier("X1", ["T43-XHAL_fluorinase_chlorinase"]) == "Inventory"


def test_class_marker_floors_to_medium():
    # a genuine class-defining marker still floats a KCB-dark gene-only lead to >=Medium
    for trig in ["T43-ENE_enediyne", "T43-PHO_phosphonate", "T43-DKP_cdps",
                 "T43-TET_tetronate_spirotetronate", "T43-IDC_indolocarbazole"]:
        assert _tier("C1", [trig]) in ("Medium", "High", "Exceptional"), f"{trig} failed to floor"


def test_halogenase_co_occurring_with_class_marker_still_floors():
    # the co-occurring case (Actinomadura BGC018 pattern): enediyne floors, halogenase rides along
    assert _tier("CO", ["T43-ENE_enediyne", "T43-HAL_halogenase"]) in ("Medium", "High", "Exceptional")


def test_terpene_control_with_no_trigger_stays_inventory():
    assert _tier("T1", []) == "Inventory"


if __name__ == "__main__":
    for fn in list(globals().values()):
        if callable(fn) and getattr(fn, "__name__", "").startswith("test_"):
            fn()
    print("tier-1 floor tuning: all tests pass")
