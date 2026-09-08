"""A10 shared paired-save helper and legacy inventory contract."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from mamey.figure_save import FigureSaveRefusal, NativeSvgFigure, audit_figure_outputs, save_figure
from mamey.figure_theme import CLAIM_SAFETY
from mamey.interactive_figures.three_channel_evidence_matrix import write_matrix


ROOT = Path(__file__).resolve().parents[1]


class _FakeCairoSVG:
    @staticmethod
    def svg2png(*, bytestring, output_width):
        assert CLAIM_SAFETY.encode() in bytestring
        assert output_width == 2160
        return b"\x89PNG\r\n\x1a\nsynthetic-raster"


def test_native_svg_writes_pair_and_appends_receipt(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "cairosvg", _FakeCairoSVG)
    package = tmp_path / "package"
    svg = f'<svg xmlns="http://www.w3.org/2000/svg"><text>{CLAIM_SAFETY}</text></svg>'
    receipt = save_figure(
        NativeSvgFigure(svg), figure_id="SYNTHETIC_FIGURE", out_stem=package / "figures" / "one",
        renderer="synthetic-native-svg", package_dir=package, provenance="synthetic fixture",
    )

    assert (package / "figures" / "one.png").is_file()
    assert (package / "figures" / "one.svg").is_file()
    rows = [json.loads(line) for line in (package / "figure_receipts.jsonl").read_text().splitlines()]
    assert rows == [{key: value for key, value in receipt.items() if key != "receipt_locator"}]
    assert audit_figure_outputs(package)["figures"] == [{
        "png": "figures/one.png", "svg": "figures/one.svg", "state": "RECEIPT_BOUND_PAIR"
    }]


def test_unpaired_png_is_legacy_unverified_and_never_regenerated(tmp_path):
    package = tmp_path / "package"
    package.mkdir()
    png = package / "old.png"
    original = b"\x89PNG\r\n\x1a\nlegacy"
    png.write_bytes(original)

    audit = audit_figure_outputs(package)
    assert audit["status"] == "PASS_WITH_LEGACY"
    assert audit["figures"] == [{"png": "old.png", "svg": None, "state": "LEGACY_UNVERIFIED"}]
    assert png.read_bytes() == original
    assert not png.with_suffix(".svg").exists()
    assert not (package / "figure_receipts.jsonl").exists()


def test_tampered_bound_png_is_legacy_unverified(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "cairosvg", _FakeCairoSVG)
    package = tmp_path / "package"
    svg = f'<svg xmlns="http://www.w3.org/2000/svg"><text>{CLAIM_SAFETY}</text></svg>'
    save_figure(
        NativeSvgFigure(svg), figure_id="SYNTHETIC_FIGURE", out_stem=package / "one",
        renderer="synthetic-native-svg", package_dir=package, provenance="synthetic fixture",
    )
    png = package / "one.png"
    png.write_bytes(png.read_bytes() + b"tampered")

    audit = audit_figure_outputs(package)
    assert audit["figures"] == [{"png": "one.png", "svg": "one.svg", "state": "LEGACY_UNVERIFIED"}]


def test_matplotlib_figure_gets_footer_pair_and_receipt(tmp_path):
    plt = pytest.importorskip("matplotlib.pyplot")
    package = tmp_path / "package"
    fig, axis = plt.subplots()
    axis.plot([0, 1], [0, 1])
    try:
        receipt = save_figure(
            fig, figure_id="SYNTHETIC_MATPLOTLIB", out_stem=package / "mpl",
            renderer="synthetic-matplotlib", package_dir=package, provenance="synthetic fixture",
        )
        assert {text.get_text() for text in fig.texts} >= {
            CLAIM_SAFETY, "synthetic fixture | Candidate Only — judgment deferred"
        }
        assert set(receipt["outputs"]) == {"png", "svg"}
        assert audit_figure_outputs(package)["status"] == "PASS"
    finally:
        plt.close(fig)


def test_output_stem_must_be_inside_package(tmp_path):
    svg = f'<svg xmlns="http://www.w3.org/2000/svg"><text>{CLAIM_SAFETY}</text></svg>'
    with pytest.raises(FigureSaveRefusal, match="out_stem must be contained"):
        save_figure(
            NativeSvgFigure(svg), figure_id="SYNTHETIC", out_stem=tmp_path / "outside",
            renderer="synthetic", package_dir=tmp_path / "package", provenance="synthetic fixture",
        )


def test_native_rasterizer_failure_is_typed_and_writes_nothing(tmp_path, monkeypatch):
    class BrokenCairoSVG:
        @staticmethod
        def svg2png(**_kwargs):
            raise OSError("native cairo unavailable")

    monkeypatch.setitem(sys.modules, "cairosvg", BrokenCairoSVG)
    package = tmp_path / "package"
    svg = f'<svg xmlns="http://www.w3.org/2000/svg"><text>{CLAIM_SAFETY}</text></svg>'
    with pytest.raises(FigureSaveRefusal, match="FIGURE_RENDER_FAILED"):
        save_figure(
            NativeSvgFigure(svg), figure_id="SYNTHETIC", out_stem=package / "one",
            renderer="synthetic", package_dir=package, provenance="synthetic fixture",
        )
    assert not (package / "one.png").exists()
    assert not (package / "one.svg").exists()
    assert not (package / "figure_receipts.jsonl").exists()


def test_three_channel_png_path_uses_canonical_pair_receipt(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "cairosvg", _FakeCairoSVG)
    fixture = ROOT / "examples" / "figure_factory" / "three_channel_evidence_matrix.synthetic.json"
    package = tmp_path / "package"

    receipt = write_matrix(fixture, package, emit_png=True)

    assert receipt["paired_figure_receipt"]["receipt_locator"] == "figure_receipts.jsonl"
    assert audit_figure_outputs(package)["status"] == "PASS"
    assert (package / "three_channel_evidence_matrix.receipt.json").is_file()


def test_output_symlink_is_refused_without_touching_target(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "cairosvg", _FakeCairoSVG)
    package = tmp_path / "package"
    package.mkdir()
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"keep")
    (package / "one.png").symlink_to(outside)
    svg = f'<svg xmlns="http://www.w3.org/2000/svg"><text>{CLAIM_SAFETY}</text></svg>'

    with pytest.raises(FigureSaveRefusal, match="output path is a symlink"):
        save_figure(
            NativeSvgFigure(svg), figure_id="SYNTHETIC", out_stem=package / "one",
            renderer="synthetic", package_dir=package, provenance="synthetic fixture",
        )
    assert outside.read_bytes() == b"keep"
