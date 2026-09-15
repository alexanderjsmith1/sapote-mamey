"""v9.7.430: focal-tip colour is a knob (GG_FOCAL_COLOUR), defaulting to plain black.

The previous `tools/ggtree_rect_heatmap.R` hard-coded
`colour = "#bb0000"` for query tip labels with no override, contradicting the standing figure
ruling (query tips PLAIN BLACK, no red). Same pattern as the existing GG_FOCAL_FACE knob
(`test_rect_renderer_defaults_v9_7_416.py`), and deliberately scoped to this ONE renderer only —
see the card for why `tools/ggtree_placement.R` / `ggtree_placement_hostcolour.R` /
`ggtree_placement_bioassay.R` are explicitly OUT of this fix (a different, captioned, intentional
red/blue/grey convention for EPA-ng placement trees, not the same defect).
"""
from pathlib import Path
import subprocess
import shutil
import pytest

RS = Path(__file__).resolve().parent.parent / "tools" / "ggtree_rect_heatmap.R"


def _s():
    assert RS.exists(), "renderer required"
    return RS.read_text()


def test_focal_colour_is_a_knob_defaulting_to_black():
    s = _s()
    assert 'Sys.getenv("GG_FOCAL_COLOUR", "#000000")' in s
    assert 'colour = focal_colour' in s


def test_hardcoded_red_is_gone():
    # The literal must no longer be assigned directly to the geom_tiplab colour arg.
    s = _s()
    assert 'colour = "#bb0000"' not in s


def test_focal_face_knob_still_present():
    # Regression: don't clobber the sibling GG_FOCAL_FACE knob while adding this one.
    s = _s()
    assert 'Sys.getenv("GG_FOCAL_FACE", "plain")' in s


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="R not installed in this environment")
def test_render_actually_resolves_the_real_source_line_correctly():
    """End-to-end against the ACTUAL shipped line (not a hand-copied duplicate): extract the
    `focal_colour <- Sys.getenv(...)` assignment straight out of the renderer file's text and
    execute exactly that line in R, then confirm the resolved value with the env var unset
    (default) and set (override). On the unpatched source this assignment doesn't exist at all,
    so extraction itself fails first — a stronger fail-before than a string-in-source check."""
    import re

    src = _s()
    m = re.search(r'focal_colour\s*<-\s*Sys\.getenv\("GG_FOCAL_COLOUR",\s*"#000000"\)', src)
    assert m, "no focal_colour <- Sys.getenv(...) assignment found in the shipped renderer source"
    r_line = m.group(0)

    r1 = subprocess.run(
        ["Rscript", "-e", f'{r_line}; cat(focal_colour)'],
        capture_output=True, text=True, env={"PATH": "/usr/local/bin:/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
    )
    assert r1.returncode == 0, r1.stderr
    assert r1.stdout.strip() == "#000000"

    r2 = subprocess.run(
        ["Rscript", "-e", f'{r_line}; cat(focal_colour)'],
        capture_output=True, text=True,
        env={"PATH": "/usr/local/bin:/usr/bin:/bin", "GG_FOCAL_COLOUR": "#bb0000", "PYTHONDONTWRITEBYTECODE": "1"},
    )
    assert r2.returncode == 0, r2.stderr
    assert r2.stdout.strip() == "#bb0000"
