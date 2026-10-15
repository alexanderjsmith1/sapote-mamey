"""Cohort rendering must preserve caller styles and its own construction style."""
import importlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest


CALLER_STYLE = {
    "font.size": 17, "axes.titlesize": 19, "axes.titleweight": "normal",
    "figure.dpi": 81, "savefig.dpi": 83, "axes.edgecolor": "red",
    "savefig.bbox": None, "savefig.pad_inches": 0.1, "font.family": "monospace",
}


def snapshot():
    return {key: repr(matplotlib.rcParams[key]) for key in CALLER_STYLE}


def test_import_preserves_caller_style():
    with matplotlib.rc_context(CALLER_STYLE):
        before = snapshot()
        import mamey.cohort_figures as cohort
        importlib.reload(cohort)
        assert snapshot() == before


@pytest.mark.parametrize("save_fails", [False, True])
def test_direct_heatmap_scopes_construction_and_save_style(tmp_path, monkeypatch, save_fails):
    import mamey.cohort_figures as cohort
    captured = []

    def save(fig, **kwargs):
        captured.append(fig)
        assert fig.dpi == 300
        assert fig.axes[0].title.get_fontsize() == 12
        assert fig.axes[0].title.get_fontweight() == "bold"
        assert fig.axes[0].title.get_fontfamily() == ["DejaVu Sans"]
        assert matplotlib.rcParams["font.size"] == 9
        assert matplotlib.rcParams["savefig.bbox"] == "tight"
        assert matplotlib.rcParams["savefig.pad_inches"] == 0.35
        assert kwargs["renderer"] == "cohort_figures"
        if save_fails:
            raise OSError("synthetic save failure")

    monkeypatch.setattr(cohort, "save_figure", save)
    monkeypatch.setitem(cohort.GENUS, "SYN-971", "Example genus")
    with matplotlib.rc_context(CALLER_STYLE):
        before = snapshot()
        args = ([[1]], ["Synthetic row"], ["SYN-971"],
                {"SYN-971": {"privacy": {"effective_release": "PUBLIC"}}},
                "Synthetic style check", "SYN_style", tmp_path)
        try:
            if save_fails:
                with pytest.raises(OSError, match="synthetic save failure"):
                    cohort.heatmap(*args)
            else:
                cohort.heatmap(*args)
            assert len(captured) == 1
            assert snapshot() == before
        finally:
            for fig in captured:
                plt.close(fig)
