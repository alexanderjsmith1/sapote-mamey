"""tools/gap_rescue_locus_map.py: rows lined up on the majority of matches, oriented by the long core genes, with an\nanchor gene marked; reference labels that cannot overlap.

The owner, 2026-10-02, on the AS-660 A-74528 map: "these clinker style maps are in need of being centered on one core gene",
and on the cyclofaulknamycin map: "there is also a lot of overlapping text". The old figure lined up the midpoint of all
matched genes, so unmatched flank on the core contig pulled the lower row sideways, and it stacked reference labels up
to six levels before letting them overlap.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
spec = importlib.util.spec_from_file_location("gap_rescue_locus_map_447", ROOT / "tools/gap_rescue_locus_map.py")
glm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(glm)

# 20 adjacent reference genes, each 0.6 kb, accession-named with long product names (the cyclofaulknamycin case),
# then one long core enzyme.
N = 20
REF = [{"i": i + 1, "name": f"ABC{i:05d}.1", "product": f"Two-component system sensor histidine kinase number {i}",
        "kind": "biosynthetic-additional", "s": i * 0.6, "e": i * 0.6 + 0.55, "strand": 1} for i in range(N)]
REF.append({"i": N + 1, "name": "abcZ", "product": "peptide synthetase", "kind": "biosynthetic",
            "s": N * 0.6, "e": N * 0.6 + 6.0, "strand": 1})
REF_LEN = REF[-1]["e"] + 0.5


def _genome(flank_bp=20000):
    """The core contig carries flank_bp of unmatched genes before the matched block."""
    prots, rows = {}, []
    for k, g in enumerate(REF):
        start = flank_bp + int(g["s"] * 1000)
        pid = f"p{k}"
        prots[pid] = {"tag": f"core_{k}", "contig": "core", "start": start, "end": start + int((g["e"] - g["s"]) * 1000),
                      "strand": 1, "contig_len": 60000}
        rows.append({"status": "PRESENT_IN_CORE", "best_protein": pid, "best_identity_pct": 90.0,
                     "reciprocal_best": True, "partner_verdict": ""})
    for j in range(8):  # unmatched flank genes
        prots[f"f{j}"] = {"tag": f"flank_{j}", "contig": "core", "start": 1000 + j * 2200, "end": 2800 + j * 2200,
                          "strand": -1, "contig_len": 60000}
    core = {"contig": "core", "start": 0, "end": flank_bp + int(REF_LEN * 1000),
            "identity": "AS-0 / core / region001 / BGC001"}
    return prots, rows, core


def _draw(monkeypatch, tmp_path, anchor=None):
    import matplotlib.pyplot as plt
    monkeypatch.setattr(glm, "reference_genes", lambda _p: (REF, REF_LEN))
    figs = []
    monkeypatch.setattr(plt, "close", lambda fig=None: figs.append(fig))
    prots, rows, core = _genome()
    glm.draw_locus_map(tmp_path / "BGC0000000.gbk", rows, [], prots, [core], core, "AS-0", "test", tmp_path / "m.png",
                       anchor=anchor)
    return figs[-1]


def test_the_default_anchor_is_the_longest_matched_core_enzyme_on_the_core_contig():
    prots, rows, _ = _genome()
    drawn = [(k, f"p{k}", 90.0) for k in range(len(REF))]
    assert glm.anchor_gene(REF, drawn, prots, "core") == (N, f"p{N}")
    assert glm.anchor_gene(REF, drawn, prots, "core", name="ABC00003.1") == (3, "p3")
    assert glm.anchor_gene(REF, [], prots, "core") is None


def test_a_core_enzyme_on_a_partner_contig_beats_a_transporter_on_the_core_contig():
    """AS-609 BGC010 against SF2768: the NRPS match sits on NODE_243, and the map had centred on an MFS transporter."""
    prots, _, _ = _genome()
    prots = dict(prots, p20=dict(prots[f"p{N}"], contig="partner"))
    drawn = [(3, "p3", 70.0), (N, "p20", 72.0)]
    assert glm.anchor_gene(REF, drawn, prots, "core") == (N, "p20")


def test_the_anchor_match_sits_directly_under_the_anchor_gene(monkeypatch, tmp_path):
    """On a collinear locus the majority alignment (bulk_offset) also puts the anchor under its gene; 10 bp covers the
    whole-base rounding of the synthetic gene ends."""
    from matplotlib.patches import Polygon
    for anchor, k in ((None, N), ("ABC00004.1", 4)):
        fig = _draw(monkeypatch, tmp_path, anchor)
        g = REF[k]
        ribbon = next(p for p in fig.axes[0].patches if isinstance(p, Polygon)
                      and abs(p.get_xy()[0][0] - g["s"]) < 1e-9 and abs(p.get_xy()[1][0] - g["e"]) < 1e-9)
        xy = ribbon.get_xy()
        top_mid, bottom_mid = (xy[0][0] + xy[1][0]) / 2, (xy[2][0] + xy[3][0]) / 2
        assert bottom_mid == pytest.approx(top_mid, abs=0.01)


def test_reference_labels_never_overlap_however_many_neighbours(monkeypatch, tmp_path):
    fig = _draw(monkeypatch, tmp_path)
    ax = fig.axes[0]
    labels = sorted((t for t in ax.texts if t.get_rotation() == 60 and t.get_position()[1] > 1.0),
                    key=lambda t: t.get_position()[0])
    assert len(labels) == N + 1
    # parallel 60-degree lines of text cannot touch when their anchors are a line height / sin(60) apart
    fig.canvas.draw()
    inv = ax.transData.inverted()
    line_px = 7.5 * fig.dpi / 72 * 1.3
    min_dx = abs(inv.transform((line_px / 0.866, 0))[0] - inv.transform((0, 0))[0])
    xs = [t.get_position()[0] for t in labels]
    assert all(b - a >= min_dx * 0.999 for a, b in zip(xs, xs[1:]))
    # and none is cut: no reference label starts left of the axes
    assert min(xs) >= ax.get_xlim()[0]


def test_a_pair_map_skips_a_split_piece_contig_left_with_nothing_to_draw(monkeypatch, tmp_path):
    """AS-956, 2 Oct: a CLEAR split gene's second piece sat on a third contig. A pair map keeps only the two fragments'
    windows, so that contig had no match left and the old renderer stopped with "min() iterable argument is empty"."""
    if "partner" not in glm.draw_locus_map.__code__.co_varnames:
        pytest.skip("pair mode comes with the RG-GMCI pair-map card")
    ref = [{"i": i + 1, "name": n, "product": "p", "kind": "biosynthetic", "s": i, "e": i + 0.9, "strand": 1}
           for i, n in enumerate(["abcA", "abcB", "abcC"])]
    monkeypatch.setattr(glm, "reference_genes", lambda _p: (ref, 3.5))
    prot = lambda tag, contig, start: {"tag": tag, "contig": contig, "start": start, "end": start + 900, "strand": 1,
                                       "contig_len": 20000}
    prots = {"q1": prot("a_1", "ctgA", 18000), "q2": prot("b_1", "ctgB", 500), "q3": prot("x_1", "ctgX", 19000)}
    rows = [{"status": "PRESENT_IN_CORE", "best_protein": "q1", "best_identity_pct": 60.0, "reciprocal_best": True},
            {"status": "MISSING_FOUND_CLEAR", "best_protein": "q2", "best_identity_pct": 55.0, "reciprocal_best": True},
            {"status": "MISSING_NOT_FOUND", "best_protein": None, "best_identity_pct": 0.0, "reciprocal_best": False}]
    splits = [{"split_call": "CLEAR", "reference_gene": "3", "piece1_locus": "a_1", "piece2_locus": "x_1",
               "piece1_identity_pct": "50", "piece2_identity_pct": "48"}]
    core = {"contig": "ctgA", "start": 15000, "end": 20000, "identity": "S / ctgA / region001 / BGC001"}
    partner = {"contig": "ctgB", "start": 0, "end": 5000, "identity": "S / ctgB / region001 / BGC002"}
    res = glm.draw_locus_map(tmp_path / "BGC0000000.gbk", rows, splits, prots, [core, partner], core, "S", "test",
                             tmp_path / "m.png", partner=partner)
    assert res["contigs_drawn"] == ["ctgA", "ctgB"]


def test_rows_line_up_on_the_majority_of_matches_not_one_anchor_gene():
    """The owner, 2 Oct (AS-365 BGC020): "aligned (centered) against 2 genes and then the majority of the genes are not
    centered". Three of four matches share one offset; the long anchor gene sits after an insertion. The median wins."""
    ref = [{"s": float(i), "e": i + 0.5} for i in range(4)]
    prots = {f"p{i}": {"contig": "core"} for i in range(4)}
    xpos = {"p0": (10.0, 10.5, 1), "p1": (11.0, 11.5, 1), "p2": (12.0, 12.5, 1), "p3": (20.0, 26.0, 1)}
    drawn = [(i, f"p{i}", 80.0) for i in range(4)]
    assert glm.bulk_offset(ref, drawn, xpos, prots, "core") == -10.0
    assert glm.bulk_offset(ref, [], xpos, prots, "core") is None


