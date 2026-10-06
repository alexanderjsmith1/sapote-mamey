"""A strip is saved with a tight bounding box, so its x-axis label is never clipped: nothing touches the image's bottom
edge. (A strip with long angled labels, drawn flipped, used to cut its axis label off at the bottom.)"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import strain_slides as ss  # noqa: E402

PIL = pytest.importorskip("PIL.Image")


def test_strip_axis_label_is_not_clipped(tmp_path):
    pytest.importorskip("matplotlib")
    genes = [dict(s=1500 * i, e=1500 * i + 1300, strand=1, tag=f"ctg1_{i}", role="", dom="", p=0.5) for i in range(1, 10)]
    out = ss.strip(genes, [], 0, 15000, tmp_path / "s.png", label_fn=lambda g: "Ketoacyl-synt_C, PKSI-KS_m4",
                   colour_fn=lambda g: "#C7CBD1", height=2.15, flip=True)
    im = PIL.open(out).convert("L")
    w, h = im.size
    assert min(im.crop((0, h - 3, w, h)).getdata()) > 240  # the bottom edge is blank: no clipped text
