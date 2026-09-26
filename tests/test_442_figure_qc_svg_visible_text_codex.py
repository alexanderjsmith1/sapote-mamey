"""Figure QC must distinguish SVG metadata/definitions from drawn text."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import figure_render_qc as qc  # noqa: E402


def test_svg_text_ignores_definitions_and_metadata(tmp_path):
    svg = tmp_path / "figure.svg"
    svg.write_text('''<svg xmlns="http://www.w3.org/2000/svg">
      <defs><text>judgment deferred</text></defs>
      <metadata><text>claim-safe</text></metadata>
      <g style="display: none"><text>not potency</text></g>
      <text x="10" y="20">Measured <tspan style="visibility: hidden">not bioactivity</tspan>counts</text>
    </svg>''', encoding="utf-8")
    assert qc.svg_text(svg) == ["Measured counts"]


def test_svg_with_only_undrawn_text_requires_another_text_source(tmp_path):
    svg = tmp_path / "figure.svg"
    svg.write_text('''<svg xmlns="http://www.w3.org/2000/svg">
      <defs><text>not production</text></defs>
      <desc><text>query strain</text></desc>
    </svg>''', encoding="utf-8")
    assert qc.svg_text(svg) is None


def test_metadata_only_svg_leaves_png_text_not_checked_without_ocr(tmp_path):
    Image = pytest.importorskip("PIL.Image")
    Draw = pytest.importorskip("PIL.ImageDraw")
    png = tmp_path / "figure.png"
    image = Image.new("RGB", (400, 300), "white")
    Draw.Draw(image).rectangle((50, 50, 350, 250), fill="navy")
    image.save(png, dpi=(300, 300))
    png.with_suffix(".svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><defs><text>metadata only</text></defs></svg>',
        encoding="utf-8")
    results = qc.run([tmp_path], tmp_path, ocr_mode="off")
    assert any(level == "not_checked" for level, _ in results[0][1])
