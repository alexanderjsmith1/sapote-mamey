"""ggtree_rect_heatmap.R: the bound-render preflight names every output the renderer can write,
including `.pages.json`, `.svg` and the `<prefix>_page*` files, before anything is drawn.

Source-level check: an end-to-end bound render needs a gated display receipt, which this test
does not build. The render path that writes each file is listed beside it."""
import re
from pathlib import Path

SRC = (Path(__file__).resolve().parents[1] / "tools" / "ggtree_rect_heatmap.R").read_text(encoding="utf-8")


def _preflight_block():
    i = SRC.index("Bound display render outputs already exist")
    return SRC[SRC.rindex("if (nzchar(display_receipt)", 0, i):i]


def test_preflight_lists_every_fixed_output_written_later():
    block = _preflight_block()
    written = set(re.findall(r'paste0\(out\s*,\s*"(\.[a-z_.]+)"\)', SRC))
    written |= {".pdf", ".png", ".svg"}
    for suffix in sorted(written):
        assert f'"{suffix}"' in block, suffix


def test_preflight_covers_page_files():
    assert 'Sys.glob(paste0(out, "_page*"))' in _preflight_block()
    assert 'paste0(out,"_page",i)' in SRC.replace(" ", "")
