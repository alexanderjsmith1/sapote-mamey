"""Tests for the v9.7.437 matrix-panel geometry cap (PATCH_07).

The defect: `fig_w = 1.55*len(order)+3.4` had no upper bound, so a 46-strain cohort
produced a 74.7-inch figure and a three-row view rendered at an aspect ratio over 20:1
(G04 on disk: 11295 x 644 px). The load-bearing guarantees are (a) small cohorts are unchanged,
(b) width is capped, (c) aspect is capped, (d) labels taper so a capped panel stays legible.
"""
import matplotlib
matplotlib.use("Agg")

import numpy as np

from mamey import cohort_figures as cf


def test_any_panel_within_the_width_cap_is_byte_identical_to_the_old_formula():
    """A figure that renders acceptably today must not change shape. The aspect correction is
    gated on the width cap for exactly this reason."""
    for n in range(1, 13):
        w, h = cf._matrix_fig_size(n, 6, 1.55, 3.4, 0.36, 2.6)
        assert w == max(8.0, 1.55 * n + 3.4)
        assert h == max(3.2, 0.36 * 6 + 2.6)


def test_width_is_capped_at_cohort_scale():
    w, _ = cf._matrix_fig_size(46, 25, 1.55, 3.4, 0.36, 2.6)
    assert w == cf.MATRIX_MAX_FIG_W
    assert w < 1.55 * 46 + 3.4          # the uncapped value was 74.7 inches


def test_the_actual_G04_shape_is_no_longer_a_ribbon():
    """46 strains x 3 rows is the panel that rendered 11295 x 644 px."""
    w, h = cf._matrix_fig_size(46, 3, 1.55, 3.4, 0.36, 2.6)
    assert w / h <= cf.MATRIX_MAX_ASPECT + 1e-9
    assert w / h < 20.0


def test_aspect_cap_grows_height_rather_than_shrinking_width():
    w, h = cf._matrix_fig_size(46, 3, 1.55, 3.4, 0.36, 2.6)
    assert w == cf.MATRIX_MAX_FIG_W
    assert h > max(3.2, 0.36 * 3 + 2.6)


def test_tall_panels_are_left_alone():
    """Many rows and few columns is already fine; the cap must not touch it."""
    w, h = cf._matrix_fig_size(4, 40, 1.55, 3.4, 0.36, 2.6)
    assert w == max(8.0, 1.55 * 4 + 3.4)
    assert h == 0.36 * 40 + 2.6


def test_label_size_tapers_only_past_the_knee():
    assert cf._matrix_label_size(8) == 8.0
    assert cf._matrix_label_size(cf.MATRIX_LABEL_KNEE) == 8.0
    assert cf._matrix_label_size(46) < 8.0
    assert cf._matrix_label_size(46) >= 5.0


def test_dense_labels_rotate_but_small_cohorts_keep_historical_orientation():
    assert "rotation" not in cf._matrix_label_kwargs(cf.MATRIX_LABEL_KNEE)
    assert cf._matrix_label_kwargs(46)["rotation"] == 90


def test_degenerate_inputs_do_not_explode():
    for n_cols, n_rows in ((0, 0), (0, 5), (5, 0), (-1, -1)):
        w, h = cf._matrix_fig_size(n_cols, n_rows, 1.55, 3.4, 0.36, 2.6)
        assert w >= 8.0 and h >= 3.2
        assert w <= cf.MATRIX_MAX_FIG_W


def test_hmap_uses_capped_geometry_and_tapered_labels_at_cohort_scale(monkeypatch, tmp_path):
    captured = {}

    def capture(fig, _path):
        captured["size"] = tuple(float(v) for v in fig.get_size_inches())
        captured["label_sizes"] = [tick.get_fontsize() for tick in fig.axes[0].get_xticklabels()]
        captured["label_rotations"] = [tick.get_rotation() for tick in fig.axes[0].get_xticklabels()]

    monkeypatch.setattr(cf, "_save_pair", capture)
    monkeypatch.setattr(cf, "sidecar", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cf, "lab", lambda value: value)
    monkeypatch.setattr(cf, "is_private", lambda _value: False)

    order = [f"strain-{index:02d}" for index in range(46)]
    cf.hmap(
        np.ones((3, 46)),
        ["interior", "edge", "full-contig"],
        order,
        "Synthetic boundary-status matrix",
        "geometry_check",
        str(tmp_path),
        lognorm=False,
        annot=False,
    )

    width, height = captured["size"]
    assert width == cf.MATRIX_MAX_FIG_W
    assert width / height <= cf.MATRIX_MAX_ASPECT
    assert captured["label_sizes"]
    assert set(captured["label_sizes"]) == {cf._matrix_label_size(46)}
    assert set(captured["label_rotations"]) == {90.0}
