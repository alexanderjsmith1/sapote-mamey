"""TREES_434: a tip with no deposited value must draw NO strip tile.

render_tree_COLOR_STRIPS.R already maps empty strings to NA (line ~57), then hands the frame to
ggplot with `na.translate=FALSE` and no `na.value`. `na.translate=FALSE` drops NA from the *scale*,
it does not stop the geom drawing a tile for that row, so the tile falls back to ggplot's default
grey50. An absent value therefore renders as a solid block indistinguishable from a real category.

That is not cosmetic. Leaving a field empty is only defensible because an empty cell reads as
"not deposited". If absence renders as a filled block, the figure asserts provenance the record
does not support.

Fix: build the strip from the rows that have a value, so absence leaves the background showing.
"""
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parent.parent
R_FILE = ROOT / "tools" / "render_tree_COLOR_STRIPS.R"


def test_strip_builder_excludes_absent_rows():
    """Static contract: mk() must not hand NA rows to the geom."""
    src = R_FILE.read_text()
    mk = [ln for ln in src.splitlines() if ln.startswith("mk<-function(")]
    assert len(mk) == 1, "expected exactly one mk() strip builder"
    line = mk[0]
    assert "ggplot(d[!is.na(d[[field]])" in line, (
        "mk() builds the strip from the full frame, so tips with no deposited value still draw a "
        "tile and receive ggplot's default grey50 fill"
    )


def test_empty_string_is_still_mapped_to_na():
    """The NA mapping is the precondition for the fix; keep them together."""
    src = R_FILE.read_text()
    assert "[!nzchar(" in src and "]<-NA" in src, "empty-string to NA mapping missing"


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not available")
def test_absent_value_renders_background_not_grey(tmp_path):
    """Behavioural check: an NA row must not paint a tile."""
    probe = tmp_path / "probe.R"
    out = tmp_path / "probe.png"
    probe.write_text(
        'ok <- suppressWarnings(require(ggplot2, quietly=TRUE))\n'
        'if (!ok) { cat("NO_GGPLOT\\n"); quit(status=0) }\n'
        'd <- data.frame(y=1:2, v=c("soil", NA), stringsAsFactors=FALSE)\n'
        'pal <- c(soil="#8C510A")\n'
        # the patched construction
        'g <- ggplot(d[!is.na(d[["v"]]),,drop=FALSE], aes(x=0,y=y,fill=.data[["v"]])) +\n'
        '     geom_tile(width=.85,height=.96) +\n'
        '     scale_fill_manual(values=pal, na.translate=FALSE) +\n'
        '     ylim(0.5,2.5) + theme_void() + theme(legend.position="none")\n'
        f'ggsave("{out}", g, width=1, height=2, dpi=100, bg="white")\n'
        'cat("OK\\n")\n'
    )
    res = subprocess.run([shutil.which("Rscript"), str(probe)], capture_output=True, text=True)
    if "NO_GGPLOT" in res.stdout:
        pytest.skip("ggplot2 not installed")
    assert res.returncode == 0, res.stderr
    png = out.read_bytes()
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("Pillow not available for pixel check")
    im = Image.open(out).convert("RGB")
    w, h = im.size
    # upper half is the NA row: must be background, never ggplot's grey50 (127,127,127)
    assert im.getpixel((w // 2, h // 4)) != (127, 127, 127), "absent value painted a grey50 tile"
