"""D06 count labels stay with strain ticks at every score scale."""
import pytest
from mamey import cohort_figures as figures

@pytest.mark.parametrize("score", [1000, 100000000, None])
@pytest.mark.parametrize("release", ["PUBLIC", "PRIVATE"])
def test_d06_counts_do_not_expand_the_canvas(tmp_path, monkeypatch, score, release):
    strain = "Micromonospora-vinacea"
    records = {strain: {"privacy": {"effective_release": release},
        "ms": {"raw_bgcs": 2, "corrected_bgcs": 2, "assembly_tier": "GOOD"},
        "deep": {"bgc_profile": [{"bgc_id": "BGC001", "total_domains": 1},
                                  {"bgc_id": "BGC002", "total_domains": 2}]}}}
    inventory = {strain: [{"BGC_ID": alias, "Contig": "CP192024.1",
        "Region": region, "Length_kb": 20, "Products": "", "Boundary": "Interior",
        "KCB_score": value, "KCB_top": "reference" if value else ""}
        for alias, region, value in [("BGC001", "region001", score),
                                      ("BGC002", "region002", None)]]}
    monkeypatch.setitem(figures.GENUS, strain, "Micromonospora vinacea")
    monkeypatch.setattr(figures, "_load_inv_d", lambda *_: inventory)
    monkeypatch.setattr(figures, "bubble_matrix", lambda *a, **k: None)
    monkeypatch.setattr(figures, "sidecar", lambda *a, **k: None)
    observed = []
    class FinishedD06(Exception):
        pass
    def capture(fig, path, **kwargs):
        if "strip_kcb_per_strain" not in str(path):
            figures.plt.close(fig)
            return
        try:
            ax = fig.axes[0]
            fig.canvas.draw()
            extent = fig.get_tightbbox(fig.canvas.get_renderer())
            assert extent.height < 1.5 * fig.get_figheight(), "annotation expands export canvas"
            renderer = fig.canvas.get_renderer()
            assert all(not tick.get_window_extent(renderer).overlaps(stamp.get_window_extent(renderer))
                       for tick in ax.get_xticklabels() for stamp in fig.texts), "count label touches figure stamp"
            expected = 1 if score else 2
            assert any(f"{expected} no-hit" in t.get_text() for t in ax.get_xticklabels())
            assert not any("no-hit" in t.get_text() for t in ax.texts)
            assert ax.get_yscale() == ("log" if score else "linear")
            points = ax.collections[0].get_offsets()
            assert list(points[:, 1]) == ([score] if score else [])
            observed.append(True)
        finally:
            figures.plt.close(fig)
        raise FinishedD06
    monkeypatch.setattr(figures, "_save_pair", capture)
    with pytest.raises(FinishedD06):
        figures.build(records, [strain], str(tmp_path))
    assert observed
