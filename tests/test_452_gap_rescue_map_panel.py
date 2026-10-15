"""tools/gap_rescue_locus_map.py panel/key and gap_directed_rescue.py --panel/--no-key (card .452 gap_rescue_map_panel).

A locus map drawn for a multi-panel figure: the footnote leaves the page for the caption, an unnamed reference gene is
labelled by its accession alone, and key=False leaves the colour bar and class legend to one shared key. Without
panel the map is drawn as before. Synthetic data only.
"""
import importlib.util
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


glm = _load(HERE / "tools" / "gap_rescue_locus_map.py", "gap_rescue_locus_map_452p")
gdr = _load(HERE / "tools" / "gap_directed_rescue.py", "gap_directed_rescue_452p")
# a 10-gene reference, unnamed genes with accessions and long products, all matched on one contig
REF = [{"i": i + 1, "name": f"SYN{i:05d}.1", "product": "ABC transporter ATP-binding protein domain-containing",
        "kind": "biosynthetic", "s": i * 1.6, "e": i * 1.6 + 1.4, "strand": 1} for i in range(10)]
REF_LEN = REF[-1]["e"] + 0.5


def _genome():
    prots, rows = {}, []
    for k, g in enumerate(REF):
        start = 40000 + int(g["s"] * 1000)
        prots[f"p{k}"] = {"tag": f"core_{k}", "contig": "core", "start": start,
                          "end": start + int((g["e"] - g["s"]) * 1000), "strand": 1, "contig_len": 200000}
        rows.append({"status": "PRESENT_IN_CORE", "best_protein": f"p{k}",
                     "best_identity_pct": 60.0, "reciprocal_best": True, "partner_verdict": ""})
    core = {"contig": "core", "start": 39000, "end": 58000, "identity": "SYN-970 / core / region001 / BGC001"}
    return prots, rows, core


def _draw(monkeypatch, tmp_path, name, **kw):
    monkeypatch.setattr(glm, "reference_genes", lambda _p: ([dict(g) for g in REF], REF_LEN))
    prots, rows, core = _genome()
    png = tmp_path / f"{name}.png"
    out = glm.draw_locus_map(tmp_path / "BGC0000000.gbk", rows, [], prots, [core], core, "SYN-970", "synthetic",
                             png, print_width="double", **kw)
    return out, Image.open(png).size


def test_short_panel_drops_the_product():
    assert glm.short_panel({"name": "SYN00001.1", "product": "ABC transporter permease"}) == "SYN00001.1"
    assert glm.short({"name": "SYN00001.1", "product": "ABC transporter permease"}) == "SYN00001.1 (ABC transporter permease)"
    assert glm.short_panel({"name": "", "product": "ABC transporter permease"}) == "ABC transporter permease"
    named = {"name": "copA", "product": "NRPS"}
    assert glm.short_panel(named) == glm.short(named)


def test_panel_takes_the_footnote_off_the_page(monkeypatch, tmp_path):
    full, size_full = _draw(monkeypatch, tmp_path, "full")
    panel, size_panel = _draw(monkeypatch, tmp_path, "panel", panel=True)
    assert panel["footnote"] == full["footnote"]          # returned for the caption, word for word
    assert size_panel[1] < size_full[1]                   # shorter: no footnote, short reference labels
    assert panel["min_font_pt"] >= 8 and panel["text_overlaps"] == 0


def test_no_key_is_shorter_still(monkeypatch, tmp_path):
    _, with_key = _draw(monkeypatch, tmp_path, "key", panel=True)
    out, no_key = _draw(monkeypatch, tmp_path, "nokey", panel=True, key=False)
    assert no_key[1] < with_key[1]
    assert out["min_font_pt"] >= 8 and out["text_overlaps"] == 0


def test_panel_needs_a_print_width_and_key_needs_panel(monkeypatch, tmp_path):
    monkeypatch.setattr(glm, "reference_genes", lambda _p: ([dict(g) for g in REF], REF_LEN))
    prots, rows, core = _genome()
    with pytest.raises(ValueError, match="GAP_RESCUE_MAP_PANEL"):
        glm.draw_locus_map(tmp_path / "BGC0000000.gbk", rows, [], prots, [core], core, "SYN-970", "synthetic",
                           tmp_path / "a.png", print_width=None, panel=True)
    with pytest.raises(ValueError, match="GAP_RESCUE_MAP_PANEL"):
        glm.draw_locus_map(tmp_path / "BGC0000000.gbk", rows, [], prots, [core], core, "SYN-970", "synthetic",
                           tmp_path / "b.png", print_width="double", key=False)


def test_cli_refuses_no_key_without_panel_and_panel_without_redraw(tmp_path):
    with pytest.raises(SystemExit, match="add --panel"):
        gdr.main(["--zip", str(tmp_path / "x.zip"), "--label", "SYN-970", "--no-key"])
    with pytest.raises(SystemExit, match="needs --redraw"):
        gdr.main(["--zip", str(tmp_path / "x.zip"), "--label", "SYN-970", "--panel"])
