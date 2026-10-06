"""Region slides carry the BGC's own reference structure beside the map (4 Oct), and PCoA panels label each protein
once, clear of the stars."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import strain_slides as ss  # noqa: E402

PIL = pytest.importorskip("PIL.Image")


def _binding(alias, contig, rank, frac):
    return {"bgc_alias": alias, "full_contig": contig, "region": "region001", "kcb_rank": str(rank),
            "reference_match_metrics": {"state": "REFERENCE_MATCH_METRICS_BOUND", "query_genes_matched_fraction": frac,
                                        "matched_query_genes": 4, "query_gene_denominator": 10,
                                        "median_best_hit_identity_percent": 70.0}}


def _assets(tmp_path):
    cs = tmp_path / "assets" / "chemical_structures"
    (cs / "structures").mkdir(parents=True)
    for n in ("a", "b"):
        im = PIL.new("RGB", (400, 400), "white")
        im.paste((0, 0, 0), (180, 180, 220, 220))  # a small drawing in a wide white margin
        im.save(cs / "structures" / f"{n}.png")
    entries = [
        {"mibig_accession": "BGC0000001", "representative_name": "second", "drawing_available": True,
         "representative_png": "structures/a.png", "locus_bindings": [_binding("BGC001", "NODE_1_length_9_cov_1.0", 2, 0.9)]},
        {"mibig_accession": "BGC0000002", "representative_name": "first", "drawing_available": True,
         "representative_png": "structures/b.png", "locus_bindings": [_binding("BGC001", "NODE_1_length_9_cov_1.0", 1, 0.2),
                                                                      _binding("BGC002", "NODE_2_length_9_cov_1.0", 1, 0.5)]},
        {"mibig_accession": "BGC0000003", "representative_name": "undrawn", "drawing_available": False,
         "locus_bindings": [_binding("BGC003", "NODE_3_length_9_cov_1.0", 1, 0.9)]},
    ]
    (cs / "STRUCTURE_ASSETS.json").write_text(json.dumps({"strain": "AS-XXX", "entries": entries}))
    return tmp_path / "assets"


def test_the_best_ranked_drawn_reference_bound_to_this_exact_locus_is_chosen(tmp_path):
    D = {"strain": "AS-XXX", "src": {}}
    a = _assets(tmp_path)
    e, b, png = ss.region_structure(D, a, "BGC001", "NODE_1_length_9_cov_1.0")
    assert e["representative_name"] == "first" and b["kcb_rank"] == "1"  # rank wins over a larger matched fraction
    assert ss.region_structure(D, a, "BGC001", "NODE_9_length_9_cov_1.0") is None  # same alias, other contig: no
    assert ss.region_structure(D, a, "BGC003", "NODE_3_length_9_cov_1.0") is None  # undrawn reference: no box


def test_another_strains_assets_give_no_structure(tmp_path):
    a = _assets(tmp_path)
    assert ss.region_structure({"strain": "AS-YYY", "src": {}}, a, "BGC001", "NODE_1_length_9_cov_1.0") is None


def test_trimming_cuts_the_white_margin(tmp_path):
    a = _assets(tmp_path)
    out = ss.trimmed(a / "chemical_structures" / "structures" / "a.png", tmp_path / "crops")
    w, h = PIL.open(out).size
    assert w < 60 and h < 60  # 40 px of drawing plus a 4% margin, from a 400 px canvas


def test_pcoa_labels_avoid_stars_and_each_other():
    mpl = pytest.importorskip("matplotlib")
    mpl.use("Agg")
    import matplotlib.pyplot as plt
    import strain_slides_pcoa as spc
    fig, ax = plt.subplots(figsize=(3, 3), dpi=100)
    ax.set_xlim(0, 1), ax.set_ylim(0, 1)
    stars = [(0.5, 0.5), (0.52, 0.5), (0.5, 0.52)]
    left = spc.place_labels(ax, [stars[0]], ["ctg1_1 ×3"], avoid=stars)
    assert left == 0
    ann = [c for c in ax.get_children() if c.__class__.__name__ == "Annotation"]
    assert len(ann) == 1 and ann[0].get_text() == "ctg1_1 ×3"
    plt.close(fig)


def test_label_boxes_clear_the_drawn_star_size():
    mpl = pytest.importorskip("matplotlib")
    mpl.use("Agg")
    import matplotlib.pyplot as plt
    import strain_slides_pcoa as spc
    fig, ax = plt.subplots(figsize=(3, 3), dpi=100)
    ax.set_xlim(0, 1), ax.set_ylim(0, 1)
    stars = [(0.3, 0.5), (0.34, 0.49), (0.38, 0.5), (0.42, 0.48)]  # a tight row of full-size stars
    r = 320 ** 0.5 / 2 + 1
    assert spc.place_labels(ax, [stars[0]], ["ctg21_7 ×6"], avoid=stars, star_r=r) == 0
    fig.canvas.draw()
    box = [c for c in ax.get_children() if c.__class__.__name__ == "Annotation"][0].get_window_extent()
    rp = r * fig.dpi / 72
    for s in stars:
        sx, sy = ax.transData.transform(s)
        assert box.x1 <= sx - rp or box.x0 >= sx + rp or box.y1 <= sy - rp or box.y0 >= sy + rp
    plt.close(fig)
