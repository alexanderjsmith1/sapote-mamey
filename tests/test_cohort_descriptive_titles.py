"""Schema-only figure cases: labels describe the view, not an uncomputed trend."""
import pytest
from mamey import cohort_figures as figures

@pytest.mark.parametrize("target", ["scatter_kcb_vs_size", "scatter_rarechem_vs_bgcs"])
@pytest.mark.parametrize("n", [1, 2])
def test_scatter_titles_describe_quantities_without_an_uncomputed_trend(tmp_path, monkeypatch, target, n):
    names = [f"software-fixture-{i}" for i in range(n)]
    records = {s: {"privacy": {"effective_release": "PUBLIC"},
        "ms": {"raw_bgcs": 1, "corrected_bgcs": 1, "assembly_tier": "GOOD"},
        "deep": {"bgc_profile": [{"bgc_id": "BGC001", "total_domains": 1}]}} for s in names}
    inventory = {s: [{"BGC_ID": "BGC001", "Length_kb": 20, "Products": "",
        "KCB_score": 1000, "KCB_top": "reference", "Boundary": "Interior"}] for s in names}
    monkeypatch.setattr(figures, "_load_inv_d", lambda *_: inventory)
    monkeypatch.setattr(figures, "bubble_matrix", lambda *a, **k: None)
    monkeypatch.setattr(figures, "sidecar", lambda *a, **k: None)
    seen = []
    class Finished(Exception): pass
    def capture(fig, path, **kwargs):
        try:
            if target in str(path):
                title = fig.axes[0].get_title().lower()
                assert "trend" not in title and "punch" not in title
                assert "bgc" in title
                seen.append(True)
                raise Finished
        finally:
            figures.plt.close(fig)
    monkeypatch.setattr(figures, "_save_pair", capture)
    with pytest.raises(Finished): figures.build(records, names, str(tmp_path))
    assert seen

@pytest.mark.parametrize("n", [1, 2, 5])
def test_product_class_title_matches_the_actual_roster(tmp_path, monkeypatch, n):
    names = [f"software-fixture-{i}" for i in range(n)]
    records = {s: {"deep": {"bgc_profile": []}} for s in names}
    inventory = {s: [{"Products": "NRPS"}] for s in names}
    inventory[names[0]].append({"Products": "terpene"})
    monkeypatch.setattr(figures, "_load_inv_g", lambda *_: inventory)
    observed = []
    class Finished(Exception): pass
    def hmap(matrix, labels, order, title, fid, out, **kwargs):
        if fid != "rare_product_classes": return
        assert "rare" not in title.lower()
        if n == 1:
            assert "one strain" in title
        else:
            assert f"≤{min(4,n)} of {n} strains" in title
        expected = {"NRPS", "terpene"} if n <= 4 else {"terpene"}
        assert set(kwargs["row_raw"]) == expected
        data = dict(zip(kwargs["row_raw"], matrix))
        assert data["terpene"] == [1] + [0] * (n-1)
        observed.append(True)
        raise Finished
    monkeypatch.setattr(figures, "hmap", hmap)
    with pytest.raises(Finished): figures.batch1(records, names, str(tmp_path))
    assert observed

@pytest.mark.parametrize("key, forbidden", [
    ("scatter_kcb_vs_size", "trend"),
    ("scatter_rarechem_vs_bgcs", "trend"),
    ("rare_product_classes", "unusual chemistry"),
])
def test_written_captions_do_not_restore_unsupported_claims(tmp_path, key, forbidden):
    filename = {"scatter_kcb_vs_size": "D04", "scatter_rarechem_vs_bgcs": "D07",
                "rare_product_classes": "G02"}[key] + "_" + key + ".png"
    path = figures.write_captions(str(tmp_path), [filename])
    caption = next(line for line in open(path) if line.startswith("**"))
    assert forbidden not in caption.lower()
