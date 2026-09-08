"""v9.7.86 P-8: the DAPR scatter annotates with node/contig-anchored labels.

The bare-BGC-id label (`BGC050`) violated the BGC-anchoring rule. The fix routes the
scatter through locus_label, so every annotated label carries its contig/node anchor.
"""
from __future__ import annotations
import pytest

from mamey.render_safe import locus_label


def test_locus_label_carries_node_anchor():
    row = {"bgc_id": "BGC050", "contig": "NODE_77_length_41007_cov_45", "region": "region001"}
    lab = locus_label(row, max_chars=28)
    # the label must start from the assembly locator, not the bare BGC id
    assert "NODE_77" in lab or "NODE" in lab
    assert "BGC050" in lab           # id retained as parenthetical cross-reference
    assert not lab.strip().startswith("BGC050")   # not a bare id


def test_dapr_scatter_uses_locus_label(monkeypatch, tmp_path):
    # render the scatter on a small fixture and assert annotations carry node tokens
    import matplotlib
    matplotlib.use("Agg")
    from mamey import figures_sapote as fs

    rows = [
        {"bgc_id": "BGC001", "contig": "NODE_8_length_203992", "region": "region001",
         "products": ["PKS", "T1PKS"], "boundary": "Edge", "ab": 84.0, "af": 38.0, "kcb_top": "x"},
        {"bgc_id": "BGC002", "contig": "NODE_25_length_118255", "region": "region001",
         "products": ["NRPS"], "boundary": "Interior", "ab": 82.0, "af": 28.0, "kcb_top": "y"},
        {"bgc_id": "BGC003", "contig": "NODE_41_length_80890", "region": "region001",
         "products": ["terpene"], "boundary": "Edge", "ab": 55.0, "af": 52.0, "kcb_top": "z"},
    ]
    captured = []

    import matplotlib.axes
    orig = matplotlib.axes.Axes.annotate
    def spy(self, text, *a, **k):
        captured.append(text)
        return orig(self, text, *a, **k)
    monkeypatch.setattr(matplotlib.axes.Axes, "annotate", spy)

    png = tmp_path / "dapr.png"
    import matplotlib.pyplot as plt
    fs.fig_dapr_scatter(rows, str(png), "Test sp. strain X", plt)

    node_labels = [c for c in captured if "NODE" in str(c)]
    assert node_labels, f"no node-anchored labels were rendered; got {captured}"
    # none of the annotated labels should be a bare BGC id
    for c in captured:
        if str(c).startswith("BGC") and "NODE" not in str(c) and "(" not in str(c):
            raise AssertionError(f"bare BGC label rendered: {c}")
