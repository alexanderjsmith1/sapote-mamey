"""F2 — RiPP completeness floor: a RiPP-family product on a truncated sub-8kb fragment is capped at
Inventory (lone modifying enzyme + KCB can't float a fragment above a complete cluster). Never touches
Interior or large regions."""
import types
from mamey.models import BGCRecord
from mamey.scoring import triage_bgcs


def _bgc(bid, edge, span_kb, products=("lanthipeptide",)):
    return BGCRecord(bgc_id=bid, contig="ctg1", region_number=1, start=0, end=int(span_kb * 1000),
                     contig_length=int(span_kb * 1000), products=list(products),
                     edge_status=edge, architecture_confidence="D")


def _scans(bid):  # give the BGC a class trigger so its pre-floor tier reaches >= Medium
    return types.SimpleNamespace(cctt={"per_bgc": {bid: ["T43-LAN_lanthipeptide"]}})


def test_tiny_truncated_ripp_fragment_floored():
    r = triage_bgcs([_bgc("BGC001", "Full-contig", 3.7)], scans=_scans("BGC001"))[0]
    # AQUARIUS_01: the bottom tier is class-gated — a RiPP (lanthipeptide) is specialized, so the
    # fragment floor caps it at 'Low' (specialized-but-unevaluable), not 'Inventory' (housekeeping).
    # The guarded property is unchanged: the fragment is capped at the bottom, never floated to a lead tier.
    assert r.lead_tier == "Low"
    assert "RIPP-FRAGMENT-FLOOR" in r.rationale and "fragment_no_precursor" in r.rationale


def test_interior_ripp_not_floored():
    # Interior = complete context; the fragment floor must not fire
    r = triage_bgcs([_bgc("BGC001", "Interior", 3.7)], scans=_scans("BGC001"))[0]
    assert r.lead_tier != "Inventory"
    assert "RIPP-FRAGMENT-FLOOR" not in r.rationale


def test_large_truncated_ripp_not_floored():
    # a 20 kb truncated RiPP region is large enough to carry precursor + maturation — not floored
    r = triage_bgcs([_bgc("BGC001", "Full-contig", 20.0)], scans=_scans("BGC001"))[0]
    assert "RIPP-FRAGMENT-FLOOR" not in r.rationale


def test_non_ripp_fragment_not_floored():
    r = triage_bgcs([_bgc("BGC001", "Full-contig", 3.7, products=("NRPS",))], scans=_scans("BGC001"))[0]
    assert "RIPP-FRAGMENT-FLOOR" not in r.rationale
