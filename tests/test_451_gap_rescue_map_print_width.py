"""Synthetic print-width regression: every plot label is at least 8 pt at 3.5 or 7.2 in,
without touching labels. print_width=None preserves the legacy layout.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
HERE = Path(__file__).resolve().parents[1]
TOOLS = HERE / "tools" if (HERE / "tools" / "gap_rescue_locus_map.py").exists() else HERE / "src" / "tools"
sys.path.insert(0, str(TOOLS))
STAGE_TOOLS = HERE.parent / "STAGE_451" / "src_451" / "tools"   # card folder only: the unedited sibling modules
if TOOLS.name == "tools" and TOOLS.parent.name == "src" and STAGE_TOOLS.exists():
    sys.path.append(str(STAGE_TOOLS)); sys.path.append(str(STAGE_TOOLS.parent))


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


glm = _load(TOOLS / "gap_rescue_locus_map.py", "gap_rescue_locus_map_451p")

# a two-row map: 14 reference genes, all matched on the core contig
REF = [{"i": i + 1, "name": f"madA{i}", "product": "biosynthetic enzyme", "kind": "biosynthetic",
        "s": i * 1.6, "e": i * 1.6 + 1.4, "strand": 1} for i in range(14)]
REF_LEN = REF[-1]["e"] + 0.5


def _genome(n_grey=0, grey_class="other"):
    prots, rows, names = {}, [], {}
    for k, g in enumerate(REF):
        start = 5000 + int(g["s"] * 1000)
        prots[f"p{k}"] = {"tag": f"core_{k}", "contig": "core", "start": start,
                          "end": start + int((g["e"] - g["s"]) * 1000), "strand": 1, "contig_len": 90000}
        rows.append({"status": "PRESENT_IN_CORE", "best_protein": f"p{k}", "best_identity_pct": 80.0 + k,
                     "reciprocal_best": True, "partner_verdict": ""})
    # crowded stretch of unmatched genes, each 0.35 kb, every one with a protein-search name
    for j in range(n_grey):
        start = 30000 + j * 400
        tag = f"grey_{j}"
        prots[f"g{j}"] = {"tag": tag, "contig": "core", "start": start, "end": start + 350, "strand": 1 if j % 2 else -1,
                          "contig_len": 90000}
        names[tag] = {"top10_consensus_name": f"hypothetical transporter family protein {j}", "db": "nr",
                      "top10_mean_identity": "71", "function_class": grey_class if j % 3 else "biosynthetic core"}
    core = {"contig": "core", "start": 4000, "end": 30000 + max(n_grey, 1) * 400 + 2000,
            "identity": "AS-0 / core / region001 / BGC001"}
    return prots, rows, core, names


def _draw(monkeypatch, tmp_path, mod=glm, n_grey=0, **kw):
    monkeypatch.setattr(mod, "reference_genes", lambda _p: (REF, REF_LEN))
    prots, rows, core, names = _genome(n_grey)
    out = tmp_path / f"m_{kw.get('print_width')}_{n_grey}.png"
    res = mod.draw_locus_map(tmp_path / "BGC0000000.gbk", rows, [], prots, [core], core, "AS-0", "madurastatin", out,
                             gene_names=names, **kw)
    return res, out


def _png_width_in(path):
    from PIL import Image
    with Image.open(path) as im:
        return im.size[0] / 300.0


@pytest.mark.parametrize("width,inches", [("double", 7.2), ("single", 3.5)])
def test_a_two_row_map_at_print_width_has_no_text_under_8_pt(monkeypatch, tmp_path, width, inches):
    res, out = _draw(monkeypatch, tmp_path, print_width=width)
    assert res["print_width_in"] == inches
    assert res["min_font_pt"] >= 8.0
    assert res["text_overlaps"] == 0
    assert _png_width_in(out) <= inches + 0.02   # never wider than the column, so nothing shrinks on the page


def test_a_crowded_row_keeps_matched_labels_drops_the_overflow_and_counts_it(monkeypatch, tmp_path):
    res, _ = _draw(monkeypatch, tmp_path, n_grey=60, print_width="double")
    assert res["text_overlaps"] == 0
    assert res["min_font_pt"] >= 8.0
    assert res["labels_omitted"]["strain"] > 0          # 60 names cannot fit 24 kb at 8 pt
    assert "not printed for space" in res["footnote"] and "gene table lists every gene" in res["footnote"]
    assert len(res["blastp_named"]) == 60                # every gene is still drawn and filled; only names are left off


def test_the_screen_layout_is_unchanged_when_print_width_is_none(monkeypatch, tmp_path):
    res, out = _draw(monkeypatch, tmp_path, n_grey=10)
    assert "print_width_in" not in res                    # no print gate on the old layout
    assert _png_width_in(out) > 9                         # still the 13.5 in screen canvas
    orig = HERE / "orig" / "tools" / "gap_rescue_locus_map.py"
    if not orig.exists():
        pytest.skip("pixel comparison runs in the card folder, where the pre-card copy is kept")
    old = _load(orig, "gap_rescue_locus_map_pre451")
    old_dir = tmp_path / "old"
    old_dir.mkdir()
    res_old, out_old = _draw(monkeypatch, old_dir, mod=old, n_grey=10)
    from PIL import Image, ImageChops
    with Image.open(out) as a, Image.open(out_old) as b:
        assert a.size == b.size
        assert ImageChops.difference(a.convert("RGB"), b.convert("RGB")).getbbox() is None
    assert res_old["footnote"] == res["footnote"]


def test_fill_label_gaps_keeps_spacing_and_drift():
    placed, dropped = glm.fill_label_gaps([0.0, 1.0], [(0.5, "a"), (3.0, "b"), (0.2, "c"), (0.5, "d")], min_dx=0.4,
                                          drift=0.8)
    xs = sorted([0.0, 1.0] + [x for x, _, _ in placed])
    assert all(b - a >= 0.4 - 1e-9 for a, b in zip(xs, xs[1:]))
    assert all(abs(x - mid) <= 0.8 + 1e-9 for x, mid, _ in placed)
    assert {k for _, _, k in placed} | set(dropped) == {"a", "b", "c", "d"}
    assert dropped == ["d"]   # "a" took the only slot near 0.5; "c" moved left of 0; "d" has nowhere within its drift


def test_text_overlaps_finds_touching_rotated_labels_and_labels_on_a_gene_row():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(4, 3)); ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    ax.text(5, 5, "a long rotated label", rotation=60, rotation_mode="anchor", fontsize=8)
    ax.text(5.05, 5, "another rotated label", rotation=60, rotation_mode="anchor", fontsize=8)
    ax.text(1, 9, "far away", fontsize=8)
    fig.canvas.draw(); rend = fig.canvas.get_renderer()
    hits = glm.text_overlaps(ax, rend)
    assert ("a long rotated label", "another rotated label") in hits
    assert not any("far away" in h for pair in hits for h in pair)
    (x0, y0), (x1, y1) = ax.transData.transform([(0, 8.8), (10, 9.4)])
    assert ("far away", "gene row") in glm.text_overlaps(ax, rend, [(x0, y0, x1, y1)])
    plt.close(fig)


def test_cli_print_width_reaches_the_renderer(monkeypatch, tmp_path):
    gdr = _load(TOOLS / "gap_directed_rescue.py", "gap_directed_rescue_451p")
    seen = []
    monkeypatch.setattr(gdr, "load_genome", lambda *_a, **_k: ({}, []))
    monkeypatch.setattr(gdr, "assert_output_outside_bundle", lambda *_a, **_k: None)
    monkeypatch.setattr(gdr, "redraw", lambda *a, **k: seen.append(a[10] if len(a) >= 11 else k.get("print_width")))
    base = ["--zip", str(tmp_path / "x.zip"), "--label", "L", "--redraw", str(tmp_path), "--mibig-dir", str(tmp_path)]
    gdr.main(base)
    gdr.main(base + ["--print-width", "none"])
    gdr.main(base + ["--print-width", "single"])
    assert seen == ["double", None, "single"]


# The shape of the Saccharothrix coeruleofusca JCM 3313 / BMRG01000004.1 / region001 / BGC011 map (Codex, 12 Oct): two
# sequence records, 35 reference CDS all matched, a long row label. Matched labels pushed right one by one ran 1.9 in
# past a 7.2 in page and the fit refused; centred runs fit.
REF35 = [{"i": i + 1, "name": f"Ctg3_{i + 1}", "product": "biosynthetic enzyme", "kind": "biosynthetic",
          "s": i * 1.9, "e": i * 1.9 + 1.7, "strand": 1} for i in range(35)]
REF35_LEN = REF35[-1]["e"] + 0.5
LONG_LABEL = "Saccharothrix_coeruleofusca_JCM_3313"


def _two_records():
    prots, rows = {}, []
    for k, g in enumerate(REF35):
        contig, base = ("BMRG01000004.1", 8000) if k >= 12 else ("BMRG01000018.1", 3000)
        start = base + int(g["s"] * 1000) - (0 if k < 12 else int(REF35[12]["s"] * 1000))
        prots[f"p{k}"] = {"tag": f"t{k}", "contig": contig, "start": start, "end": start + 1700, "strand": 1,
                          "contig_len": 120000 if k >= 12 else 40000}
        rows.append({"status": "PRESENT_IN_CORE" if k >= 12 else "MISSING_FOUND_CLEAR", "best_protein": f"p{k}",
                     "best_identity_pct": 45.0 + (k * 7) % 40, "reciprocal_best": True, "partner_verdict": ""})
    core = {"contig": "BMRG01000004.1", "start": 7000, "end": 8000 + int((REF35[-1]["e"] - REF35[12]["s"]) * 1000) + 1000,
            "identity": f"{LONG_LABEL} / BMRG01000004.1 / region001 / BGC011"}
    return prots, rows, core


def _draw35(monkeypatch, tmp_path, width, label=LONG_LABEL):
    monkeypatch.setattr(glm, "reference_genes", lambda _p: (REF35, REF35_LEN))
    prots, rows, core = _two_records()
    out = tmp_path / f"m35_{width}.png"
    return glm.draw_locus_map(tmp_path / "BGC0001853.gbk", rows, [], prots, [core], core, label, "largimycin", out,
                              print_width=width), out


def test_a_two_record_map_with_35_matched_genes_and_a_long_label_fits_double_width(monkeypatch, tmp_path):
    res, out = _draw35(monkeypatch, tmp_path, "double")
    assert len(res["contigs_drawn"]) == 2
    assert res["min_font_pt"] >= 8.0 and res["text_overlaps"] == 0
    assert _png_width_in(out) <= 7.2 + 0.02


def test_shrink_steps_run_in_order_before_the_map_is_refused(monkeypatch, tmp_path):
    # 35 matched labels at 8 pt cannot share 3.5 in: every shrink step is tried, then the map is refused, unwritten
    with pytest.raises(ValueError, match="after every shrink step"):
        _draw35(monkeypatch, tmp_path, "single")
    assert not (tmp_path / "m35_single.png").exists()
    # a small locus whose only problem is a very long row label fits at the gutter step (3)
    monkeypatch.setattr(glm, "reference_genes", lambda _p: (REF, REF_LEN))
    prots, rows, core, names = _genome(0)
    res = glm.draw_locus_map(tmp_path / "BGC0000000.gbk", rows, [], prots, [core], core,
                             "Saccharothrix_coeruleofusca_JCM_3313_extra_long_deposited_strain_name", "madurastatin",
                             tmp_path / "long.png", print_width="single")
    assert res["shrink_level"] <= 3 and res["min_font_pt"] >= 8.0 and res["text_overlaps"] == 0


def test_spread_labels_centres_a_crowded_run_and_keeps_spacing():
    xs = glm.spread_labels([5.0, 5.0, 5.0, 5.0], 1.0)
    assert xs == pytest.approx([3.5, 4.5, 5.5, 6.5])          # centred on the genes, not pushed right from 5.0
    xs = glm.spread_labels([0.0, 0.1, 9.9, 10.0], 1.0, lo=0.0, hi=10.0)
    assert xs[0] >= 0.0 and xs[-1] <= 10.0 and all(b - a >= 1.0 - 1e-9 for a, b in zip(xs, xs[1:]))


@pytest.fixture
def _inspected_figures(monkeypatch):
    """Keep inspected figures alive only through this test's assertions."""
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure
    from matplotlib._pylab_helpers import Gcf
    real_close = plt.close
    existing = set(Gcf.get_all_fig_managers())
    existing_figures = {manager.canvas.figure for manager in existing}
    figures = []

    def capture_close(fig=None):
        if isinstance(fig, Figure) and fig not in existing_figures:
            figures.append(fig)
        else:
            real_close(fig)

    try:
        with monkeypatch.context() as patch:
            patch.setattr(plt, "close", capture_close)
            yield figures
    finally:
        owned = set(figures)
        owned.update(manager.canvas.figure for manager in Gcf.get_all_fig_managers()
                     if manager not in existing and manager.canvas.figure not in existing_figures)
        for fig in owned:
            real_close(fig)


