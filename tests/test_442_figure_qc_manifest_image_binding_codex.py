"""A review PNG must be bound to the source SVG and optional manifest digest."""

import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import figure_render_qc as qc  # noqa: E402


def _png(path, color):
    Image = pytest.importorskip("PIL.Image")
    image = Image.new("RGB", (400, 300), "white")
    from PIL import ImageDraw
    ImageDraw.Draw(image).rectangle((50, 50, 350, 250), fill=color)
    image.save(path, dpi=(300, 300))


def _fixture(tmp_path, *, different_review=False, digest=None, missing_source=False):
    source_dir = tmp_path / "source"
    review_dir = tmp_path / "review"
    source_dir.mkdir(); review_dir.mkdir()
    source = source_dir / "figure.png"
    review = review_dir / "figure.png"
    if not missing_source:
        _png(source, "navy")
        source.with_suffix(".svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg"><text>Measured counts</text></svg>',
            encoding="utf-8")
    _png(review, "red" if different_review else "navy")
    expected = digest if digest is not None else hashlib.sha256(review.read_bytes()).hexdigest()
    manifest = review_dir / "MANIFEST.tsv"
    manifest.write_text("png\tsource\tsha256\nfigure.png\t../source/figure.png\t" + expected + "\n",
                        encoding="utf-8")
    return manifest


def _errors(tmp_path, manifest):
    result = qc.run([], tmp_path / "qc", ocr_mode="off", manifest=manifest)
    return [message for level, message in result[0][1] if level == "error"]


def test_review_copy_must_match_source_before_using_source_svg(tmp_path):
    manifest = _fixture(tmp_path, different_review=True)
    result = qc.run([], tmp_path / "qc", ocr_mode="off", manifest=manifest)
    assert any(level == "error" and "review/source PNG mismatch" in message
               for level, message in result[0][1])
    assert any(level == "not_checked" for level, _ in result[0][1])


def test_manifest_sha256_must_match_review_png(tmp_path):
    manifest = _fixture(tmp_path, digest="0" * 64)
    assert any("manifest SHA-256 mismatch" in message for message in _errors(tmp_path, manifest))


def test_missing_source_png_is_an_error(tmp_path):
    manifest = _fixture(tmp_path, missing_source=True)
    assert any("source PNG missing" in message for message in _errors(tmp_path, manifest))
