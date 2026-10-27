"""The v8 locus-map PNG is written at 300 DPI (figure house rule 1).

The producer requested 180 DPI. The owner ruled that the house rule is the standard. This test
renders one map and reads the DPI and pixel width back from the PNG.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

pytest.importorskip("matplotlib")
Image = pytest.importorskip("PIL.Image")

from test_locus_map_v8 import _fixture  # noqa: E402


def test_v8_png_carries_300_dpi():
    from mamey.locus_map_v8 import render_bgc_v8

    with tempfile.TemporaryDirectory() as tmp:
        pkg = _fixture(Path(tmp), with_comparator=False, gene_count=6)
        out = Path(tmp) / "rendered"
        receipt = render_bgc_v8(pkg, "BGC001", out_dir=out)
        assert receipt["status"] == "READY"
        with Image.open(out / "BGC001_locus_map.png") as img:
            dpi = img.info.get("dpi")
            width = img.size[0]
        assert dpi is not None and round(dpi[0]) == 300, dpi
        assert width == 16 * 300, width
