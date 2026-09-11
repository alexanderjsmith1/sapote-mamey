"""v9.7.400 regression: the per-BGC CCTT + resistance-tier-strip figure must DEFINE the strip.

The strip's tier colours (T1/T2/T3/NULL) were previously undefined anywhere on the rendered
image — an unlabeled orange/red/blue band. The figure must now carry a legend naming every tier.
Claim-safety: tiers are source-derived routing strata, not resistance assertions; the legend
wording stays capacity-level.
"""
import pytest

mpl = pytest.importorskip("matplotlib")
mpl.use("Agg")

import mamey.cohort_figures as cf

DEEP = {
    "bgc_profile": [
        {"bgc_id": "BGC001", "cctt_triggers": "T43-HAL",
         "resistance_tier": "T1_DIAGNOSTIC_SELF_PROTECTION_SOURCE_DERIVED"},
        {"bgc_id": "BGC002", "cctt_triggers": "T43-LAN",
         "resistance_tier": "T3_TRANSPORTER_ONLY_ROUTING"},
        {"bgc_id": "BGC003", "cctt_triggers": "T43-HAL,T43-LAN",
         "resistance_tier": "NULL_NO_SOURCE_DERIVED_RESISTANCE"},
    ],
    "active_sites": [],
}


def test_resistance_strip_figure_carries_tier_legend(tmp_path, monkeypatch):
    captured = []
    real_close = cf.plt.close

    def _capture(fig=None):
        try:
            if fig is not None and hasattr(fig, "axes"):
                for ax in fig.axes:
                    leg = ax.get_legend()
                    if leg is not None:
                        captured.append([t.get_text() for t in leg.get_texts()])
        finally:
            real_close(fig) if fig is not None else real_close()

    monkeypatch.setattr(cf.plt, "close", _capture)
    cf.figs_single({"ST-500": {"deep": DEEP}}, "ST-500", str(tmp_path))

    pngs = [p.name for p in tmp_path.iterdir() if "perBGC_cctt_resistance" in p.name and p.suffix == ".png"]
    assert pngs, "the S3 cctt+resistance figure was not rendered"
    labels = [l for leg in captured for l in leg]
    assert any("T1" in l and "self-protection" in l for l in labels), \
        "resistance tier strip has no legend defining T1 (strip is undefined on the figure)"
    assert any("T3" in l for l in labels)
    assert any("no source-derived resistance" in l for l in labels)
