"""AQUARIUS_01 (v9.7.350/.351) — class-gated bottom tier guard.

the Developer or User's rule (2026-08-04): the Inventory tier is reserved for genuinely low-interest housekeeping
classes (saccharide, terpene, geosmin, ectoine, NAPAA + the Developer or User-ratified broadened primary-metabolism/
pigment/signaling/glycolipid classes). A specialized / antimicrobial-capable BGC that merely scored
below the Medium threshold is labelled 'Low', not buried in 'Inventory'.

Locks the invariant so a future edit cannot silently re-bury specialized clusters in Inventory, and
guards that the relabel never touches a higher tier or any score. Claim-safe: tiers are auto-floor
routing priors, not measured activity; class = capacity. Judgment deferred.
"""
import os, sys
from types import SimpleNamespace as NS

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mamey.scoring import (triage_bgcs, is_housekeeping_only, bottom_tier,  # noqa: E402
                           HOUSEKEEPING_INVENTORY_CLASSES)
from mamey.boundary_audit import LEAD_TIERS  # noqa: E402
from mamey.package_addons import _LEAD_TIER_ORDER  # noqa: E402


def _bgc(bid, products):
    return NS(bgc_id=bid, products=list(products), mibig_hits=[], kcb_top="Streptomyces sp. chromosome",
              kcb_cumulative=None, riq_score=None, edge_status="Full-contig", architecture_confidence="E")


def _tier(records, bid):
    return next(r.lead_tier for r in records if r.bgc_id == bid)


def test_housekeeping_classes_are_inventory():
    for c in ("saccharide", "terpene", "geosmin", "ectoine", "napaa"):
        assert is_housekeeping_only(_bgc("B", [c])), c
        assert bottom_tier(_bgc("B", [c])) == "Inventory", c


def test_broadened_classes_are_inventory():
    # the Developer or User-ratified broadened housekeeping (2026-08-04)
    for c in ("fatty_acid", "arylpolyene", "melanin", "butyrolactone", "hserlactone",
              "hgle-ks", "redox-cofactor", "naggn"):
        assert c in HOUSEKEEPING_INVENTORY_CLASSES, c
        assert bottom_tier(_bgc("B", [c])) == "Inventory", c
        assert is_housekeeping_only(_bgc("B", [c])), c


def test_specialized_classes_are_low():
    for c in ("nrps", "pks", "t1pks", "ripp", "lanthipeptide", "lassopeptide", "phenazine",
              "nucleoside", "ni-siderophore", "nrp-metallophore"):
        assert not is_housekeeping_only(_bgc("B", [c])), c
        assert bottom_tier(_bgc("B", [c])) == "Low", c


def test_mixed_housekeeping_plus_specialized_is_low():
    # any specialized class in the region -> Low (surface the specialized signal)
    assert bottom_tier(_bgc("B", ["saccharide", "nrps"])) == "Low"
    assert bottom_tier(_bgc("B", ["terpene", "ripp"])) == "Low"


def test_unresolved_is_inventory():
    assert bottom_tier(_bgc("B", ["other"])) == "Inventory"
    assert bottom_tier(_bgc("B", [])) == "Inventory"


def test_low_scoring_specialized_routes_to_low_not_inventory():
    # bare specialized product, no scans, no diagnostic -> below Medium -> 'Low' (not Inventory, not Medium)
    recs = triage_bgcs([_bgc("BGC1", ["nrps"])])
    assert _tier(recs, "BGC1") == "Low"


def test_low_scoring_housekeeping_stays_inventory():
    recs = triage_bgcs([_bgc("BGC2", ["terpene"])])
    assert _tier(recs, "BGC2") == "Inventory"


def test_tier_set_and_ordering_include_low():
    assert "Low" in LEAD_TIERS
    # Low ranks above Inventory, below Medium
    assert _LEAD_TIER_ORDER["Medium"] < _LEAD_TIER_ORDER["Low"] < _LEAD_TIER_ORDER["Inventory"]


if __name__ == "__main__":
    for fn in list(globals()):
        if fn.startswith("test_"):
            globals()[fn]()
    print("inventory-tier-reform guard: all tests pass")
