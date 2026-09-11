"""Canonical figure-save contract for the legacy BGC figure producer."""
from __future__ import annotations

import json

import pytest

pytest.importorskip("matplotlib")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from mamey.bgc_figures import _save_pair
from mamey.figure_save import audit_figure_outputs


def test_bgc_figure_adapter_writes_pair_and_bound_receipt(tmp_path):
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    png = tmp_path / "generic_bgc_figure.png"
    _save_pair(fig, png, renderer="test.generic", provenance="synthetic_fixture")
    plt.close(fig)

    assert png.is_file()
    assert png.with_suffix(".svg").is_file()
    rows = [json.loads(line) for line in (tmp_path / "figure_receipts.jsonl").read_text().splitlines()]
    assert rows[0]["figure_id"] == "generic_bgc_figure"
    assert rows[0]["provenance"] == "synthetic_fixture"
    assert audit_figure_outputs(tmp_path)["status"] == "PASS"
