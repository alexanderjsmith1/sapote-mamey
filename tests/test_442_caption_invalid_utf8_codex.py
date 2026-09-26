"""Invalid caption bytes cannot be reported as clean by either caption reader."""

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from caption_guard import CaptionUnreadableError, scan_paths  # noqa: E402
import figure_render_qc as qc  # noqa: E402


def test_caption_guard_strict_refuses_invalid_utf8(tmp_path):
    caption = tmp_path / "figure_CAPTION.md"
    caption.write_bytes(b"Counts of generic observations.\xff\n")
    with pytest.raises(CaptionUnreadableError, match="CAPTION_UNREADABLE"):
        scan_paths([caption])


def test_caption_guard_lenient_marks_invalid_utf8_unreadable(tmp_path):
    caption = tmp_path / "figure_CAPTION.md"
    caption.write_bytes(b"Counts of generic observations.\xff\n")
    result = scan_paths([caption], strict=False)
    assert "__unreadable__" in result
    assert str(caption) in [path for path, _ in result["__unreadable__"]]


def test_render_qc_refuses_invalid_utf8_caption(tmp_path):
    image = pytest.importorskip("PIL.Image")
    draw = pytest.importorskip("PIL.ImageDraw")
    png = tmp_path / "figure.png"
    canvas = image.new("RGB", (1200, 800), "white")
    painter = draw.Draw(canvas)
    painter.rectangle((100, 100, 700, 600), fill=(40, 60, 90))
    canvas.save(png, dpi=(300, 300))
    (tmp_path / "figure.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"><text>Counts</text></svg>')
    (tmp_path / "figure_plot_only.png").write_bytes(png.read_bytes())
    (tmp_path / "figure.pdf").write_bytes(b"%PDF-1.4\n")
    (tmp_path / "figure_CAPTION.md").write_bytes(b"Counts of generic observations.\xff\n")
    flags = qc.check_files(png)
    assert any(level == "error" and "unreadable" in message for level, message in flags)
    assert qc.main([str(tmp_path), "--ocr", "off"]) == 2
