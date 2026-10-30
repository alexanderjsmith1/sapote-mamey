"""The D03 legend preserves the strain name without a taxonomy-derived prefix."""
import pytest
from mamey import cohort_figures as figures

@pytest.mark.parametrize("taxonomy", ["not supplied", "", "Micromonospora vinacea"])
@pytest.mark.parametrize("release", ["PUBLIC", "PRIVATE"])
def test_d03_legend_uses_exact_strain_identity(tmp_path, monkeypatch, taxonomy, release):
    strain = "Micromonospora-vinacea"
    records = {strain: {"privacy": {"effective_release": release},
                       "deep": {"bgc_profile": [{"bgc_id": "BGC005", "total_domains": 13}]}}}
    inventory = {strain: [{"BGC_ID": "BGC005", "Contig": "CP192024.1",
                           "Region": "region005", "Length_kb": 42, "Products": ""}]}
    monkeypatch.setitem(figures.GENUS, strain, taxonomy)
    monkeypatch.setattr(figures, "_load_inv_d", lambda *_: inventory)
    monkeypatch.setattr(figures, "bubble_matrix", lambda *a, **k: None)
    observed = []
    class FinishedD03(Exception):
        pass
    def capture(fig, path, **kwargs):
        assert "scatter_size_vs_domains" in str(path)
        labels = fig.axes[0].get_legend_handles_labels()[1]
        observed.extend(labels)
        figures.plt.close(fig)
        raise FinishedD03
    monkeypatch.setattr(figures, "_save_pair", capture)
    with pytest.raises(FinishedD03):
        figures.build(records, [strain], str(tmp_path))
    assert observed == [strain + (" (PRIV)" if release == "PRIVATE" else "")]
