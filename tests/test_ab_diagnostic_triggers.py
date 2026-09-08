"""Regression: T43-PHO (phosphonate) and T43-AMC (aminoglycoside/aminocyclitol) grant the AB diagnostic bonus.

v9.7.20 wires two textbook antibacterial classes into AB_DIAGNOSTIC_TRIGGERS, making the high-confidence
detector layer consistent with the keyword weights the scorer already carries (phosphonate=15, aminoglycoside=14
— the top AB keywords). The bonus must apply when the class diagnostic fires, and must NOT leak to families that
were deliberately left unwired (e.g. T43-IDC indolocarbazole, whose pharmacology is mixed) — guarding against
over-classification. Verified on real data: AS-XXX BGC042 AB 40->65, AS-XXX BGC039 43.5->68.5 with the phosphonate
trigger wired.
"""
import os, sys
from types import SimpleNamespace as NS

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mamey.scoring import triage_bgcs, AB_DIAGNOSTIC_TRIGGERS


def _bgc(bid, products, kcb="Streptomyces sp. chromosome", edge="Full-contig"):
    return NS(bgc_id=bid, products=list(products), mibig_hits=[], kcb_top=kcb,
              kcb_cumulative=None, riq_score=None, edge_status=edge, architecture_confidence="E")


def _scans(per_bgc_triggers):
    return NS(cctt={"per_bgc": per_bgc_triggers}, resistance_tiers={"per_bgc": {}})


def _ab(records, bid):
    return next(r.ab_score for r in records if r.bgc_id == bid)


def test_phosphonate_and_aminoglycoside_are_ab_triggers():
    assert "T43-PHO" in AB_DIAGNOSTIC_TRIGGERS
    assert "T43-AMC" in AB_DIAGNOSTIC_TRIGGERS


def test_phosphonate_trigger_grants_ab_bonus():
    """Same phosphonate BGC scores higher in AB with its T43-PHO diagnostic than without it (the +bonus)."""
    bgc = [_bgc("BGC027", ["phosphonate"])]
    with_trig = _ab(triage_bgcs(bgc, None, _scans({"BGC027": ["T43-PHO_phosphonate"]})), "BGC027")
    without = _ab(triage_bgcs(bgc, None, _scans({})), "BGC027")
    assert with_trig > without, f"phosphonate diagnostic granted no AB bonus ({without} -> {with_trig})"


def test_aminocyclitol_trigger_grants_ab_bonus():
    """T43-AMC (a fired aminocyclitol diagnostic = a real aminoglycoside, not a similarity-only anchor)."""
    bgc = [_bgc("BGC050", ["aminoglycoside"])]
    with_trig = _ab(triage_bgcs(bgc, None, _scans({"BGC050": ["T43-AMC_aminocyclitol"]})), "BGC050")
    without = _ab(triage_bgcs(bgc, None, _scans({})), "BGC050")
    assert with_trig > without, f"aminocyclitol diagnostic granted no AB bonus ({without} -> {with_trig})"


def test_unwired_family_grants_no_ab_bonus():
    """T43-IDC (indolocarbazole) was deliberately left unwired (mixed pharmacology) — no AB bonus leak.

    It still floors to Medium as any class diagnostic does; we assert only that the AB *score* is unchanged
    versus the no-trigger control, i.e. the diagnostic bonus did not fire.
    """
    bgc = [_bgc("BGC077", ["indole"])]
    with_idc = _ab(triage_bgcs(bgc, None, _scans({"BGC077": ["T43-IDC_indolocarbazole"]})), "BGC077")
    without = _ab(triage_bgcs(bgc, None, _scans({})), "BGC077")
    assert with_idc == without, f"unwired T43-IDC leaked an AB bonus ({without} -> {with_idc})"


if __name__ == "__main__":
    test_phosphonate_and_aminoglycoside_are_ab_triggers()
    test_phosphonate_trigger_grants_ab_bonus()
    test_aminocyclitol_trigger_grants_ab_bonus()
    test_unwired_family_grants_no_ab_bonus()
    print("AB diagnostic-trigger regression: all 4 tests pass")
