"""A strain with no data must not be drawn at the origin.

`_median([])` returns `0.0`. Where the result sits next to a count that is also zero, a reader can
still tell absence from measurement — a strain at (0 genes, 0) is visibly a no-data strain. Where
the count is not carried, that 0.0 becomes a data point on the axis.

FS042 is the unrecoverable case: **both axes are medians and neither carries a count**. A protein
cannot be 0 aa, so every point it drew on an axis was necessarily absent data rendered as present.
FS045 is the same defect in a heatmap, where an empty cell reads as *shortest* on the colour scale
rather than *absent*.

This project does not coerce one evidence state into another anywhere else. A figure is not an
exception.
"""
import pytest

from mamey.interactive_figures.figure_set_renderer import _median, _median_or_none


def test_the_lenient_helper_still_returns_zero_for_empty():
    """Unchanged on purpose — callers that pair it with a count rely on this, and changing it
    would be a much larger blast radius than the defect warrants."""
    assert _median([]) == 0.0
    assert _median([10, 20, 30]) == 20.0


def test_the_strict_helper_distinguishes_absent_from_zero():
    assert _median_or_none([]) is None
    assert _median_or_none([10, 20, 30]) == 20.0
    # a genuine zero is still a zero, not absence
    assert _median_or_none([0, 0]) == 0.0


def test_a_real_zero_and_an_absence_are_not_the_same_object():
    """The distinction the four-state rule exists to protect."""
    assert _median_or_none([0]) is not None
    assert _median_or_none([]) is None
    assert _median_or_none([0]) == 0.0


@pytest.mark.parametrize("values,expected", [
    ([], None),
    ([1], 1.0),
    ([1, 2], 1.5),
    ([5, 1, 3], 3.0),
])
def test_strict_median_matches_the_lenient_one_whenever_there_is_data(values, expected):
    got = _median_or_none(values)
    assert got == expected
    if values:
        assert got == _median(values), "the two helpers must agree whenever data exists"
