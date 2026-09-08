"""Regression guards for the v9.7.7 P0 primary-metabolism / pigment gate (+ thiopeptide, nucleoside).

Covers the three convergent field reports:
- Doc 3 P0: SID-XXX topoisomerase "NRPS-like" ranked #1 AB (primary-metabolism false positive).
- Doc 1 P1-1: carotenoid (lycopene cyclase) under a "terpene" label credited on the AF axis.
- Doc 1 P1-1b: thiopeptide under-ranked (no AB keyword).
- Doc 3 TEST: nucleoside BGC must still score on AF (lock the v9.7.6 cassette-aware fix).

The gate fires only when (a) a housekeeping/pigment core-gene marker is in the BGC's own CDS,
(b) the BGC's own product class is exclusively weak/over-call labels, and (c) no Tier-1 diagnostic
fires. Committed classes and CCTT diagnostics exempt the region.

Standalone: python3 tests/test_primary_metabolism_gate.py
"""
from __future__ import annotations
import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mamey.models import BGCRecord
from mamey.scoring import triage_bgcs, AB_KEYWORDS, AF_KEYWORDS


def _bgc(bgc_id, products, edge="Interior", arch="A", kcb=None):
    return BGCRecord(bgc_id=bgc_id, contig="c1", region_number=1, start=1, end=9000, contig_length=20000,
                     products=list(products), edge_status=edge, architecture_confidence=arch, kcb_cumulative=kcb)


def _scans(pm=None, cctt=None):
    """Minimal stub exposing the three per-BGC dicts triage_bgcs reads."""
    return SimpleNamespace(
        primary_metabolism={"per_bgc": pm or {}},
        cctt={"per_bgc": cctt or {}},
        resistance_tiers={"per_bgc": {}},
    )


def _by_id(records):
    return {r.bgc_id: r for r in records}


def test_topoisomerase_primary_metab_suppressed():
    """NRPS-like + housekeeping marker -> flagged, AB stripped to floor, below a real NRPS."""
    bgcs = [_bgc("BGC017", ["NRPS-like"]), _bgc("BGC900", ["NRPS", "T1PKS"])]
    pm = {"BGC017": {"families": ["housekeeping"]}}  # topoisomerase/dTMP kinase inside the region
    recs = _by_id(triage_bgcs(bgcs, None, _scans(pm=pm)))
    assert recs["BGC017"].primary_metabolism_flag is True
    # AB stripped: floor 25 minus interior penalty(0) -> 25; the real NRPS must outrank it
    assert recs["BGC017"].ab_score < recs["BGC900"].ab_score
    assert recs["BGC017"].ab_score <= 25.0
    assert recs["BGC900"].primary_metabolism_flag is False


def test_carotenoid_terpene_not_antifungal():
    """terpene + pigment marker (lycopene cyclase) -> flagged, AF stripped to floor."""
    bgcs = [_bgc("BGC053", ["terpene"])]
    pm = {"BGC053": {"families": ["pigment"]}}
    recs = _by_id(triage_bgcs(bgcs, None, _scans(pm=pm)))
    assert recs["BGC053"].primary_metabolism_flag is True
    assert recs["BGC053"].af_score <= 20.0   # terpene(+6) credit removed


def test_real_cluster_with_housekeeping_neighbor_not_flagged():
    """A committed class (NRPS;T1PKS) is exempt even if a housekeeping marker couples to it."""
    bgcs = [_bgc("BGC900", ["NRPS", "T1PKS"])]
    pm = {"BGC900": {"families": ["housekeeping"]}}
    recs = _by_id(triage_bgcs(bgcs, None, _scans(pm=pm)))
    assert recs["BGC900"].primary_metabolism_flag is False
    assert recs["BGC900"].ab_score > 25.0    # keeps nrps(12)+t1pks(10) credit


def test_tier1_diagnostic_exempts_gate():
    """A Tier-1 CCTT diagnostic overrides the gate even on a weak label + pigment marker."""
    bgcs = [_bgc("BGC700", ["terpene"])]
    pm = {"BGC700": {"families": ["pigment"]}}
    cctt = {"BGC700": ["T43-NUC_nucleoside"]}
    recs = _by_id(triage_bgcs(bgcs, None, _scans(pm=pm, cctt=cctt)))
    assert recs["BGC700"].primary_metabolism_flag is False


def test_no_marker_no_flag():
    """A weak label with NO housekeeping/pigment marker keeps its credit (gate needs gene evidence)."""
    bgcs = [_bgc("BGC100", ["terpene"])]
    recs = _by_id(triage_bgcs(bgcs, None, _scans(pm={})))
    assert recs["BGC100"].primary_metabolism_flag is False
    assert recs["BGC100"].af_score > 20.0    # terpene credit intact


def test_thiopeptide_scores_on_ab():
    """Doc1 P1-1b: thiopeptide must now carry AB weight (was a false negative)."""
    assert "thiopeptide" in AB_KEYWORDS and AB_KEYWORDS["thiopeptide"] >= 12
    bgcs = [_bgc("BGC031", ["thiopeptide"])]
    recs = _by_id(triage_bgcs(bgcs, None, _scans()))
    assert recs["BGC031"].ab_score > 25.0    # 25 + thiopeptide(14)


def test_nucleoside_scores_on_af_regression():
    """Doc3 TEST: lock the v9.7.6 fix — a nucleoside-product BGC scores on the AF axis."""
    assert AF_KEYWORDS.get("nucleoside", 0) >= 12
    bgcs = [_bgc("BGC001", ["nucleoside"])]
    recs = _by_id(triage_bgcs(bgcs, None, _scans()))
    assert recs["BGC001"].af_score > 20.0


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    p = 0
    for fn in fns:
        try:
            fn(); p += 1; print(f"PASS {fn.__name__}")
        except AssertionError as e:
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{p}/{len(fns)} passed")
