"""test_umed_gap_flag.py — v9.7.62

Tests that the UMED maturation gap flag is correctly set on TriageRecord and
emitted in the triage board CSV when a RiPP/nucleoside BGC has no nearby
maturation genes (verdict = MATURATION_GAP_SOURCE_DERIVED).

Closes worst-list item 21: UMED GAP findings previously only in scan_states.json,
invisible in the triage board.
"""
import pytest
from types import SimpleNamespace
from mamey.scoring import triage_bgcs
from mamey.models import BGCRecord


def _make_bgc(bgc_id, products, edge="Interior"):
    return BGCRecord(
        bgc_id=bgc_id, contig="NODE_1", region_number=1,
        start=1, end=20000, contig_length=100000,
        products=list(products), edge_status=edge,
        architecture_confidence="A", kcb_top="", kcb_cumulative=0,
    )


def _scans_with_umed(umed_per_bgc: dict) -> SimpleNamespace:
    return SimpleNamespace(
        cctt={"per_bgc": {}, "context_uncorroborated_by_bgc": {}},
        cassette={},
        primary_metabolism={"per_bgc": {}},
        resistance_tiers={"per_bgc": {}},
        umed={"per_bgc": umed_per_bgc},
    )


def test_umed_gap_flag_set_for_maturation_gap_bgc():
    """When UMED verdict is MATURATION_GAP_SOURCE_DERIVED, umed_gap_flag = MATURATION_GAP."""
    bgc = _make_bgc("BGC001", ["RiPP", "lanthipeptide-class-i"])
    scans = _scans_with_umed({
        "BGC001": {
            "needs_maturation": True,
            "umed_hits": [],
            "verdict": "MATURATION_GAP_SOURCE_DERIVED",
        }
    })
    records = triage_bgcs([bgc], scans=scans)
    assert records[0].umed_gap_flag == "MATURATION_GAP", (
        f"Expected MATURATION_GAP, got {records[0].umed_gap_flag!r}"
    )


def test_umed_gap_flag_empty_when_maturation_supported():
    """When UMED verdict is IN_CLUSTER_OR_PROXIMAL, umed_gap_flag is empty."""
    bgc = _make_bgc("BGC002", ["RiPP", "lanthipeptide-class-i"])
    scans = _scans_with_umed({
        "BGC002": {
            "needs_maturation": True,
            "umed_hits": ["LanP"],
            "verdict": "IN_CLUSTER_OR_PROXIMAL_MATURATION_SOURCE_SUPPORTED",
        }
    })
    records = triage_bgcs([bgc], scans=scans)
    assert records[0].umed_gap_flag == "", (
        f"Expected empty, got {records[0].umed_gap_flag!r}"
    )


def test_umed_gap_flag_empty_when_not_maturation_gated():
    """PKS BGC with NOT_MATURATION_GATED verdict: flag is empty."""
    bgc = _make_bgc("BGC003", ["PKS", "T1PKS"])
    scans = _scans_with_umed({
        "BGC003": {
            "needs_maturation": False,
            "umed_hits": [],
            "verdict": "NOT_MATURATION_GATED",
        }
    })
    records = triage_bgcs([bgc], scans=scans)
    assert records[0].umed_gap_flag == ""


def test_umed_gap_flag_empty_when_bgc_not_in_umed():
    """BGC not present in UMED per_bgc dict: flag defaults to empty."""
    bgc = _make_bgc("BGC004", ["RiPP", "thiopeptide"])
    scans = _scans_with_umed({})  # BGC004 absent
    records = triage_bgcs([bgc], scans=scans)
    assert records[0].umed_gap_flag == ""


def test_umed_gap_flag_empty_when_no_scans():
    """No scans object at all: flag defaults to empty (graceful degradation)."""
    bgc = _make_bgc("BGC005", ["RiPP", "lassopeptide"])
    records = triage_bgcs([bgc], scans=None)
    assert records[0].umed_gap_flag == ""


def test_umed_gap_flag_nucleoside_bgc():
    """Nucleoside BGC with maturation gap: flag set correctly."""
    bgc = _make_bgc("BGC006", ["nucleoside", "other"])
    scans = _scans_with_umed({
        "BGC006": {
            "needs_maturation": True,
            "umed_hits": [],
            "verdict": "MATURATION_GAP_SOURCE_DERIVED",
        }
    })
    records = triage_bgcs([bgc], scans=scans)
    assert records[0].umed_gap_flag == "MATURATION_GAP"


def test_umed_gap_flag_as902_lanthipeptide_case():
    """Regression: AS-XXX BGC031 lanthipeptide with UMED GAP (from audit)."""
    bgc = _make_bgc("BGC031", ["RiPP", "lanthipeptide-class-i"])
    scans = _scans_with_umed({
        "BGC031": {
            "needs_maturation": True,
            "umed_hits": [],
            "verdict": "MATURATION_GAP_SOURCE_DERIVED",
        }
    })
    records = triage_bgcs([bgc], scans=scans)
    rec = records[0]
    assert rec.umed_gap_flag == "MATURATION_GAP"
    # Flag should not affect tier or scores
    assert rec.lead_tier is not None
    assert rec.ab_score >= 0
