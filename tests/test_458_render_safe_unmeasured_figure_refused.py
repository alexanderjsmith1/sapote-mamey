"""safe_savefig_dpi refuses a figure it cannot measure instead of passing the requested DPI through.

The except branch's comment said "do not silently pass a possibly-huge figure through" and then
returned requested_dpi unchanged, uncapped.
"""
import pytest

from mamey.render_safe import FigureCanvasTooLargeError, safe_savefig_dpi


class _Unmeasurable:
    def get_size_inches(self):
        raise RuntimeError("no canvas")


class _Small:
    def get_size_inches(self):
        return (4.0, 3.0)


def test_unmeasurable_figure_is_a_typed_refusal():
    with pytest.raises(FigureCanvasTooLargeError, match="could not be measured"):
        safe_savefig_dpi(_Unmeasurable(), 600)


def test_measurable_figure_is_unchanged():
    assert safe_savefig_dpi(_Small(), 300) == 300
