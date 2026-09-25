"""figure_render_qc: text drawn inside a figure is checked, and unread text is never reported clean."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
PIL = pytest.importorskip("PIL")
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import figure_render_qc as qc  # noqa: E402
from caption_guard import check_caption  # noqa: E402


def _png(path: Path, ink: bool = True, text: str | None = None, size=(1200, 800)) -> Path:
    im = Image.new("RGB", size, "white")
    d = ImageDraw.Draw(im)
    if ink:
        d.rectangle([100, 100, 700, 600], fill=(40, 60, 90))
    if text:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 48)
        except OSError:
            font = ImageFont.load_default()
        d.text((60, 680), text, fill="black", font=font)
    im.save(path, dpi=(300, 300))
    return path


def _svg(path: Path, *lines: str) -> None:
    body = "".join(f'<text x="10" y="{20 * (i + 1)}">{t}</text>' for i, t in enumerate(lines))
    path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200">{body}</svg>')


def _flags(results, name):
    return next(fl for f, fl in results if f.name == name)


def _complete(folder: Path, stem: str, caption: str = "Counts of regions per isolate.") -> None:
    _png(folder / f"{stem}_plot_only.png")
    (folder / f"{stem}.pdf").write_bytes(b"%PDF-1.4\n")
    (folder / f"{stem}_CAPTION.md").write_text(caption)


def test_claim_wording_drawn_in_the_figure_is_an_error(tmp_path):
    _png(tmp_path / "fig_net.png")
    _svg(tmp_path / "fig_net.svg", "query strain (AS)", "Not identity, not production. Judgment deferred.")
    _complete(tmp_path, "fig_net")
    res = qc.run([tmp_path], tmp_path, ocr_mode="off")
    msgs = " | ".join(m for lv, m in _flags(res, "fig_net.png") if lv == "error")
    assert "query strain" in msgs and "judgment deferred" in msgs
    assert qc.main([str(tmp_path), "--ocr", "off"]) == 2


def test_scientific_class_level_is_not_flagged(tmp_path):
    _png(tmp_path / "fig_cls.png")
    _svg(tmp_path / "fig_cls.svg", "Class-level composition of BGCs across 26 isolates")
    _complete(tmp_path, "fig_cls")
    res = qc.run([tmp_path], tmp_path, ocr_mode="off")
    assert [m for lv, m in _flags(res, "fig_cls.png") if lv in ("error", "warn")] == []
    assert qc.main([str(tmp_path), "--ocr", "off"]) == 0


def test_raw_markup_and_na_are_errors(tmp_path):
    _png(tmp_path / "fig_raw.png")
    _svg(tmp_path / "fig_raw.svg", "&lt;i&gt;Streptomyces&lt;/i&gt; sp.", "Host: NA", "line one\\nline two")
    _complete(tmp_path, "fig_raw")
    msgs = " | ".join(m for lv, m in _flags(qc.run([tmp_path], tmp_path, ocr_mode="off"), "fig_raw.png"))
    assert "raw HTML tag" in msgs and "NA / NaN / Inf" in msgs and "literal \\n" in msgs


def test_unread_text_is_not_checked_never_clean(tmp_path):
    _png(tmp_path / "fig_png_only.png")
    _complete(tmp_path, "fig_png_only")
    res = qc.run([tmp_path], tmp_path, ocr_mode="off")
    assert any(lv == "not_checked" for lv, _ in _flags(res, "fig_png_only.png"))
    assert qc.main([str(tmp_path), "--ocr", "off"]) == 0
    assert "figure text not checked" in (tmp_path / "RENDER_QC.md").read_text()


def test_ocr_require_fails_when_ocr_is_unavailable(tmp_path, monkeypatch):
    _png(tmp_path / "fig_png_only.png")
    _complete(tmp_path, "fig_png_only")
    monkeypatch.setattr(qc.shutil, "which", lambda _name: None)
    assert qc.main([str(tmp_path), "--ocr", "require"]) == 2
    assert qc.main([str(tmp_path), "--ocr", "auto"]) == 0


def test_near_blank_image_is_an_error(tmp_path):
    _png(tmp_path / "fig_blank.png", ink=False)
    _svg(tmp_path / "fig_blank.svg", "Title")
    _complete(tmp_path, "fig_blank")
    assert any("near-blank" in m for lv, m in _flags(qc.run([tmp_path], tmp_path, ocr_mode="off"), "fig_blank.png"))


def test_bioassay_material_must_be_in_the_file_name(tmp_path):
    for stem, text in [("fig_227c_candida_scatter", "Candida sp. inhibition"),
                       ("fig_227g_candida_scatter_crude", "Crude extracts: Candida sp. inhibition")]:
        _png(tmp_path / f"{stem}.png")
        _svg(tmp_path / f"{stem}.svg", text)
        _complete(tmp_path, stem)
    res = qc.run([tmp_path], tmp_path, ocr_mode="off", bioassay=True)
    assert any("file name does not say" in m for lv, m in _flags(res, "fig_227c_candida_scatter.png") if lv == "error")
    assert not [m for lv, m in _flags(res, "fig_227g_candida_scatter_crude.png") if lv == "error"]


def test_caption_file_wording_warns_but_drawn_wording_errors(tmp_path):
    _png(tmp_path / "fig_cap.png")
    _svg(tmp_path / "fig_cap.svg", "Counts")
    _complete(tmp_path, "fig_cap", caption="Networks of shared families. Descriptive screening, not potency.")
    fl = _flags(qc.run([tmp_path], tmp_path, ocr_mode="off"), "fig_cap.png")
    assert not [m for lv, m in fl if lv == "error"]
    assert any(lv == "warn" and "fig_cap_CAPTION.md" in m for lv, m in fl)


def test_plot_only_and_replaced_are_not_units(tmp_path):
    _png(tmp_path / "fig_a.png")
    _complete(tmp_path, "fig_a")
    (tmp_path / "_replaced").mkdir()
    _png(tmp_path / "_replaced" / "fig_old.png")
    names = [f.name for f in qc.find_figures([tmp_path])]
    assert names == ["fig_a.png"]


@pytest.mark.parametrize("phrase", ["query strain", "not identity", "not production", "not potency",
                                    "not bioactivity", "descriptive screening", "not compound identity"])
def test_caption_guard_blocks_the_2026_09_24_phrases(phrase):
    assert check_caption(f"Figure 3. Shared families. {phrase.capitalize()}.", raises=False)


@pytest.mark.skipif(sys.platform != "darwin" or not shutil.which("swiftc"), reason="macOS Vision OCR only")
def test_ocr_reads_claim_text_off_a_png(tmp_path):
    _png(tmp_path / "fig_ocr.png", text="Judgment deferred", size=(1400, 800))
    _complete(tmp_path, "fig_ocr")
    res = qc.run([tmp_path], tmp_path, ocr_mode="auto")
    assert any("judgment deferred" in m for lv, m in _flags(res, "fig_ocr.png") if lv == "error")


def test_manifest_checks_companions_at_the_source_and_carries_defect_notes(tmp_path):
    src = tmp_path / "FIG_035c"
    src.mkdir()
    _png(src / "FIG_035c_counts.png")
    _svg(src / "FIG_035c_counts.svg", "Regions per isolate")
    _complete(src, "FIG_035c_counts")
    review = tmp_path / "review" / "2_Genome"
    review.mkdir(parents=True)
    _png(review / "143_FIG_035c_counts.png")
    _png(review / "144_FIG_035b_counts.png")
    (tmp_path / "review" / "MANIFEST.tsv").write_text(
        "n\tsection\treview_file\tfigure_folder\tsource_png\tnote\n"
        "143\t2_Genome\t143_FIG_035c_counts.png\tFIG_035c\tFIG_035c_counts.png\tloose for all genomes\n"
        "144\t2_Genome\t144_FIG_035b_counts.png\tFIG_035c\tFIG_035c_counts.png\tDO NOT USE: mixed strictness\n")
    res = qc.run([], tmp_path / "review", ocr_mode="off", manifest=tmp_path / "review" / "MANIFEST.tsv")
    good = _flags(res, "143_FIG_035c_counts.png")
    assert [m for lv, m in good if lv in ("error", "warn", "not_checked")] == []
    bad = _flags(res, "144_FIG_035b_counts.png")
    assert any(lv == "error" and "mixed strictness" in m for lv, m in bad)
    assert qc.main(["--manifest", str(tmp_path / "review" / "MANIFEST.tsv"), "--ocr", "off"]) == 2
