"""D11 distinguishes display offsets from its source integer counts."""
import pytest
from mamey import cohort_figures as figures

@pytest.mark.parametrize("pairs", [[(0, 0), (1, 2), (13, 1)], [(0, 0), (0, 0)]])
@pytest.mark.parametrize("release", ["PUBLIC", "PRIVATE"])
def test_d11_offsets_are_disclosed_and_source_counts_preserved(tmp_path, monkeypatch, pairs, release):
    strain = "Micromonospora-vinacea"
    profiles = [{"bgc_id": f"BGC{i:03d}", "total_domains": 1,
                 "PKS_KS": modules, "NRPS_C": 0, "tta_codons": tta}
                for i, (modules, tta) in enumerate(pairs, 1)]
    records = {strain: {"privacy": {"effective_release": release},
        "ms": {"raw_bgcs": len(pairs), "corrected_bgcs": len(pairs), "assembly_tier": "GOOD"},
        "deep": {"bgc_profile": profiles}}}
    inventory = {strain: [{"BGC_ID": p["bgc_id"], "Contig": "CP192024.1",
        "Region": f"region{i:03d}", "Length_kb": 20, "Products": "", "Boundary": "Interior"}
        for i, p in enumerate(profiles, 1)]}
    monkeypatch.setitem(figures.GENUS, strain, "Micromonospora vinacea")
    monkeypatch.setattr(figures, "_load_inv_d", lambda *_: inventory)
    monkeypatch.setattr(figures, "bubble_matrix", lambda *a, **k: None)
    saved = []
    def sidecar(path, header, rows):
        if "scatter_tta_vs_modularity" in str(path):
            saved.extend(rows)
    monkeypatch.setattr(figures, "sidecar", sidecar)
    seen = []
    def capture(fig, path, **kwargs):
        try:
            if "scatter_tta_vs_modularity" not in str(path):
                return
            ax = fig.axes[0]
            fig.canvas.draw()
            assert "counts are integers" in ax.get_title().lower()
            assert "0.2 per axis" in ax.get_title()
            assert all(float(t).is_integer() for t in [*ax.get_xticks(), *ax.get_yticks()])
            offsets = ax.collections[0].get_offsets()
            assert len(offsets) == len(pairs)
            assert all(abs(float(x) - modules) <= .2 and abs(float(y) - tta) <= .2
                       for (x, y), (modules, tta) in zip(offsets, pairs))
            assert any(float(x) != modules or float(y) != tta
                       for (x, y), (modules, tta) in zip(offsets, pairs))
            seen.append(True)
        finally:
            figures.plt.close(fig)
    monkeypatch.setattr(figures, "_save_pair", capture)
    figures.build(records, [strain], str(tmp_path))
    assert seen
    assert [(r[2], r[3]) for r in saved] == pairs
    assert [r[1] for r in saved] == [p["bgc_id"] for p in profiles]
