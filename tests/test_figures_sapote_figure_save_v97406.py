"""Canonical pair/receipt regression for Sapote-layer figure producers."""
from __future__ import annotations

import json

import pytest

pytest.importorskip("matplotlib")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from mamey.figures_sapote import fig_dapr_scatter


def test_dapr_producer_writes_svg_sibling_and_receipt(tmp_path):
    rows = [{
        "bgc_id": "BGC001", "contig": "NODE_1_length_5000_cov_40.0",
        "region": "region001", "products": ["NRPS"], "boundary": "Interior",
        "ab": 80.0, "af": 50.0, "kcb_top": "", "lead_tier": "High",
    }]
    png = tmp_path / "generic_dapr.png"
    fig_dapr_scatter(rows, str(png), "Synthetic strain", plt)
    assert png.is_file() and png.with_suffix(".svg").is_file()
    receipt = json.loads((tmp_path / "figure_receipts.jsonl").read_text().splitlines()[0])
    assert receipt["renderer"] == "figures_sapote.dapr_scatter"
    assert receipt["outputs"]["png"]["logical_locator"] == png.name
