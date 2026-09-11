"""v9.7.87 Defect 1 + Defect 2: deterministic figure layout de-collision."""
from __future__ import annotations
import pytest as _pytest
_pytest.importorskip("matplotlib")  # SKIP (not error) when figure stack absent
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest


def test_dapr_scatter_label_decollision(tmp_path, monkeypatch):
    # two BGCs sharing (ab, af) must NOT print at the same y-offset
    from mamey import figures_sapote as fs
    rows = [
        {"bgc_id": "BGC010", "contig": "NODE_2", "region": "r001", "products": ["PKS"],
         "boundary": "Interior", "ab": 39.0, "af": 34.0, "kcb_top": "x"},
        {"bgc_id": "BGC013", "contig": "NODE_3", "region": "r002", "products": ["PKS"],
         "boundary": "Interior", "ab": 39.0, "af": 34.0, "kcb_top": "y"},
    ]
    offsets = []
    import matplotlib.axes
    orig = matplotlib.axes.Axes.annotate
    def spy(self, text, xy, *a, **k):
        offsets.append(tuple(k.get("xytext", (0, 0))))
        return orig(self, text, xy, *a, **k)
    monkeypatch.setattr(matplotlib.axes.Axes, "annotate", spy)
    fs.fig_dapr_scatter(rows, str(tmp_path / "d.png"), "Test sp.", plt)
    # the two collided labels must have distinct y offsets (no exact overprint)
    ys = [o[1] for o in offsets]
    assert len(set(ys)) == len(ys), f"labels overprinted at identical offsets: {offsets}"


def test_rggmci_legend_above_axes(tmp_path):
    # render the rescue chart and assert the legend anchor is above the axes (y >= 1.0)
    from mamey import render_brief as rb
    import csv
    pairs = tmp_path / "pairs.csv"
    with open(pairs, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["bgc_a", "bgc_b", "rggmci_score", "rggmci_confidence"])
        w.writeheader()
        for i in range(4):
            w.writerow({"bgc_a": f"BGC{i:03d}", "bgc_b": f"BGC{i+50:03d}",
                        "rggmci_score": 10 + i, "rggmci_confidence": "HIGH_RG_GMCI_RESCUE"})
    png = tmp_path / "r.png"
    # TEST-03: do NOT swallow renderer breakage into a skip — a broken renderer must FAIL here.
    rb.fig_rggmci_rescue(str(pairs), str(png), "Test sp.", plt)
    assert png.exists() and png.stat().st_size > 0
    # Invariant (Defect 2): the confidence legend is anchored ABOVE the axes (y >= 1.0 in
    # axes-fraction), not inside the data area where it masked the low-rank bars. The renderer
    # leaves the figure open, so read the legend off the current axes and check its position.
    fig = plt.gcf()
    fig.canvas.draw()
    ax = plt.gca()
    leg = ax.get_legend()
    assert leg is not None, "rescue figure must draw a confidence legend"
    leg_y0_axesfrac = ax.transAxes.inverted().transform(
        (0, leg.get_window_extent().y0))[1]
    assert leg_y0_axesfrac >= 1.0, f"legend anchored inside/below axes (y={leg_y0_axesfrac:.3f})"
    plt.close(fig)
