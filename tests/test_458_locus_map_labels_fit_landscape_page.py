"""tools/gap_rescue_locus_map.py at a print width: the locus-tag stem shared by the gene labels is named once in the title, and an
optional (unmatched-gene) label never lengthens the page.

Bee/Attine AS-846 ansacarbamitocin maps (MIBiG BGC0002011, 60 genes labelled AMYAL_RS0139360 and so on): at landscape width the page came
out 7.3 to 7.7 in tall against a 6.5 in limit, and the held maps could not be placed. Every rotated label repeated the stem AMYAL_, and
the grey unmatched-gene labels (and the long "split piece 1 of 2" labels) set the depth of the page.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tools"))
spec = importlib.util.spec_from_file_location("gap_rescue_locus_map_458", HERE / "tools/gap_rescue_locus_map.py")
glm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(glm)

N = 26
REF = [{"i": i + 1, "name": f"AMYAL_RS{139360 + 5 * i:07d}", "product": "biosynthetic enzyme", "kind": "biosynthetic",
        "s": i * 1.6, "e": i * 1.6 + 1.4, "strand": 1} for i in range(N)]
REF_LEN = REF[-1]["e"] + 0.5


def _genome(long_grey=False):
    prots, rows, names = {}, [], {}
    for k, g in enumerate(REF):
        start = 5000 + int(g["s"] * 1000)
        prots[f"p{k}"] = {"tag": f"core_{k}", "contig": "core", "start": start, "end": start + int((g["e"] - g["s"]) * 1000),
                          "strand": 1, "contig_len": 90000}
        rows.append({"status": "PRESENT_IN_CORE", "best_protein": f"p{k}", "best_identity_pct": 80.0 + k % 15,
                     "reciprocal_best": True, "partner_verdict": ""})
    if long_grey:   # one unmatched gene with a protein-search name, before the first matched gene
        prots["g0"] = {"tag": "grey_0", "contig": "core", "start": 1000, "end": 1900, "strand": 1, "contig_len": 90000}
        names["grey_0"] = {"top10_consensus_name": "SdrD B-like domain-containing protein with a long name", "db": "clustered",
                           "top10_mean_identity": "78", "function_class": "other"}
    core = {"contig": "core", "start": 0, "end": 5000 + int(REF_LEN * 1000) + 1000, "identity": "AS-0 / core / region001 / BGC001"}
    return prots, rows, core, names


@pytest.fixture
def _figs(monkeypatch):
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure
    real_close = plt.close
    figures = []

    def capture_close(fig=None):
        if isinstance(fig, Figure):
            figures.append(fig)
        else:
            real_close(fig)
    monkeypatch.setattr(plt, "close", capture_close)
    yield figures
    for f in figures:
        real_close(f)


def _draw(monkeypatch, tmp_path, tag, long_grey=False, **kw):
    monkeypatch.setattr(glm, "reference_genes", lambda _p: (REF, REF_LEN))
    prots, rows, core, names = _genome(long_grey)
    out = tmp_path / f"m_{tag}.png"
    res = glm.draw_locus_map(tmp_path / "BGC0000000.gbk", rows, [], prots, [core], core, "AS-0", "ansacarbamitocin A", out,
                             gene_names=names, **kw)
    return res, out


def _texts(fig):
    return [t.get_text() for ax in fig.axes for t in ax.texts]


def _png_height_in(path):
    from PIL import Image
    with Image.open(path) as im:
        return im.size[1] / 300.0


def test_shared_tag_prefix_is_found_only_when_most_labels_carry_it():
    tags = [f"AMYAL_RS{i:07d}" for i in range(10)]
    assert glm.shared_tag_prefix(tags + ["Eno", "Eno"]) == "AMYAL_"          # named genes do not stop it
    assert glm.shared_tag_prefix(tags[:7]) == ""                              # too few labels to call a stem
    assert glm.shared_tag_prefix(tags[:8] + [f"XYZ_{i:05d}" for i in range(8)] + [f"QRS_{i:05d}" for i in range(8)]) == ""   # under half share it
    assert glm.shared_tag_prefix([f"AB_{i}" for i in range(10)]) == ""        # stripping would leave under 3 characters
    assert glm.shared_tag_prefix([f"gene{i}" for i in range(12)]) == ""       # no underscore stem at all


def test_at_a_print_width_the_stem_is_dropped_from_the_labels_and_named_in_the_title(monkeypatch, tmp_path, _figs):
    _draw(monkeypatch, tmp_path, "land", print_width="landscape", panel=True)
    texts = _texts(_figs[-1])
    assert not [t for t in texts if t.startswith("AMYAL_")]
    assert any(t.startswith("RS0139360") for t in texts)
    assert any("labels omit AMYAL_" in t for t in texts)


def test_the_screen_layout_is_unchanged(monkeypatch, tmp_path, _figs):
    _draw(monkeypatch, tmp_path, "screen")
    texts = _texts(_figs[-1])
    assert any(t.startswith("AMYAL_RS0139360") for t in texts)
    assert not any("labels omit" in t for t in texts)


def test_dropping_the_stem_makes_the_page_shorter(monkeypatch, tmp_path):
    _, short_png = _draw(monkeypatch, tmp_path, "stem", print_width="landscape", panel=True)
    monkeypatch.setattr(glm, "shared_tag_prefix", lambda *a, **k: "")
    _, full_png = _draw(monkeypatch, tmp_path, "nostem", print_width="landscape", panel=True)
    assert _png_height_in(short_png) < _png_height_in(full_png) - 0.1


def test_an_optional_grey_label_never_lengthens_the_page(monkeypatch, tmp_path):
    _, base_png = _draw(monkeypatch, tmp_path, "plain", print_width="landscape", panel=True)
    res, grey_png = _draw(monkeypatch, tmp_path, "grey", long_grey=True, print_width="landscape", panel=True)
    assert _png_height_in(grey_png) <= _png_height_in(base_png) + 0.01
    assert res["min_font_pt"] >= 8.0


def _panel_page_key_height(tmp_path, width_in):
    from PIL import Image
    import gap_rescue_panel_figure as pf
    png = tmp_path / f"panel_{width_in}.png"
    Image.new("RGB", (2700, 1700), "white").save(png)
    classes = list(glm.CLASS_ORDER[:6])
    fig, H = pf.draw_page([(tmp_path, png, {})], [0], "a", width_in, True, classes, False, gecco=True)
    inside = fig.legends[0].get_window_extent().x1 / fig.dpi <= width_in + 0.01
    return H - 1700 / 300, inside


def test_a_landscape_page_puts_the_identity_and_gecco_bars_side_by_side(tmp_path):
    """The GECCO bar sat under the identity bar and added 0.62 in to every landscape page; at 9 in there is room beside it."""
    key_h, inside = _panel_page_key_height(tmp_path, 9.0)
    assert key_h <= 0.8 and inside


def test_a_narrower_page_keeps_the_stacked_key(tmp_path):
    key_h, inside = _panel_page_key_height(tmp_path, 7.2)
    assert key_h >= 1.2 and inside
