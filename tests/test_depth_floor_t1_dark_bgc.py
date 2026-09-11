"""test_depth_floor_t1_dark_bgc.py — v9.7.93 (Cut 2: standard mode retired)

Standard mode is retired (v9.7.92) and gold is the engine's only full-analysis
mode. In Cut 2 (v9.7.93) _depth_floor's former heuristic (Interior / CCTT /
KCB-threshold / T1-dark-BGC promotion) was hard-removed: under gold EVERY BGC
floors to full_mode_b and nothing is ever abbreviated.

This test preserves the original regression intent — the dark-BGC profile
(T1 self-protection + blank KCB, e.g. BGC063 on NODE_8) must receive full Mode B —
and additionally pins the Cut 2 invariant: there is no input for which _depth_floor
returns abbreviated_ledger. The dark-BGC rescue is now a consequence of
gold-uniformity, not a special rule.
"""
from mamey.cli import _depth_floor
from mamey.models import BGCRecord


def _bgc(bgc_id, boundary="Full-contig", kcb_cumulative=None):
    return BGCRecord(
        bgc_id=bgc_id, contig="NODE_1", region_number=1,
        start=1, end=60000, contig_length=62000,
        products=["NRPS", "NRPS-like"], edge_status=boundary,
        architecture_confidence="D",
        kcb_top="", kcb_cumulative=kcb_cumulative,
    )


def _rt(bgc_id, tier):
    return {bgc_id: {"tier": tier, "genes": ["abcA"]}}


# ── Cut 2 invariant: every BGC floors to full_mode_b under gold ──────────────

def test_gold_full_contig_no_kcb_no_resistance_is_full():
    """Former abbreviated case (non-T1, no KCB, Full-contig) is now full under gold."""
    bgc = _bgc("BGC045", boundary="Full-contig", kcb_cumulative=None)
    assert _depth_floor(bgc, {}, "gold", rt_per_bgc={"BGC045": {"tier": "T3_MINOR"}}) == "full_mode_b"


def test_gold_no_resistance_data_is_full():
    bgc = _bgc("BGC050", boundary="Full-contig", kcb_cumulative=None)
    assert _depth_floor(bgc, {}, "gold", rt_per_bgc={}) == "full_mode_b"


def test_gold_is_default_mode_and_call_compatible():
    """mode defaults to gold; legacy positional call shapes still work."""
    bgc = _bgc("BGC001", boundary="Full-contig", kcb_cumulative=None)
    assert _depth_floor(bgc) == "full_mode_b"
    assert _depth_floor(bgc, {}, "gold") == "full_mode_b"
    assert _depth_floor(bgc, {}, "gold", rt_per_bgc={}) == "full_mode_b"


def test_no_abbreviated_ledger_for_any_input():
    """Cut 2: no input yields abbreviated_ledger — sweep the old branch profiles."""
    profiles = [
        _bgc("a", "Interior", None),
        _bgc("b", "Edge", None),
        _bgc("c", "Full-contig", None),
        _bgc("d", "Full-contig", 0),
        _bgc("e", "Full-contig", 8000),
    ]
    for bgc in profiles:
        assert _depth_floor(bgc, {}, "gold", rt_per_bgc={}) == "full_mode_b"


# ── Preserved regression intent: dark-BGC profile gets full Mode B ───────────

def test_dark_bgc_t1_no_kcb_full_contig_gets_full_mode_b():
    """BGC063 profile (T1 self-protection + blank KCB, Full-contig) → full_mode_b.

    Originally rescued by the dark-BGC heuristic rule; now guaranteed by gold-uniformity.
    """
    bgc = _bgc("BGC063", boundary="Full-contig", kcb_cumulative=None)
    rt = _rt("BGC063", "T1_DIAGNOSTIC_SELF_PROTECTION_SOURCE_DERIVED")
    assert _depth_floor(bgc, {}, "gold", rt_per_bgc=rt) == "full_mode_b"


def test_dark_bgc_t1_no_kcb_edge_gets_full_mode_b():
    bgc = _bgc("BGC003", boundary="Edge", kcb_cumulative=0)
    rt = _rt("BGC003", "T1_DIAGNOSTIC_SELF_PROTECTION_SOURCE_DERIVED")
    assert _depth_floor(bgc, {}, "gold", rt_per_bgc=rt) == "full_mode_b"


def test_interior_still_full_mode_b():
    bgc = _bgc("BGC028", boundary="Interior", kcb_cumulative=None)
    assert _depth_floor(bgc, {}, "gold", rt_per_bgc={}) == "full_mode_b"


def test_cctt_trigger_still_full():
    bgc = _bgc("BGC026", boundary="Full-contig", kcb_cumulative=None)
    assert _depth_floor(bgc, {"BGC026": ["T43-LAN"]}, "gold", rt_per_bgc={}) == "full_mode_b"


def test_high_kcb_still_full():
    bgc = _bgc("BGC040", boundary="Full-contig", kcb_cumulative=7500)
    assert _depth_floor(bgc, {}, "gold", rt_per_bgc={}) == "full_mode_b"