def test_orientation_follows_the_long_core_genes_not_many_small_ones(monkeypatch, tmp_path):
    """The owner, 2 Oct (AS-365 BGC049): five small tailoring genes in reference order outvoted two NRPS genes in reverse
    order, and the NRPS ribbons crossed. Orientation is now weighted by gene length."""
    import matplotlib.pyplot as plt
    ref = [{"i": 1, "name": "nrpsA", "product": "NRPS", "kind": "biosynthetic", "s": 0.0, "e": 12.0, "strand": 1},
           {"i": 2, "name": "nrpsB", "product": "NRPS", "kind": "biosynthetic", "s": 12.5, "e": 24.0, "strand": 1}]
    ref += [{"i": 3 + j, "name": f"t{j}", "product": "tailoring", "kind": "biosynthetic-additional",
             "s": 25.0 + j, "e": 25.6 + j, "strand": 1} for j in range(5)]
    monkeypatch.setattr(glm, "reference_genes", lambda _p: (ref, 31.0))
    prots, rows = {}, []
    place = {0: 13000, 1: 0}                       # the two NRPS genes in reverse order on the contig...
    for k, g in enumerate(ref):
        start = place.get(k, 26000 + (k - 2) * 1000)  # ...the five small genes in reference order after them
        prots[f"p{k}"] = {"tag": f"c{k}", "contig": "core", "start": start, "end": start + int((g["e"] - g["s"]) * 1000),
                          "strand": -1 if k in place else 1, "contig_len": 40000}   # the NRPS pair is reverse-complemented
        rows.append({"status": "PRESENT_IN_CORE", "best_protein": f"p{k}", "best_identity_pct": 80.0,
                     "reciprocal_best": True, "partner_verdict": ""})
    core = {"contig": "core", "start": 0, "end": 31000, "identity": "AS-0 / core / region001 / BGC001"}
    monkeypatch.setattr(plt, "close", lambda fig=None: None)
    res = glm.draw_locus_map(tmp_path / "BGC0000000.gbk", rows, [], prots, [core], core, "AS-0", "test", tmp_path / "m.png")
    assert res["flipped"]["core"] is True           # by count the five small (+) genes would have kept it forward


