"""Figure layout-lint (#10) — guards the render_brief overlap fixes (audit W2/W13) from silent regression.

The v9.7.31 migration moved the tier swatch off the bars into a right gutter and the tier legend below the
axes. These asserts fail if either is moved back onto the plot: (1) the tier legend must not overlap the
axes; (2) the tier-swatch markers must sit in the right gutter (x >= the bar axis upper limit). The
composition figure's boundary legend must also sit outside its axes.
"""
import pytest as _pytest
_pytest.importorskip("matplotlib")  # SKIP (not error) when figure stack absent
import matplotlib
matplotlib.use("Agg")
from mamey.render_brief import _setup_mpl, fig_landscape, fig_composition


def _row(bid, products, ab=50, tier="High"):
    return {"rank": bid[-1], "bgc_id": bid, "contig": "c1", "region": f"r{bid[-1]}", "products": products,
            "boundary": "Interior", "arch": "A", "ab": ab, "af": 20, "novelty": 30, "lead_tier": tier,
            "kcb_top": "", "kcb_score": "", "cctt": ""}


def test_landscape_legend_outside_axes(tmp_path):
    plt = _setup_mpl()
    rows = [_row("BGC001", "NRPS", ab=80, tier="High"), _row("BGC002", "T1PKS", ab=60, tier="Medium")]
    fig = fig_landscape(rows, str(tmp_path / "land.png"), "S", plt)
    fig.canvas.draw()
    ax = fig.axes[0]
    leg = ax.get_legend()
    assert leg is not None, "tier legend missing"
    # the tier legend must sit OUTSIDE the plot area (it was colliding with the title before the fix)
    assert not ax.get_window_extent().overlaps(leg.get_window_extent()), \
        "tier legend overlaps the axes (W2/title-collision regression)"
    plt.close(fig)


def test_landscape_tier_swatch_in_right_gutter(tmp_path):
    plt = _setup_mpl()
    rows = [_row("BGC001", "NRPS", ab=80, tier="High"), _row("BGC002", "T1PKS", ab=60, tier="Inventory")]
    fig = fig_landscape(rows, str(tmp_path / "land.png"), "S", plt)
    ax = fig.axes[0]
    xmax = ax.get_xlim()[1]   # the 0-100 bar axis upper limit
    # find the tier-swatch scatter (a PathCollection with point offsets) and assert it's off the bars
    swatch_collections = [c for c in ax.collections if getattr(c, "get_offsets", None) and len(c.get_offsets())]
    assert swatch_collections, "no tier-swatch scatter found"
    for c in swatch_collections:
        xs = [float(o[0]) for o in c.get_offsets()]
        assert all(x >= xmax for x in xs), \
            f"tier swatch at x={xs} is on the bars (must be in the gutter x>={xmax}) — W2 regression"
    plt.close(fig)


def test_composition_legend_outside_axes(tmp_path):
    plt = _setup_mpl()
    rows = [_row("BGC001", "NRPS"), _row("BGC002", "T1PKS"), _row("BGC003", "saccharide")]
    fig = fig_composition(rows, str(tmp_path / "comp.png"), plt)
    fig.canvas.draw()
    # the boundary-mix legend lives on the right axes; it must sit below/outside that axes
    for ax in fig.axes:
        leg = ax.get_legend()
        if leg is not None:
            assert not ax.get_window_extent().overlaps(leg.get_window_extent()), \
                "composition legend overlaps its axes"
    plt.close(fig)
