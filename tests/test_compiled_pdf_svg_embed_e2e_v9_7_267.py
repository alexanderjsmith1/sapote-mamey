"""v9.7.267 — end-to-end lock for the SVG-embed render path (.265/.266).

Builds a tiny package whose compiled markdown references a locus-map *SVG*, runs the real
`_render_compiled_pdf` (pandoc + xelatex via md_to_pdf.sh), and asserts the SVG was preserved through
vector PDF conversion — rather than rasterized or dropped. Skips cleanly where
the PDF toolchain or cairosvg is unavailable, so it locks the path wherever the toolchain exists (the
whole point of the `render` extra) without breaking bare environments."""
import shutil
from pathlib import Path

import pytest

try:
    import cairosvg  # noqa: F401
except Exception as _cairo_err:  # ImportError, or OSError when native libcairo fails to load
    pytest.skip(f"cairosvg unavailable: {_cairo_err}", allow_module_level=True)
from mamey.compile_report import _render_compiled_pdf, _svg_to_pdf

_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="160" height="90">'
        '<rect width="160" height="90" fill="#4a90d9"/>'
        '<text x="12" y="50" fill="white" font-size="16">locus map</text></svg>')

_TOOLCHAIN = all(shutil.which(tool) for tool in ("pandoc", "xelatex", "pdffonts", "pdftotext"))


def test_svg_to_pdf_produces_vector_pdf(tmp_path):
    src = tmp_path / "locus.svg"; src.write_text(_SVG, encoding="utf-8")
    dst = tmp_path / "locus.svg.vector.pdf"
    assert _svg_to_pdf(src, dst) is True
    assert dst.read_bytes()[:4] == b"%PDF"


@pytest.mark.skipif(not _TOOLCHAIN, reason="pandoc/xelatex not installed")
def test_compiled_pdf_preserves_converted_svg_end_to_end(tmp_path):
    pkg = tmp_path
    (pkg / "locus_maps").mkdir()
    (pkg / "locus_maps" / "BGC001_locus_map.svg").write_text(_SVG, encoding="utf-8")
    md = ("# Compiled report\n\n"
          "## Locus map\n\n"
          "![BGC001 locus map](locus_maps/BGC001_locus_map.svg)\n\n"
          "Some prose after the figure.\n")
    out_pdf = pkg / "compiled.pdf"
    res = _render_compiled_pdf(md, out_pdf, pkg)

    # the render must succeed and report the SVG as vector-preserved, not dropped
    assert res.get("status") == "WRITTEN", res
    assert res.get("converted_figs", 0) >= 1, res
    assert res.get("embedded_pdf_qa", {}).get("vector_fonts") == "EMBEDDED", res
    assert res.get("embedded_pdf_qa", {}).get("live_text_probe") == "VERIFIED", res
    assert out_pdf.exists() and out_pdf.stat().st_size > 0

    # the vector intermediary sits next to the SVG; no screen PNG is created.
    assert (pkg / "locus_maps" / "BGC001_locus_map.svg.vector.pdf").exists()
    assert not (pkg / "locus_maps" / "BGC001_locus_map.svg.png").exists()
