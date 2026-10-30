"""Discrete count scales remain distinct from continuous or fractional values."""
import pytest
from mamey import cohort_figures as figures

@pytest.mark.parametrize("counts", [[0], [1], [2], [5], [1, 5]])
def test_integer_bubble_counts_have_nonnegative_integer_color_ticks(tmp_path, monkeypatch, counts):
    labels = [f"metric-{i}" for i in range(len(counts))]
    observed = []
    def capture(fig, path, **kwargs):
        fig.canvas.draw()
        colorbar = fig.axes[-1]
        assert all(float(t).is_integer() and t >= 0 for t in colorbar.get_yticks())
        scatter = fig.axes[0].collections[0]
        assert scatter.norm.vmin == 0
        assert scatter.norm.vmax == max(1, max(counts))
        observed.append(True)
    monkeypatch.setattr(figures, "_save_pair", capture)
    figures.bubble_matrix(labels, ["software-fixture"],
        lambda row, strain: counts[labels.index(row)], None, "Count view", "count_view",
        str(tmp_path), "BGC count", "BGC count", color_is_count=True)
    assert observed

@pytest.mark.parametrize("count_mode", [False, True])
def test_continuous_and_fractional_values_are_not_forced_to_integer_scales(tmp_path, monkeypatch, count_mode):
    observed = []
    def capture(fig, path, **kwargs):
        scatter = fig.axes[0].collections[0]
        assert float(scatter.get_array()[0]) == (1.5 if count_mode else 12.5)
        assert scatter.norm.vmin > 0
        observed.append(True)
    monkeypatch.setattr(figures, "_save_pair", capture)
    figures.bubble_matrix(["metric"], ["software-fixture"], lambda *_: 1.5,
        lambda *_: 12.5, "Continuous view", "continuous_view", str(tmp_path),
        "metric", "size", color_is_count=count_mode)
    assert observed

@pytest.mark.parametrize("triggers", ["", "T43-A", "T43-A,T43-B"])
def test_single_strain_count_scatter_uses_integer_ticks(tmp_path, monkeypatch, triggers):
    strain = "software-fixture"
    records = {strain: {"privacy": {"effective_release": "PUBLIC"},
        "ms": {"raw_bgcs": 13, "corrected_bgcs": 13, "assembly_tier": "GOOD"},
        "deep": {"bgc_profile": [{"bgc_id": "BGC001", "total_domains": 1,
                                  "cctt_triggers": triggers}]}}}
    inventory = {strain: [{"BGC_ID": "BGC001", "Contig": "fixture_contig.v1",
                           "Region": "region001", "Length_kb": 20,
                           "Products": "", "Boundary": "Interior"}]}
    monkeypatch.setattr(figures, "_load_inv_d", lambda *_: inventory)
    monkeypatch.setattr(figures, "bubble_matrix", lambda *a, **k: None)
    monkeypatch.setattr(figures, "sidecar", lambda *a, **k: None)
    observed = []
    class Finished(Exception): pass
    def capture(fig, path, **kwargs):
        try:
            if "scatter_rarechem_vs_bgcs" in str(path):
                ax = fig.axes[0]
                fig.canvas.draw()
                assert all(float(t).is_integer() for t in [*ax.get_xticks(), *ax.get_yticks()])
                assert list(ax.collections[0].get_offsets()[0]) == [13, len(triggers.split(",")) if triggers else 0]
                observed.append(True)
                raise Finished
        finally:
            figures.plt.close(fig)
    monkeypatch.setattr(figures, "_save_pair", capture)
    with pytest.raises(Finished): figures.build(records, [strain], str(tmp_path))
    assert observed
