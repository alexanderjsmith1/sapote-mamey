"""Re-audit of .456, F03 and F21 (pcoa_stack v4).

F03: a TriMap or t-SNE grid page admits its coordinates through embedding_coordinates(), the same strict join the single-panel
layout uses, so a repeated id in the embedding table is refused before any drawing (it used to overwrite silently).
F21: a grid caption reports the high tier from the panel's n_high and discloses proteins with unavailable identity; unknown identity is
never counted as high. Synthetic data only (the multiset-grid test kit)."""
import importlib.util, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("grid_test", ROOT / "tests" / "test_m5_452_protein_pcoa_multiset_grid.py")
g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)


def test_grid_refuses_a_repeated_embedding_id(tmp_path, monkeypatch):
    root = g.five_set_kit(tmp_path)
    table = root / "trimap.tsv"
    first_query = next(line for line in table.read_text().splitlines() if line.startswith("i0\t"))
    with open(table, "a") as fh:
        fh.write("i0\t99\t88\n")          # the re-audit fixture: a complete table plus a second i0 row
    assert first_query.split("\t")[1:] != ["99", "88"]
    drawn = []
    monkeypatch.setattr(g.base.ppr, "build_grid_page", lambda *a, **k: drawn.append(True) or {})
    extra = ["--page", "trimap", "--page-grid", "2x2"]
    for s in g.SETS:
        extra += ["--embedding-table", f"{s}={table}"]
    assert g.grid(root, *extra) == 2
    assert not drawn


def _panel(**counts):
    p = dict(letter="a", title="KS", cohort_genomes={"SYN-901": 1}, n_ref_centroids=3, n_ref=5, n_reference_genomes=2,
             n_mibig_centroids=1, n_mibig=1, labels=dict(labelled=0, outlier_groups=0), n_low=0, n_mid=0)
    p.update(counts)
    return p


def _caption(panel):
    from tools import protein_pcoa_page_docs as docs
    rec = dict(legend={"iso_low": "query genome proteins, x"}, label_below=50.0, mid_below=70.0, page=["trimap"], panels=[panel],
               label_mode="outlier", prefix="PAGE_GRID_test")
    return docs.grid_caption_text(rec, [], {}, None)


def test_grid_caption_never_counts_unknown_identity_as_high():
    text = _caption(_panel(n_cohort_points=1, n_high=0, n_unknown=1))
    assert "tiers 0 / 0 / 0" in text and "tiers 0 / 0 / 1" not in text
    assert "identity unavailable for 1" in text and "Open diamonds show" in text


def test_grid_caption_without_unknowns_is_unchanged():
    text = _caption(_panel(n_cohort_points=3, n_low=1, n_mid=1, n_high=1, n_unknown=0))
    assert "tiers 1 / 1 / 1" in text and "identity unavailable" not in text and "Open diamonds" not in text


def test_older_panel_records_without_n_high_still_subtract_unknowns():
    text = _caption(_panel(n_cohort_points=4, n_low=1, n_mid=1, n_unknown=1))
    assert "tiers 1 / 1 / 1" in text and "identity unavailable for 1" in text
