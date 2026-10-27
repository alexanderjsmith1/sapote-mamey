"""tools/bioassay_paper_theme.R .ink_margins(): the white space around everything drawn, measured to solve each panel's plot margins.

It counted "ink" only where a pixel was darker than 0.92 on some channel. The palest heat-map tile (#EEF3F8 = 0.933 / 0.953 / 0.973) is
lighter than that, so a heat map whose last column is pale (Bee Fig. S21 panel B, "P. larvae 818": 0/1, n.t.) had that column left out of the
measurement. The right margin was solved too small and the last column was cut by the page edge. Any non-white pixel now counts.
"""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(shutil.which("Rscript") is None, reason="needs R: Rscript not on PATH")

R_PROBE = r'''
suppressPackageStartupMessages(library(png))
src <- parse(file = file.path(Sys.getenv("ROOT"), "tools", "bioassay_paper_theme.R"))
for (e in src) if (is.call(e) && identical(as.character(e[[1]]), "<-") && identical(as.character(e[[2]]), ".ink_margins")) eval(e)
a <- array(1, c(100, 200, 3))
tile <- as.numeric(strsplit(Sys.getenv("TILE"), ",")[[1]])
for (k in 1:3) a[20:80, 100:180, k] <- tile[k]       # a tile ending 20 px short of the right edge
f <- tempfile(fileext = ".png"); writePNG(a, f)
m <- .ink_margins(f); cat(m[["r"]], m[["l"]], m[["t"]], m[["b"]], "\n")
'''


def _margins(tile):
    import os
    env = dict(os.environ, ROOT=str(ROOT), TILE=tile)
    out = subprocess.run(["Rscript", "-e", R_PROBE], env=env, text=True, capture_output=True)
    assert out.returncode == 0, out.stderr
    return [float(x) for x in out.stdout.split()[-4:]]


def test_the_palest_heat_map_tile_counts_as_drawn_content():
    r, l, t, b = _margins("0.9333,0.9529,0.9725")      # #EEF3F8
    assert (r, l, t, b) == (20, 99, 19, 20)


def test_a_dark_tile_still_counts():
    r, l, t, b = _margins("0.1,0.2,0.3")
    assert (r, l, t, b) == (20, 99, 19, 20)


def test_pure_white_is_not_content():
    r, l, t, b = _margins("1,1,1")
    assert r == float('inf') or r >= 200     # nothing drawn: no ink found at all
