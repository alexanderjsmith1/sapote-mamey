"""Regression test for the diagnostic-floor / nucleoside fix (JudgmentChecks #11).

Guards the headline fix: a KCB-dark nucleoside (product labelled only "nucleoside", anchor a bare chromosome
hit — no antifungal word to keyword-match) must still reach lead tier when its T43-NUC diagnostic fired, because
nikkomycin/polyoxin chitin-synthase inhibitors are antifungal. Without the scan layer it correctly stays
Inventory (the bug). A terpene control with no diagnostic must NOT be floored. Verified against the two real
cases this fix was built and validated on: AS-XXX/BGC008 and M. humida/BGC034 (both KCB-dark nucleosides).
"""
import os, sys
from types import SimpleNamespace as NS

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mamey.scoring import triage_bgcs


def _bgc(bid, products, kcb, edge="Full-contig"):
    # scoring.py reads only these attributes off a BGC record
    return NS(bgc_id=bid, products=list(products), mibig_hits=[], kcb_top=kcb,
              kcb_cumulative=None, riq_score=None, edge_status=edge, architecture_confidence="E")


def _scans(per_bgc_triggers):
    return NS(cctt={"per_bgc": per_bgc_triggers}, resistance_tiers={"per_bgc": {}})


def _tier(records, bid):
    return next(r.lead_tier for r in records if r.bgc_id == bid)


def test_kcb_dark_nucleoside_floored_with_t43nuc():
    """BGC008 (AS-XXX) + BGC034 (M. humida) pattern: KCB-dark nucleoside + T43-NUC -> at least Medium."""
    bgcs = [_bgc("BGC008", ["nucleoside", "other"], "Streptomyces sp. M56 chromosome"),
            _bgc("BGC034", ["nucleoside", "halogenated"], "Micromonospora sp. chromosome")]
    recs = triage_bgcs(bgcs, None, _scans({"BGC008": ["T43-NUC_nucleoside"],
                                           "BGC034": ["T43-NUC_nucleoside"]}))
    assert _tier(recs, "BGC008") in ("Medium", "High", "Exceptional"), "BGC008 nucleoside not floored"
    assert _tier(recs, "BGC034") in ("Medium", "High", "Exceptional"), "BGC034 nucleoside not floored"


def test_nucleoside_stays_bottom_without_scans():
    """No scan layer -> the diagnostic can't be read -> NOT floored to a lead tier (the bug being guarded).
    AQUARIUS_01: the bottom tier is now class-gated — a nucleoside is a specialized (non-housekeeping)
    class, so its un-floored bottom is 'Low', not 'Inventory'. The guarded property is unchanged: without
    the T43-NUC diagnostic it does not reach Medium+."""
    recs = triage_bgcs([_bgc("BGC008", ["nucleoside", "other"], "Streptomyces sp. M56 chromosome")])
    assert _tier(recs, "BGC008") == "Low"
    assert _tier(recs, "BGC008") not in ("Medium", "High", "Exceptional")


def test_terpene_control_not_floored():
    """A terpene with no nucleoside / no diagnostic trigger must NOT be floored — guards against over-firing."""
    recs = triage_bgcs([_bgc("BGC099", ["terpene"], "Streptomyces sp. chromosome")], None, _scans({}))
    assert _tier(recs, "BGC099") == "Inventory"


if __name__ == "__main__":  # allow running without pytest
    test_kcb_dark_nucleoside_floored_with_t43nuc()
    test_nucleoside_stays_bottom_without_scans()
    test_terpene_control_not_floored()
    print("diagnostic-floor regression: all 3 tests pass")
