"""v9.7.267 — Path-3 guard: the gold figure helpers must not crash on a degenerate (empty) input.

A single-BGC strain (e.g., a single-region MIBiG reference run through `mamey run`) leaves some
cross-strain/cross-BGC views with an empty matrix. Previously `bubble_matrix` did `counts.max()` on
the empty array ("zero-size array to reduction operation maximum") and `hmap` did `imshow` on a
zero-size array ("Invalid shape (0,)"); either exception propagated out of the whole gold suite and
skipped every figure. They now render a labelled empty-state panel and return. Reproduced from a
1-BGC slice of a real gold package."""
import glob
import os
import pytest

pytest.importorskip("matplotlib")
from PIL import Image  # ships with matplotlib
from mamey import cohort_figures as cf


def test_hmap_empty_matrix_writes_placeholder_not_crash(tmp_path):
    out = str(tmp_path)
    # empty matrix (0 rows) — the single-BGC / empty-view case
    cf.hmap(mat=[], rowlabs=[], order=["S_only"], title="empty view", fid="G_empty", OUT=out)
    assert glob.glob(f"{out}/*G_empty*.png"), "hmap should still emit a placeholder PNG on empty input"


def test_bubble_matrix_empty_rows_writes_placeholder_not_crash(tmp_path):
    out = str(tmp_path)
    # no rows -> counts.max() on empty array used to raise the audit's exact ValueError
    cf.bubble_matrix(rows=[], order=["S_only"],
                     count_fn=lambda r, s: 0, color_fn=lambda r, s: None,
                     title="empty bubbles", fid="D_empty", OUT=out, clab="c", slab="s")
    hits = glob.glob(f"{out}/*D_empty*.png")
    assert hits, "bubble_matrix should emit a placeholder PNG on empty input"
    fname = os.path.basename(hits[0])

    # v9.7.268 — lock the EARLY-RETURN placeholder path specifically. bubble_matrix has a second,
    # inline guard (`counts.max() if counts.size else 0`) that also prevents the crash, so a bare
    # "a PNG exists / it didn't crash" assertion passes even if the early-return guard is removed —
    # it was effectively vacuous w.r.t. the guard it was meant to lock. Two discriminators that only
    # the early-return placeholder satisfies:
    #   1. size: the placeholder is a fixed 6.0x2.2in panel; the normal render path on this same
    #      empty input is ~8.6in wide. A width under 7.6in fails if the early-return is bypassed.
    #
    # v9.7.403 — measure INCHES, not pixels. This assertion was written as a raw `w < 1150` when
    # savefig.dpi was ~150 (placeholder ~992px, normal ~1292px). cohort_figures now sets
    # PUBLICATION_RASTER_DPI = 300 globally, so the *correct* placeholder renders at 1984x844 and
    # the pixel bound went red for a reason that has nothing to do with the early-return guard it
    # exists to lock — a false alarm that made `--run-slow` unusable as a release gate. Dividing by
    # the module's own DPI restores the original discriminator at any raster setting, and keeps the
    # guard honest: bypassing the early return still widens the figure past the threshold.
    dpi = float(cf.PUBLICATION_RASTER_DPI)
    w, h = Image.open(hits[0]).size
    w_in, h_in = w / dpi, h / dpi
    assert w_in < 7.6, (
        f"expected the small 6.0in placeholder panel, got {w_in:.2f}x{h_in:.2f}in "
        f"({w}x{h} px at {dpi:g} dpi) — early-return bypassed?"
    )
    #   2. series: bubble_matrix is a D-series figure; the placeholder must be stamped D, not G
    #      (the pre-v9.7.268 copy from hmap stamped it G, mis-filing it into the heatmap family).
    assert fname.startswith("D"), f"placeholder must be D-series, got {fname}"


def test_hmap_normal_input_still_renders(tmp_path):
    # a normal 2x2 matrix must still render (guard must not swallow real data)
    out = str(tmp_path)
    cf.hmap(mat=[[1.0, 2.0], [3.0, 4.0]], rowlabs=["r1", "r2"], order=["s1", "s2"],
            title="real", fid="G_real", OUT=out)
    assert glob.glob(f"{out}/*G_real*.png")
