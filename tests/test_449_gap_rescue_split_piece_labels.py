"""tools/gap_rescue_locus_map.py: a split gene whose two pieces are drawn far apart gets one label under each piece.

A spectinomycin-like map (6 Oct) labelled SpcJ once, midway between its pieces at the two ends of the figure, so the label
sat over unrelated genes and the label-spreading pass pushed the SpcK label along with it. Pieces drawn side by side, across
a contig gap, keep one label.
"""
import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gap_rescue_locus_map_449s", ROOT / "tools/gap_rescue_locus_map.py")
glm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(glm)

REF = [{"i": i + 1, "name": n, "product": "p", "kind": "biosynthetic", "s": i * 1.2, "e": i * 1.2 + 1.0, "strand": 1}
       for i, n in enumerate(["abcA", "abcB", "abcC", "abcD"])]


def _prot(tag, contig, start_bp, contig_len=40000):
    return {"tag": tag, "contig": contig, "start": start_bp, "end": start_bp + 900, "strand": 1, "contig_len": contig_len}


def _labels(monkeypatch, tmp_path, prots, core):
    import matplotlib.pyplot as plt
    monkeypatch.setattr(glm, "reference_genes", lambda _p: (REF, 5.0))
    figs = []
    monkeypatch.setattr(plt, "close", lambda fig=None: figs.append(fig))
    rows = [{"status": "PRESENT_IN_CORE", "best_protein": f"q{i}", "best_identity_pct": 70.0, "reciprocal_best": True,
             "partner_verdict": ""} for i in range(3)] + [{"status": "MISSING_NOT_FOUND", "best_protein": None,
                                                           "best_identity_pct": 0.0, "reciprocal_best": False}]
    splits = [{"split_call": "CLEAR", "reference_gene": "4", "piece1_locus": "s_1", "piece2_locus": "s_2",
               "piece1_identity_pct": "64", "piece2_identity_pct": "61"}]
    glm.draw_locus_map(tmp_path / "BGC0000000.gbk", rows, splits, prots, [core], core, "AS-0", "test", tmp_path / "m.png")
    # gene labels only ("AbcD-like, split ..."): the footnote also mentions a split gene, and is not a label
    return [t.get_text() for t in figs[-1].axes[0].texts if "split" in t.get_text() and "-like" in t.get_text()]


def test_pieces_drawn_far_apart_get_one_label_each(monkeypatch, tmp_path):
    prots = {"q0": _prot("c_0", "core", 20000), "q1": _prot("c_1", "core", 21200), "q2": _prot("c_2", "core", 22400),
             "p1": _prot("s_1", "core", 100), "p2": _prot("s_2", "ctgX", 39000)}
    core = {"contig": "core", "start": 0, "end": 40000, "identity": "AS-0 / core / region001 / BGC001"}
    labs = _labels(monkeypatch, tmp_path, prots, core)
    assert sorted(labs) == ["AbcD-like, split piece 1 of 2, 64%", "AbcD-like, split piece 2 of 2, 61%"]


def test_pieces_side_by_side_across_a_gap_keep_one_label(monkeypatch, tmp_path):
    prots = {"q0": _prot("c_0", "core", 35000), "q1": _prot("c_1", "core", 36200), "q2": _prot("c_2", "core", 37400),
             "p1": _prot("s_1", "core", 38800), "p2": _prot("s_2", "ctgX", 100)}
    core = {"contig": "core", "start": 30000, "end": 40000, "identity": "AS-0 / core / region001 / BGC001"}
    labs = _labels(monkeypatch, tmp_path, prots, core)
    assert labs == ["AbcD-like, split 64% | 61%"]
