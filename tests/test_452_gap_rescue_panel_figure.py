"""tools/gap_rescue_panel_figure.py and the key file of a panel redraw (card .452 gap_rescue_panel_figure).

Locus maps drawn as figure panels are stacked into one figure with one shared key. The key classes are read from the
maps (gap_rescue_key.json, written by gap_directed_rescue.py --redraw --panel), never from a hand list. A page taller
than the limit and a map wider than the print width are refused, never scaled. Synthetic data only.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
from PIL import Image  # noqa: E402

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tools"))


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


glm = _load(HERE / "tools" / "gap_rescue_locus_map.py", "gap_rescue_locus_map_452f")
gdr = _load(HERE / "tools" / "gap_directed_rescue.py", "gap_directed_rescue_452f")
gpf = _load(HERE / "tools" / "gap_rescue_panel_figure.py", "gap_rescue_panel_figure_452f")


def _map(root, name, classes, unclear=False, w_in=7.0, h_in=3.0):
    d = root / name
    d.mkdir(parents=True)
    Image.new("RGB", (int(w_in * 300), int(h_in * 300)), "white").save(d / "gap_rescue.png", dpi=(300, 300))
    (d / "gap_rescue_key.json").write_text(json.dumps({"classes": classes, "class_unclear": unclear, "key": False}))
    return d


def test_key_classes_follow_the_map_legend_rule():
    named = {"p1": {"function_class": "regulator"}, "p2": {"function_class": "tailoring", "function_class_ambiguous": "yes"},
             "p3": None, "p4": {"function_class": "regulator"}}
    assert glm.key_classes(named) == (["tailoring", "regulator"], True)   # CLASS_ORDER, not the order seen
    assert glm.key_classes({}) == ([], False)
    assert glm.IDENTITY_RANGE == (30, 100) and len(glm.IDENTITY_RAMP) == 2


def test_panel_redraw_writes_the_key_file(monkeypatch, tmp_path):
    folder = tmp_path / "SYN-970_BGC001_synthetic"
    folder.mkdir()
    (folder / "gap_rescue_receipt.json").write_text(json.dumps(
        {"core": "SYN-970 / core / region001 / BGC001", "reference": "BGC0000000.gbk", "reference_name": "synthetic"}))
    (folder / "gap_rescue.tsv").write_text("reference_gene\tstatus\n1\tPRESENT_IN_CORE\n")
    (folder / "gap_rescue_split_genes.tsv").write_text("reference_gene\tsplit_call\n")
    seen = {}

    def fake_draw(*a, **kw):
        seen.update(kw)
        return {"footnote": "Synthetic note.", "key_classes": ["tailoring", "other"], "key_class_unclear": True}

    monkeypatch.setattr(gdr, "draw_locus_map", fake_draw)
    monkeypatch.setattr(gdr, "apply_adjudication", lambda rows, _f: rows)
    regions = [{"identity": "SYN-970 / core / region001 / BGC001", "contig": "core", "start": 1, "end": 2}]
    out = tmp_path / "panel"
    gdr.redraw(folder, {}, regions, "SYN-970", tmp_path, out=out, panel=True, key=False)
    assert seen["panel"] is True and seen["key"] is False
    assert json.loads((out / "gap_rescue_key.json").read_text()) == {
        "classes": ["tailoring", "other"], "class_unclear": True, "key": False}
    assert (out / "gap_rescue_footnote.txt").read_text() == "Synthetic note.\n"
    gdr.redraw(folder, {}, regions, "SYN-970", tmp_path, out=tmp_path / "full")   # no panel: no key file
    assert not (tmp_path / "full" / "gap_rescue_key.json").exists()


def test_compose_takes_the_union_of_the_map_classes(tmp_path):
    a = _map(tmp_path, "a", ["other", "tailoring"])
    b = _map(tmp_path, "b", ["regulator"], unclear=True)
    c = _map(tmp_path, "c", [])
    info = gpf.compose([a, b, c], tmp_path / "out" / "SYN_fig", pages="ab,c")
    assert info["key_classes"] == ["tailoring", "regulator", "other"] and info["key_class_unclear"] is True
    assert [p["letters"] for p in info["pages"]] == ["ab", "c"]
    for p in info["pages"]:
        im = Image.open(p["png"])
        assert im.width == round(7.2 * 300)                       # the page is exactly the print width
        assert im.info.get("Software", "").startswith("Sapote-Mamey")
    # a two-map page: 2 x 3.0 in + one gap; the last page also carries the key
    assert info["pages"][0]["height_in"] == pytest.approx(6.0 + gpf.GAP_IN, abs=0.01)
    assert info["pages"][1]["height_in"] == pytest.approx(3.0 + gpf.key_height(4), abs=0.01)
    assert (tmp_path / "out" / "SYN_fig.pdf").is_file()
    run = json.loads((tmp_path / "out" / "SYN_fig_RUN_INFO.json").read_text())
    assert [p["letter"] for p in run["panels"]] == ["a", "b", "c"] and len(run["panels"][0]["map_sha256"]) == 64
    with pytest.raises(gpf.PanelFigureError, match="exists"):
        gpf.compose([a, b, c], tmp_path / "out" / "SYN_fig", pages="ab,c")


def test_refusals_never_scale(tmp_path):
    tall = [_map(tmp_path, f"t{i}", ["other"], h_in=4.0) for i in range(3)]
    with pytest.raises(gpf.PanelFigureError, match="over the 10.0 in limit"):
        gpf.compose(tall, tmp_path / "o1")                         # 12 in + key on one page
    info = gpf.compose(tall, tmp_path / "o2", pages="ab,c", overview=True)   # split: allowed; overview is not a page
    assert max(p["height_in"] for p in info["pages"]) <= 10.0 and info["overview_height_in"] > 10.0
    wide = _map(tmp_path, "wide", ["other"], w_in=7.6)
    with pytest.raises(gpf.PanelFigureError, match="wider than the 7.2 in print width"):
        gpf.compose([wide], tmp_path / "o3")
    nokey = tmp_path / "nokey"
    nokey.mkdir()
    Image.new("RGB", (300, 300), "white").save(nokey / "gap_rescue.png")
    with pytest.raises(gpf.PanelFigureError, match="no gap_rescue_key.json"):
        gpf.compose([nokey], tmp_path / "o4")
    with pytest.raises(gpf.PanelFigureError, match="once each, in order"):
        gpf.compose(tall, tmp_path / "o5", pages="ba,c")
    with pytest.raises(gpf.PanelFigureError, match="CLASS_ORDER"):
        gpf.compose([_map(tmp_path, "odd", ["not a class"])], tmp_path / "o6")


def test_cli(tmp_path):
    a = _map(tmp_path, "a", ["tailoring"])
    gpf.main(["--maps", str(a), "--out", str(tmp_path / "cli" / "SYN")])
    assert (tmp_path / "cli" / "SYN.png").is_file()
    with pytest.raises(SystemExit, match="GAP_RESCUE_PANEL_FIGURE"):
        gpf.main(["--maps", str(a), "--out", str(tmp_path / "cli" / "SYN")])


def test_page_width_holds_under_a_global_tight_save(tmp_path):
    """Another bundle module can leave savefig.bbox = tight (pad 0.35 in) set for the whole process; the page must
    still be exactly the print width (found in a combined test run: 7.7 in instead of 7.2)."""
    import matplotlib
    a = _map(tmp_path, "a", ["other"])
    with matplotlib.rc_context({"savefig.bbox": "tight", "savefig.pad_inches": 0.35}):
        info = gpf.compose([a], tmp_path / "tight" / "SYN_fig")
    assert Image.open(info["pages"][0]["png"]).width == round(7.2 * 300)
