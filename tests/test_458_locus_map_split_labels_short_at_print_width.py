"""tools/gap_rescue_locus_map.py at a print width: the two split-gene label forms are shorter, so a landscape page stays inside
its height limit ("RS48140-like, split piece 1 of 2, 86%" is the deepest label on the AS-846 ansacarbamitocin maps).

Pieces far apart get one label each: "<gene>-like, split piece N of 2, P%" becomes "<gene>-like split N/2, P%". Pieces side by side
share one label: "<gene>-like, split P% | Q%" becomes "<gene>-like split P|Q%". The screen layout keeps the long forms.
"""
import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gap_rescue_locus_map_458c", ROOT / "tools/gap_rescue_locus_map.py")
glm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(glm)

REF = [{"i": i + 1, "name": n, "product": "p", "kind": "biosynthetic", "s": i * 1.2, "e": i * 1.2 + 1.0, "strand": 1}
       for i, n in enumerate(["abcA", "abcB", "abcC", "abcD"])]


def _prot(tag, contig, start_bp, contig_len=40000):
    return {"tag": tag, "contig": contig, "start": start_bp, "end": start_bp + 900, "strand": 1, "contig_len": contig_len}


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


def _labels(monkeypatch, tmp_path, prots, core, figs, **kw):
    monkeypatch.setattr(glm, "reference_genes", lambda _p: (REF, 5.0))
    rows = [{"status": "PRESENT_IN_CORE", "best_protein": f"q{i}", "best_identity_pct": 70.0, "reciprocal_best": True,
             "partner_verdict": ""} for i in range(3)] + [{"status": "MISSING_NOT_FOUND", "best_protein": None,
                                                           "best_identity_pct": 0.0, "reciprocal_best": False}]
    splits = [{"split_call": "CLEAR", "reference_gene": "4", "piece1_locus": "s_1", "piece2_locus": "s_2",
               "piece1_identity_pct": "64", "piece2_identity_pct": "61"}]
    glm.draw_locus_map(tmp_path / "BGC0000000.gbk", rows, splits, prots, [core], core, "AS-0", "test", tmp_path / "m.png", **kw)
    return [t.get_text() for t in figs[-1].axes[0].texts if "split" in t.get_text() and "-like" in t.get_text()]


FAR = ({"q0": _prot("c_0", "core", 20000), "q1": _prot("c_1", "core", 21200), "q2": _prot("c_2", "core", 22400),
        "p1": _prot("s_1", "core", 100), "p2": _prot("s_2", "ctgX", 39000)},
       {"contig": "core", "start": 0, "end": 40000, "identity": "AS-0 / core / region001 / BGC001"})
NEAR = ({"q0": _prot("c_0", "core", 35000), "q1": _prot("c_1", "core", 36200), "q2": _prot("c_2", "core", 37400),
         "p1": _prot("s_1", "core", 38800), "p2": _prot("s_2", "ctgX", 100)},
        {"contig": "core", "start": 30000, "end": 40000, "identity": "AS-0 / core / region001 / BGC001"})


def test_far_pieces_get_the_short_label_at_a_print_width(monkeypatch, tmp_path, _figs):
    labs = _labels(monkeypatch, tmp_path, *FAR, _figs, print_width="landscape")
    assert sorted(labs) == ["AbcD-like split 1/2, 64%", "AbcD-like split 2/2, 61%"]


def test_adjacent_pieces_get_the_short_shared_label_at_a_print_width(monkeypatch, tmp_path, _figs):
    assert _labels(monkeypatch, tmp_path, *NEAR, _figs, print_width="landscape") == ["AbcD-like split 64|61%"]


def test_the_screen_layout_keeps_the_long_forms(monkeypatch, tmp_path, _figs):
    assert sorted(_labels(monkeypatch, tmp_path, *FAR, _figs)) == ["AbcD-like, split piece 1 of 2, 64%", "AbcD-like, split piece 2 of 2, 61%"]
    assert _labels(monkeypatch, tmp_path, *NEAR, _figs) == ["AbcD-like, split 64% | 61%"]
