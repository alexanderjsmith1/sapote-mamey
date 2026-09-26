"""Banned figure wording must be checked as visible text."""
import pytest

from mamey.figure_policy import (
    FigureTextRefusal, assert_no_banned_figure_text,
    figure_text_violations, svg_visible_text,
)


@pytest.mark.parametrize("svg", [
    "<svg><text>Judgment&#32;deferred</text></svg>",
    "<svg><text>Judgment&#160;deferred</text></svg>",
    "<svg><text>Judgment<tspan>\n deferred</tspan></text></svg>",
])
def test_svg_visible_spacing_cannot_hide_banned_words(svg):
    with pytest.raises(FigureTextRefusal, match="FIGURE_TEXT_BANNED"):
        assert_no_banned_figure_text(svg_visible_text(svg), figure_id="GENERIC")


def test_matplotlib_multiline_text_cannot_hide_banned_words():
    assert figure_text_violations(["Judgment\ndeferred"]) == ["Judgment deferred"]


def test_metadata_is_not_treated_as_visible_text():
    svg = "<svg><metadata>Judgment&#32;deferred</metadata><text>Honeybees</text></svg>"
    assert figure_text_violations(svg_visible_text(svg)) == []


def test_matplotlib_tick_labels_are_checked():
    import matplotlib.pyplot as plt
    from mamey.figure_policy import matplotlib_visible_text

    fig, ax = plt.subplots()
    try:
        ax.set_xticks([0], ["Judgment deferred"])
        with pytest.raises(FigureTextRefusal, match="FIGURE_TEXT_BANNED"):
            assert_no_banned_figure_text(matplotlib_visible_text(fig))
    finally:
        plt.close(fig)


def test_matplotlib_figure_legend_is_checked():
    import matplotlib.pyplot as plt
    from mamey.figure_policy import matplotlib_visible_text

    fig, ax = plt.subplots()
    try:
        line, = ax.plot([0, 1], [0, 1])
        fig.legend([line], ["Not identity"])
        with pytest.raises(FigureTextRefusal, match="FIGURE_TEXT_BANNED"):
            assert_no_banned_figure_text(matplotlib_visible_text(fig))
    finally:
        plt.close(fig)