def test_strand_agreement_decides_orientation_before_gene_order(monkeypatch, tmp_path):
    """The owner, 2 Oct (AS-678 BGC021 against nocobactin): every reference gene and every match is on the + strand, but the
    matches sit in reverse reference order. An order-based flip turned every arrow the wrong way. Strand comes first."""
    import matplotlib.pyplot as plt
    ref = [{"i": k + 1, "name": f"nbt{k}", "product": "NRPS", "kind": "biosynthetic", "s": k * 3.0, "e": k * 3.0 + 2.5,
            "strand": 1} for k in range(5)]
    monkeypatch.setattr(glm, "reference_genes", lambda _p: (ref, 15.0))
    prots, rows = {}, []
    for k in range(5):
        start = (4 - k) * 3000                       # reverse order on the contig, same (+) strand
        prots[f"p{k}"] = {"tag": f"c{k}", "contig": "core", "start": start, "end": start + 2500, "strand": 1,
                          "contig_len": 20000}
        rows.append({"status": "PRESENT_IN_CORE", "best_protein": f"p{k}", "best_identity_pct": 50.0,
                     "reciprocal_best": True, "partner_verdict": ""})
    core = {"contig": "core", "start": 0, "end": 15000, "identity": "AS-0 / core / region001 / BGC001"}
    monkeypatch.setattr(plt, "close", lambda fig=None: None)
    res = glm.draw_locus_map(tmp_path / "BGC0000000.gbk", rows, [], prots, [core], core, "AS-0", "test", tmp_path / "m.png")
    assert res["flipped"]["core"] is False           # arrows agree with the reference; order alone would have flipped it
