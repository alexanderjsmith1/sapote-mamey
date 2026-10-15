"""figure_render_qc must find the companions that tools/caption_band.py writes.

caption_band.py writes <base>_with_caption.png next to <base>_plot_only.png and <base>_CAPTION.md.
The QC looked for <base>_with_caption_plot_only.png and <base>_with_caption_CAPTION.md, so every
captioned figure folder made the house way drew a false "no caption file" warning (moss S4, 12 Oct).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import figure_render_qc as q  # noqa: E402


def _folder(tmp_path):
    for name in ("FIG_plot_only.png", "FIG_with_caption.png", "FIG_with_caption.pdf"):
        (tmp_path / name).write_bytes(b"x")
    (tmp_path / "FIG_CAPTION.md").write_text("Caption.\n")
    return tmp_path / "FIG_with_caption.png"


def test_caption_band_names_find_their_caption(tmp_path):
    assert q.caption_file(_folder(tmp_path)) == tmp_path / "FIG_CAPTION.md"


def test_caption_band_names_find_their_plot_only(tmp_path):
    flags = q.check_files(_folder(tmp_path))
    assert not any("_plot_only" in msg for _, msg in flags)


def test_plain_stems_are_unchanged(tmp_path):
    (tmp_path / "G.png").write_bytes(b"x")
    assert any("_plot_only" in msg for _, msg in q.check_files(tmp_path / "G.png"))


def test_a_captioned_copy_beside_its_figure_is_not_checked_twice(tmp_path):
    for name in ("FIG.png", "FIG_plot_only.png", "FIG_with_caption.png"):
        (tmp_path / name).write_bytes(b"x")
    assert q.find_figures([tmp_path]) == [tmp_path / "FIG.png"]


def test_a_captioned_figure_on_its_own_is_still_checked(tmp_path):
    for name in ("FIG_plot_only.png", "FIG_with_caption.png"):
        (tmp_path / name).write_bytes(b"x")
    assert q.find_figures([tmp_path]) == [tmp_path / "FIG_with_caption.png"]
