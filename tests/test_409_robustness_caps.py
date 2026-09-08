"""Functional tests for CLAUDE_409_robustness_caps_r2 (Tier-B deferred DoS/robustness items).

Run with the mamey package on sys.path (the scratchpad work copy). Each test states the
fail-before behaviour it guards against.
"""
import io
import os
import sys
import contextlib

import mamey.antismash_input as ai
import mamey.render_safe as rs
import mamey.pair_scan_caps as psc


def _stderr():
    return contextlib.redirect_stderr(io.StringIO())


# ---- FIX 1: antiSMASH version gate ----------------------------------------------------------
def test_version_in_range_no_warning():
    # antiSMASH 8 is inside the tested range -> trusted, no schema warning.
    assert ai.antismash_schema_warning("8.0.4", has_regions=True) is None


def test_version_out_of_range_warns():
    # FAIL-BEFORE: a future antiSMASH 9 that renames keys reads as "no hits" silently.
    w = ai.antismash_schema_warning("9.0.1", has_regions=True)
    assert w and w.startswith("ANTISMASH_SCHEMA_UNRECOGNIZED"), w
    # older, below-range major too (AS4 region-GBK schema predates the tested 5-8 range)
    w4 = ai.antismash_schema_warning("4.2.0", has_regions=True)
    assert w4 and "outside the tested range" in w4
    # a version INSIDE the range (6) must stay trusted at this coarse GBK-schema gate
    assert ai.antismash_schema_warning("6.1.1", has_regions=True) is None


def test_version_absent_with_regions_warns():
    w = ai.antismash_schema_warning(None, has_regions=True)
    assert w and w.startswith("ANTISMASH_SCHEMA_UNRECOGNIZED")


def test_version_absent_no_regions_silent():
    # A truly empty archive (no region GBKs) must NOT warn — absence is legitimate.
    assert ai.antismash_schema_warning(None, has_regions=False) is None


def test_version_gate_env_override():
    os.environ["MAMEY_ANTISMASH_MAX_MAJOR"] = "9"
    try:
        assert ai.antismash_schema_warning("9.0.1", has_regions=True) is None
    finally:
        del os.environ["MAMEY_ANTISMASH_MAX_MAJOR"]


# ---- FIX 2: figure canvas OOM guard ---------------------------------------------------------
class _FakeFig:
    def __init__(self, w, h):
        self._s = (w, h)
    def get_size_inches(self):
        return self._s


def test_canvas_dpi_unchanged_for_small_fig():
    # 10x8 in at 300 dpi = 3000 px, well under the ceiling -> dpi unchanged.
    assert rs.safe_savefig_dpi(_FakeFig(10, 8), 300) == 300


def test_canvas_dpi_clamped_for_large_fig():
    # 150 in wide at 300 dpi = 45000 px (> the 30000 ceiling) -> clamp DPI down, still >= floor.
    dpi = rs.safe_savefig_dpi(_FakeFig(150, 8), 300)
    assert dpi < 300
    assert 150 * dpi <= rs.max_figure_edge_px()


def test_canvas_refuses_when_even_floor_too_big():
    # 700 in at the 100-dpi floor = 70000 px, over the ceiling even clamped -> clean typed refusal.
    try:
        rs.safe_savefig_dpi(_FakeFig(700, 8), 300)
        assert False, "expected FigureCanvasTooLargeError"
    except rs.FigureCanvasTooLargeError as e:
        assert e.code == "FIGURE_CANVAS_TOO_LARGE"


# ---- FIX 4: O(n^2) pair-scan caps -----------------------------------------------------------
def test_pair_cap_passthrough_small():
    items = list(range(50))
    with _stderr() as err:
        out = psc.cap_pair_scan_items(items, label="unit")
    assert out == items
    assert err.getvalue() == ""  # no warning on real-sized input


def test_pair_cap_trims_and_warns():
    items = list(range(5000))
    with _stderr() as err:
        out = psc.cap_pair_scan_items(items, label="unit", cap=800)
    assert len(out) == 800
    assert out == items[:800]  # deterministic prefix
    assert "PAIR_SCAN_CAPPED" in err.getvalue()


def test_pair_cap_env_override():
    os.environ["MAMEY_MAX_PAIR_SCAN_ITEMS"] = "3"
    try:
        assert psc.max_pair_scan_items() == 3
    finally:
        del os.environ["MAMEY_MAX_PAIR_SCAN_ITEMS"]


# ---- FIX 3: subprocess timeout is wired (clinker) -------------------------------------------
def test_clinker_timeout_config():
    import mamey.bigscape_figures as bf
    assert bf._subprocess_timeout_sec() == 1800
    os.environ["MAMEY_SUBPROCESS_TIMEOUT_SEC"] = "5"
    try:
        assert bf._subprocess_timeout_sec() == 5.0
    finally:
        del os.environ["MAMEY_SUBPROCESS_TIMEOUT_SEC"]


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} passed")
