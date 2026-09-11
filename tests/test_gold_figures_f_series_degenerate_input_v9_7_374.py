"""v9.7.374 (Black Cherry audit) — Path-3 guard, F-series: heatmap() must not crash on a
degenerate (empty) input, matching the guard v9.7.267 already gave its two siblings.

v9.7.267 gave `hmap()` (G-series) and `bubble_matrix()` (D-series) an early-return placeholder
panel when their input matrix has zero rows — see
tests/test_gold_figures_degenerate_input_v9_7_267.py. `heatmap()` (F-series) is a third,
independent copy of the same rendering logic and was never given the same guard: an empty
row list (e.g. no strain in a cohort carries any CCTT trigger, or the resistance-axis scan is
unpopulated for every BGC) reached `ax.imshow()` with a zero-size array and raised
"TypeError: Invalid shape (0,) for image data", aborting figs_multi() — and therefore every
remaining F-series figure for every strain in the batch — uncaught. Reproduced against the
unpatched sealed file; this test locks the F-series fix at the same call site the two sibling
tests already lock for G/D."""
import glob
import os
import pytest

pytest.importorskip("matplotlib")
from mamey import cohort_figures as cf


def test_heatmap_empty_matrix_writes_placeholder_not_crash(tmp_path):
    out = str(tmp_path)
    S = {"S_only": {"deep": {}, "gene": {}, "ms": {"assembly_tier": "GOOD"}, "pkg": "."}}
    # empty matrix (0 rows) — e.g. a cohort where no strain carries any CCTT trigger
    cf.heatmap(mat=[], rowlabs=[], order=["S_only"], S=S, title="empty F view", fid="F_empty", OUT=out)
    assert glob.glob(f"{out}/*F_empty*.png"), "heatmap() should still emit a placeholder PNG on empty input"


def test_heatmap_normal_input_still_renders(tmp_path):
    # a normal 2x2 matrix must still render (guard must not swallow real data)
    out = str(tmp_path)
    S = {"s1": {"deep": {}, "gene": {}, "ms": {"assembly_tier": "GOOD"}, "pkg": "."},
         "s2": {"deep": {}, "gene": {}, "ms": {"assembly_tier": "MODERATE"}, "pkg": "."}}
    cf.heatmap(mat=[[1.0, 2.0], [3.0, 4.0]], rowlabs=["r1", "r2"], order=["s1", "s2"], S=S,
               title="real", fid="F_real", OUT=out)
    assert glob.glob(f"{out}/*F_real*.png")