def _drawn_texts(fn, figs):
    res = fn()
    fig = [f for f in figs if f is not None][-1]
    return res, [t.get_text() for a in fig.axes for t in a.texts]


def test_no_drawn_label_ends_in_an_underscore_and_names_stay_whole(monkeypatch, tmp_path, _inspected_figures):
    # Integrator 12 Oct read "Ctg3_" and "Ctg3_ 18" on the Saccharothrix map: the strings are whole (Ctg3_18,
    # "Ctg3_18-like 58%"); Arial's underscore at 60 degrees only looks like a break. This pins the strings.
    res, texts = _drawn_texts(lambda: _draw35(monkeypatch, tmp_path, "double")[0], _inspected_figures)
    labels = [t for t in texts if t.startswith("Ctg3")]
    assert labels and not any(t.rstrip().endswith("_") for t in labels)
    assert "Ctg3_18" in labels and any(t.startswith("Ctg3_18-like ") for t in labels)


def test_row_label_is_drawn_as_given_and_wrapped_in_the_gutter(monkeypatch, tmp_path, _inspected_figures):
    shown = "Saccharothrix coeruleofusca JCM 3313 [GCF_014648515.1]"
    monkeypatch.setattr(glm, "reference_genes", lambda _p: (REF35, REF35_LEN))
    prots, rows, core = _two_records()
    res, texts = _drawn_texts(lambda: glm.draw_locus_map(
        tmp_path / "BGC0001853.gbk", rows, [], prots, [core], core, LONG_LABEL, "largimycin", tmp_path / "rl.png",
        print_width="double", row_label=shown), _inspected_figures)
    row = [t for t in texts if "[GCF_014648515.1]" in t]
    assert len(row) == 1 and "\n" in row[0] and row[0].replace("\n", " ") == shown
    assert not any(t == LONG_LABEL for t in texts)
    assert res["min_font_pt"] >= 8.0 and res["text_overlaps"] == 0


def test_shared_match_notes_go_to_the_footnote_at_print_width(monkeypatch, tmp_path, _inspected_figures):
    monkeypatch.setattr(glm, "reference_genes", lambda _p: (REF, REF_LEN))
    prots, rows, core, names = _genome(0)
    rows[1] = dict(rows[1], best_protein="p0")   # reference gene 2 is matched by strain gene p0, which matches gene 1 too
    for width, on_map in (("double", False), (None, True)):
        res, texts = _drawn_texts(lambda: glm.draw_locus_map(
            tmp_path / "BGC0000000.gbk", rows, [], prots, [core], core, "AS-0", "madurastatin",
            tmp_path / f"n_{width}.png", print_width=width), _inspected_figures)
        assert any(t.startswith("matches 2 reference genes") for t in texts) is on_map
        if width:
            assert "each matches 2 reference genes (core_0)" in res["footnote"]
