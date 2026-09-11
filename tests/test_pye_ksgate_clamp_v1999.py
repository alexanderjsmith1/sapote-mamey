"""End-to-end scoring tests for the T43-PYE KS-gate and the v1.9.99 triple-count clamp.

These fill the GAP the audit brief flagged: the 13 pattern tests cover matching/axis/corroboration,
but NOT a full triage_bgcs() run proving (a) KS<4 -> no AF bonus, (b) KS>=4 -> AF bonus, and
(c) the polyene chemotype +22 is SUBSUMED (not stacked) when T43-PYE fires corroborated.
"""
import os, sys
from types import SimpleNamespace as NS

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mamey.scoring import triage_bgcs, AF_DIAGNOSTIC_TRIGGERS


def _bgc(bid, products, chemotype_af=0.0, chemotype="", kcb="Streptomyces sp. chromosome", edge="Interior"):
    cca = {}
    if chemotype_af:
        cca = {"chemotype": chemotype, "scored_axis": "af", "scored_weight": chemotype_af}
    return NS(bgc_id=bid, products=list(products), mibig_hits=[], kcb_top=kcb,
              kcb_cumulative=None, riq_score=None, edge_status=edge, architecture_confidence="A",
              compound_class_annotation=cca)


def _scans(triggers_by_bgc, ks_by_bgc=None):
    mis = {bid: {"ks_domain_count": ks} for bid, ks in (ks_by_bgc or {}).items()}
    return NS(cctt={"per_bgc": triggers_by_bgc},
              resistance_tiers={"per_bgc": {}},
              misanchor_guards={"per_bgc": mis})


def _af(records, bid):
    return next(r.af_score for r in records if r.bgc_id == bid)


def test_pye_ksgate_ge4_grants_af_bonus():
    """A polyene with >=4 PKS_KS: T43-PYE corroborated -> AF diagnostic bonus applied."""
    bgc = [_bgc("BGC010", ["polyene", "T1PKS"])]
    with_ks = _af(triage_bgcs(bgc, None, _scans({"BGC010": ["T43-PYE_polyene_macrolide"]}, {"BGC010": 6})), "BGC010")
    none = _af(triage_bgcs(bgc, None, _scans({})), "BGC010")
    assert with_ks > none, f"genuine polyene (6 KS) got no AF bonus ({none} -> {with_ks})"


def test_pye_ksgate_below4_no_bonus():
    """A polyene NAME on a <4-KS fragment: T43-PYE demoted to uncorroborated -> NO AF bonus."""
    bgc = [_bgc("BGC011", ["polyene"])]
    low_ks = _af(triage_bgcs(bgc, None, _scans({"BGC011": ["T43-PYE_polyene_macrolide"]}, {"BGC011": 2})), "BGC011")
    none = _af(triage_bgcs(bgc, None, _scans({})), "BGC011")
    assert low_ks == none, f"sub-4-KS polyene must not get the diagnostic bonus ({none} vs {low_ks})"


def test_pye_missing_ks_defaults_safe_no_bonus():
    """If mis-anchor scan didn't run (no ks_domain_count), PYE defaults to uncorroborated (safe direction)."""
    bgc = [_bgc("BGC012", ["polyene"])]
    no_mis = _af(triage_bgcs(bgc, None, _scans({"BGC012": ["T43-PYE_polyene_macrolide"]}, {})), "BGC012")
    none = _af(triage_bgcs(bgc, None, _scans({})), "BGC012")
    assert no_mis == none, f"missing KS data must default to no bonus (safe), got {none} vs {no_mis}"


def test_pye_clamp_subsumes_chemotype_credit():
    """Triple-count clamp: a polyene with chemotype +22 AND corroborated T43-PYE must NOT stack both.
    The diagnostic (+25) subsumes the chemotype (+22): the chemotype credit is removed when PYE fires."""
    # Same BGC, with chemotype credit, scored two ways: PYE corroborated (>=4 KS) vs no trigger.
    bgc_pye = [_bgc("BGC013", ["polyene", "T1PKS"], chemotype_af=22.0, chemotype="polyene_macrolide")]
    bgc_none = [_bgc("BGC013", ["polyene", "T1PKS"], chemotype_af=22.0, chemotype="polyene_macrolide")]
    af_pye = _af(triage_bgcs(bgc_pye, None, _scans({"BGC013": ["T43-PYE_polyene_macrolide"]}, {"BGC013": 6})), "BGC013")
    af_none = _af(triage_bgcs(bgc_none, None, _scans({})), "BGC013")
    # With the clamp: PYE adds +25 diagnostic but removes the +22 chemotype, so net gain over baseline is +3 (25-22),
    # NOT +25. Verify the gain is the diagnostic-minus-chemotype, proving no double-count.
    gain = af_pye - af_none
    assert gain < 25, f"clamp failed: polyene gained full +{gain} (chemotype not subsumed -> double-count)"
    assert gain > 0, f"PYE should still net-increase AF (diagnostic>chemotype), got {gain}"
