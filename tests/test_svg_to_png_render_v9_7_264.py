"""v9.7.264 — locus-map SVGs embed in the compiled PDF via a soft SVG->PNG converter
instead of being dropped. The converter is optional (cairosvg/rsvg/inkscape); with none present
the render still succeeds, dropping SVGs as before. These tests exercise the helper directly."""
from pathlib import Path
import pytest
from mamey.compile_report import _svg_to_png

_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24">'
        '<rect width="24" height="24" fill="teal"/></svg>')


def _have_converter():
    import shutil
    if shutil.which("rsvg-convert") or shutil.which("inkscape"):
        return True
    try:
        import cairosvg  # noqa: F401
        return True
    except Exception:
        return False


def test_svg_to_png_converts_when_a_converter_is_present(tmp_path):
    if not _have_converter():
        pytest.skip("no SVG converter installed in this environment")
    src = tmp_path / "locus.svg"; src.write_text(_SVG, encoding="utf-8")
    dst = tmp_path / "locus.svg.png"
    assert _svg_to_png(src, dst) is True
    assert dst.exists() and dst.stat().st_size > 0
    assert dst.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"  # real PNG signature


def test_svg_to_png_returns_false_and_does_not_raise_on_garbage(tmp_path):
    # A soft dependency must never raise into the build — bad input returns False, caller drops the fig.
    src = tmp_path / "bad.svg"; src.write_text("not svg at all", encoding="utf-8")
    dst = tmp_path / "bad.png"
    assert _svg_to_png(src, dst) is False
