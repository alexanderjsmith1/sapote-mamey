from __future__ import annotations

import csv

import pytest

pytest.importorskip("matplotlib")
import matplotlib.pyplot as plt

from mamey.locus_map import render_locus_map


def _rows():
    return [
        {
            "locus_tag": f"gene_{index}",
            "start": index * 1400,
            "end": index * 1400 + 164,
            "strand": 1,
            "color": "#cccccc",
            "role": "other / hypothetical",
            "is_core": False,
            "length_aa": 54,
            "order": index,
            "gene_functions": "",
        }
        for index in range(1, 72)
    ]


def test_dense_label_suppression_is_visible_and_lossless(tmp_path, monkeypatch):
    captured = []
    original = plt.Figure.savefig

    def spy(self, *args, **kwargs):
        captured.extend(text.get_text() for text in self.texts)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(plt.Figure, "savefig", spy)
    png = tmp_path / "locus.png"
    sidecar = tmp_path / "locus_data.csv"
    render_locus_map(
        [("BGC001 · NODE_7 · region001", _rows())],
        png,
        sidecar,
        suptitle="Reference locus",
        claim_prefix="PUBLIC",
    )
    assert any("labels shown" in text and "/71" in text for text in captured)
    with sidecar.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 71
    assert "label_visible_on_figure" in rows[0]
    assert {row["label_visible_on_figure"] for row in rows} == {"NO"}


def test_normative_locus_map_contract_is_shipped():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    text = (root / "docs" / "LOCUS_MAP_REVIEW_CONTRACT.md").read_text(encoding="utf-8")
    assert "suppression must never be silent" in text
    assert "per-gene BLASTp subject, percent identity, and query coverage" in text
    assert "domain architecture or HMM" in text
