"""The caption band is part of the image, so the page-wording rule applies to it too.

Adopted from the 2026-09-22 Bioassay Figure Studio tool and used across the 2026-09-24 figure sets:
each publication figure carries its caption and methods in a croppable band plus a CAPTION.md
sidecar. v9.7.442 brings the tool into the bundle and holds the band to the same rule as the plot.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import caption_band  # noqa: E402


CAPTION = """# Crude extracts — Candida sp. inhibition by host group

Each point is one bee/wasp isolate's crude extract: the higher of C. albicans and C. auris
inhibition at 48 h, best of the 96-well and 384-well platforms at 120 ug/mL.

Host groups as deposited: Honeybees, Bumblebees, Other bees, Wasps.
"""


def test_flatten_keeps_words_and_drops_markup():
    lines = caption_band.flatten_md("# Title\n\n**bold** and `code` and [link](http://x)\n- item\n")
    assert lines == ["Title", "bold and code and link", "item"]


def test_a_clean_caption_passes_the_band_gate():
    assert caption_band.band_lines(CAPTION)[0].startswith("Crude extracts")


@pytest.mark.parametrize("bad", ["Judgment deferred.", "Similarity is not identity.",
                                 "query strain (AS)", "Class-level hypotheses only."])
def test_banned_wording_on_the_band_is_refused(bad):
    with pytest.raises(caption_band.CaptionBandRefusal, match="CAPTION_BAND_REFUSED"):
        caption_band.band_lines(CAPTION + "\n" + bad + "\n")


def test_band_is_drawn_and_sidecar_is_verbatim(tmp_path):
    pil = pytest.importorskip("PIL.Image")
    plot = tmp_path / "FIG_1_plot_only.png"
    pil.new("RGB", (1200, 800), (255, 255, 255)).save(plot)
    caption = tmp_path / "cap.md"
    caption.write_text(CAPTION, encoding="utf-8")
    out = caption_band.add_band(plot, caption, tmp_path / "out")
    assert out.name == "FIG_1_with_caption.png"
    width, height = pil.open(out).size
    assert width == 1200 and height > 800, "the band is added below the plot, not over it"
    assert (tmp_path / "out" / "FIG_1_with_caption.pdf").is_file()
    assert (tmp_path / "out" / "FIG_1_CAPTION.md").read_text(encoding="utf-8") == CAPTION


def test_a_refused_band_writes_nothing(tmp_path):
    pil = pytest.importorskip("PIL.Image")
    plot = tmp_path / "FIG_2.png"
    pil.new("RGB", (600, 400)).save(plot)
    caption = tmp_path / "cap.md"
    caption.write_text(CAPTION + "\nJudgment deferred.\n", encoding="utf-8")
    assert caption_band.main([str(plot), str(caption), "--outdir", str(tmp_path / "out")]) == 2
    assert not (tmp_path / "out" / "FIG_2_with_caption.png").exists()
