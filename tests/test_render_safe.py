import pytest as _pytest
_pytest.importorskip("matplotlib")  # SKIP (not error) when figure stack absent
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from mamey.render_safe import clean_scalar, shorten_label, wrap_label, has_forbidden_render_string, figure_text_overlap_report


class FakeNumpyInt:
    def item(self):
        return 48


def test_clean_scalar_removes_numpy_reprs():
    assert clean_scalar(FakeNumpyInt()) == 48
    assert clean_scalar('np.int64(48)') == '48'
    assert clean_scalar(float('nan')) == ''
    assert not has_forbidden_render_string(str(clean_scalar('np.int64(48)')))


def test_shorten_and_wrap_labels_are_bounded():
    s = 'NODE_12345678901234567890 very long knownclusterblast label product family name'
    assert len(shorten_label(s, max_chars=24)) <= 24
    wrapped = wrap_label(s, width=16, max_lines=2)
    assert len(wrapped.splitlines()) <= 2


def test_figure_overlap_report_detects_obvious_collision():
    fig, ax = plt.subplots()
    ax.text(0.5, 0.5, 'A')
    ax.text(0.5, 0.5, 'B')
    warnings = figure_text_overlap_report(fig)
    plt.close(fig)
    assert warnings
