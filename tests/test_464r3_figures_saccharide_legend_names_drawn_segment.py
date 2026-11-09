"""fig_saccharide_adjusted: the legend names the drawn pure-saccharide segment; it does not say "omitted"."""
import importlib.util
from pathlib import Path

import pytest

matplotlib = pytest.importorskip("matplotlib")

TOOL = Path(__file__).resolve().parents[1] / "tools" / "build_figures.py"
spec = importlib.util.spec_from_file_location("build_figures_legend_464r3", TOOL)
bf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bf)


def test_legend_labels(tmp_path, monkeypatch):
    import matplotlib.pyplot as plt
    seen = {}
    real_close = plt.close

    def capture_close(*args, **kwargs):
        fig = plt.gcf()
        seen["labels"] = [t.get_text() for ax in fig.axes if ax.get_legend() for t in ax.get_legend().get_texts()]
        return real_close(*args, **kwargs)

    monkeypatch.setattr(plt, "close", capture_close)
    rows = [{"strain": "Example_1", "raw_BGC": "10", "specialist_BGC": "8", "pure_saccharide": "2"},
            {"strain": "Example_2", "raw_BGC": "6", "specialist_BGC": "6", "pure_saccharide": "0"}]
    bf.plot_saccharide_adjusted(rows, str(tmp_path / "fig.png"))
    assert seen["labels"] == ["specialist BGCs (reported)", "pure-saccharide BGCs (drawn here)"]
    assert not any("omitted" in label for label in seen["labels"])
