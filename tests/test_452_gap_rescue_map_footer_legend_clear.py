"""tools/gap_rescue_locus_map.py footer at print width (card .452 gap_rescue_map_footer_legend_clear).

At 7.2 in the gene-class legend ("Genes not in the reference, by protein-search name") was centred under the map and
its first entry sat on the identity colour bar's "100" tick label. The text-overlap gate tested map texts only, so it
passed. The legend now sits beside the colour bar, clear of the scale bar, and the gate also tests the footer.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tools"))


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


glm = _load(HERE / "tools" / "gap_rescue_locus_map.py", "gap_rescue_locus_map_452f")
CLASSES = ["biosynthetic core", "tailoring", "transport", "regulator", "housekeeping", "other", "hypothetical"]
REF = [{"i": i + 1, "name": f"synA{i}", "product": "biosynthetic enzyme", "kind": "biosynthetic",
        "s": i * 1.6, "e": i * 1.6 + 1.4, "strand": 1} for i in range(12)]
REF_LEN = REF[-1]["e"] + 0.5


def _genome(n_grey, classes):
    prots, rows, names = {}, [], {}
    for k, g in enumerate(REF):
        start = 5000 + int(g["s"] * 1000)
        prots[f"p{k}"] = {"tag": f"core_{k}", "contig": "core", "start": start,
                          "end": start + int((g["e"] - g["s"]) * 1000), "strand": 1, "contig_len": 90000}
        rows.append({"status": "PRESENT_IN_CORE", "best_protein": f"p{k}", "best_identity_pct": 60.0 + 3 * k,
                     "reciprocal_best": True, "partner_verdict": ""})
    for j in range(n_grey):
        start = 26000 + j * 1500
        prots[f"g{j}"] = {"tag": f"grey_{j}", "contig": "core", "start": start, "end": start + 1200, "strand": 1,
                          "contig_len": 90000}
        names[f"grey_{j}"] = {"top10_consensus_name": f"protein {j}", "db": "nr", "top10_mean_identity": "70",
                              "function_class": classes[j % len(classes)]}
    core = {"contig": "core", "start": 4000, "end": 26000 + n_grey * 1500 + 2000,
            "identity": "SYN-970 / core / region001 / BGC001"}
    return prots, rows, core, names


def _draw(monkeypatch, tmp_path, width, n_grey=7, classes=CLASSES):
    monkeypatch.setattr(glm, "reference_genes", lambda _p: (REF, REF_LEN))
    prots, rows, core, names = _genome(n_grey, classes)
    out = tmp_path / f"m_{width}_{n_grey}.png"
    return glm.draw_locus_map(tmp_path / "BGC0000000.gbk", rows, [], prots, [core], core, "SYN-970", "synthetic",
                              out, gene_names=names, print_width=width)


@pytest.mark.parametrize("width", ["double", "single"])
def test_class_legend_clears_the_colour_bar_and_scale_bar(monkeypatch, tmp_path, width):
    res = _draw(monkeypatch, tmp_path, width)
    assert res["text_overlaps"] == 0 and res["min_font_pt"] >= 8.0


def test_one_class_legend_still_clear(monkeypatch, tmp_path):
    res = _draw(monkeypatch, tmp_path, "double", n_grey=2, classes=["tailoring"])
    assert res["text_overlaps"] == 0


def test_the_old_centred_legend_is_now_caught_by_the_gate(monkeypatch, tmp_path):
    def old_place(fig, ax, rend, cax, handles, xmin, xmax, ybar, y0, y1, fig_w, per_in, fs):
        ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(xmin + 0.1, ybar - 0.07),
                  bbox_transform=ax.transData, fontsize=fs(6.5), frameon=False, ncol=4)
        return y0
    monkeypatch.setattr(glm, "place_class_legend", old_place)
    with pytest.raises(ValueError, match="GAP_RESCUE_MAP_TEXT_OVERLAP"):
        _draw(monkeypatch, tmp_path, "double")


def test_footer_overlaps_reports_touching_pieces_only():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    fig, ax = plt.subplots(figsize=(7.2, 3))
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    cax = ax.inset_axes([0.5, 1, 2, 0.4], transform=ax.transData)
    rend = fig.canvas.get_renderer()
    ax.legend(handles=[Patch(label="tailoring")], loc="lower left", bbox_to_anchor=(6, 6), bbox_transform=ax.transData)
    assert glm.footer_overlaps(ax, cax, rend) == []
    ax.legend(handles=[Patch(label="tailoring")], loc="lower left", bbox_to_anchor=(1, 1), bbox_transform=ax.transData)
    assert ("identity colour bar", "gene-class legend") in glm.footer_overlaps(ax, cax, rend)
    plt.close(fig)


def test_screen_layout_keeps_the_centred_legend(monkeypatch, tmp_path):
    res = _draw(monkeypatch, tmp_path, None)
    assert "text_overlaps" not in res   # the print-width gate is not run on the 13.5 in screen layout
