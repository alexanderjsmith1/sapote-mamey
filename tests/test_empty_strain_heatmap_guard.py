"""Empty/all-zero strain must not crash the cohort heatmap helpers.

v9.7.212's empty-strain guard (Nocardia patch B) fixed ONE np.nanmax site (figs_single, ~line 458)
but left the shared heatmap()/hmap() helpers and the class×resistance figure exposed to the identical
crash: an empty cohort or an all-zero/all-negative strain row makes the log-scaled `disp` array
empty/all-NaN, and np.nanmin/np.nanmax then raise (ValueError: zero-size reduction) or emit an all-NaN
RuntimeWarning. These tests exercise the real helpers with that input.
"""
import warnings
import numpy as np
import pytest as _pytest
_pytest.importorskip("matplotlib")  # SKIP (not error) when figure stack absent
import matplotlib
matplotlib.use("Agg")
import mamey.cohort_figures as cf


def _no_crash(fn, *a, **k):
    with warnings.catch_warnings():
        # promote the all-NaN RuntimeWarning to an error so a silent near-miss still fails the test;
        # ignore the benign singular-axis UserWarning matplotlib emits on a degenerate 1-cell grid.
        warnings.simplefilter("error", RuntimeWarning)
        warnings.filterwarnings("ignore", category=UserWarning)
        fn(*a, **k)


def test_heatmap_survives_all_zero_strain(tmp_path):
    _no_crash(cf.heatmap, np.array([[0, 0], [0, 0]], float), ["rowA", "rowB"],
              ["AS-999", "AS-998"], {}, "all-zero", "T1", str(tmp_path), lognorm=True, annot=True)


def test_heatmap_survives_empty_cohort(tmp_path):
    _no_crash(cf.heatmap, np.zeros((0, 0)), [], [], {}, "empty", "T2", str(tmp_path),
              lognorm=True, annot=True)


def test_hmap_survives_all_zero_strain(tmp_path):
    # hmap() carries the same guarded block; exercise it the same way.
    _no_crash(cf.hmap, np.array([[0, 0], [0, 0]], float), ["rowA", "rowB"],
              ["AS-999", "AS-998"], "all-zero", "T3", str(tmp_path), lognorm=True, annot=True)
