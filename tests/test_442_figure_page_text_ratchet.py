"""The page-text ratchet: direct savefig callers are checked, and the known-site list only shrinks."""
from __future__ import annotations

import traceback
from pathlib import Path

import pytest

matplotlib = pytest.importorskip("matplotlib")
from matplotlib.figure import Figure  # noqa: E402

import figure_page_text_ratchet as fpt  # noqa: E402
from mamey.figure_policy import FigureTextRefusal  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def _fig(title: str) -> Figure:
    fig = Figure(figsize=(2, 1))
    fig.add_subplot().set_title(title)
    return fig


def test_the_session_wraps_savefig():
    assert hasattr(Figure.savefig, "page_text_ratchet")


def test_an_unlisted_site_that_draws_banned_text_is_refused():
    ratchet = fpt.PageTextRatchet(known=set())
    with pytest.raises(FigureTextRefusal, match="FIGURE_TEXT_BANNED"):
        ratchet.check(_fig("KCB = similarity, not identity"), "mamey/new_renderer.py::draw")


def test_a_listed_site_is_tolerated_and_a_clean_one_is_reported_cleared():
    ratchet = fpt.PageTextRatchet(known={"mamey/a.py::f", "mamey/b.py::g"})
    ratchet.check(_fig("KCB = similarity, not identity"), "mamey/a.py::f")
    ratchet.check(_fig("Regions per genome"), "mamey/b.py::g")
    assert ratchet.cleared_sites() == ["mamey/b.py::g"]


def test_ordinary_words_pass_an_unlisted_site():
    fpt.PageTextRatchet(known=set()).check(_fig("Identity of isolates by host"), "mamey/x.py::f")


def test_the_site_is_the_innermost_bundle_frame_outside_tests():
    stack = [traceback.FrameSummary(str(ROOT / "mamey" / "render_brief.py"), 10, "render_brief"),
             traceback.FrameSummary(str(ROOT / "mamey" / "figures_extra.py"), 50, "_save"),
             traceback.FrameSummary(str(ROOT / "tests" / "test_x.py"), 5, "test_x")]
    assert fpt.calling_site(stack) == "mamey/figures_extra.py::_save"


def test_the_shared_save_path_is_left_to_its_own_check():
    stack = [traceback.FrameSummary(str(ROOT / "mamey" / "cohort_figures.py"), 10, "draw"),
             traceback.FrameSummary(str(ROOT / "mamey" / "figure_save.py"), 120, "save_figure")]
    assert fpt.calling_site(stack) == ""


def test_a_shared_save_helper_is_skipped_so_the_renderer_is_named():
    stack = [traceback.FrameSummary(str(ROOT / "mamey" / "cross_strain_figures.py"), 209, "_save_chart"),
             traceback.FrameSummary(str(ROOT / "mamey" / "figure_theme.py"), 190, "save_figure_pair")]
    assert fpt.calling_site(stack) == "mamey/cross_strain_figures.py::_save_chart"


def test_a_pseudo_frame_is_not_a_renderer():
    stack = [traceback.FrameSummary("<stdin>", 1, "<module>"),
             traceback.FrameSummary(str(ROOT / "tests" / "test_x.py"), 5, "test_x")]
    assert fpt.calling_site(stack) == ""


def test_every_listed_site_names_a_function_that_exists():
    for site in sorted(fpt.load_known_sites()):
        rel, func = site.split("::")
        src = (ROOT / rel).read_text(encoding="utf-8")
        assert f"def {func}(" in src, f"stale entry {site}: delete it"


def test_known_site_exceptions_cannot_grow(tmp_path):
    proposed = tmp_path / "known_sites.txt"
    proposed.write_text(fpt.KNOWN_SITES_FILE.read_text(encoding="utf-8") +
                        "\nmamey/cohort_figures_extended.py::fig_kcb_novelty\n",
                        encoding="utf-8")
    with pytest.raises(ValueError, match="new figure page text exception"):
        fpt.load_known_sites(proposed)


def test_known_site_exceptions_can_shrink(tmp_path):
    proposed = tmp_path / "known_sites.txt"
    proposed.write_text("mamey/collection_figures.py::_save\n", encoding="utf-8")
    assert fpt.load_known_sites(proposed) == {"mamey/collection_figures.py::_save"}
