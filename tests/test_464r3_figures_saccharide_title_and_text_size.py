"""fig_saccharide_adjusted: the title does not say "omitted", every label is the 9 pt base size on a
double-column-width figure, and the figure widens (with a warning) only when the strain labels need it."""
import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")

TOOL = Path(__file__).resolve().parents[1] / "tools" / "build_figures.py"
spec = importlib.util.spec_from_file_location("build_figures_title_464r3", TOOL)
bf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bf)


def _rows(n):
    return [{"strain": f"Example_strain_{i}", "raw_BGC": str(10 + i), "specialist_BGC": str(8 + i),
             "pure_saccharide": "2"} for i in range(1, n + 1)]


def _capture(monkeypatch):
    import matplotlib.pyplot as plt
    seen = {}
    real_close = plt.close

    def capture(*args, **kwargs):
        fig = plt.gcf(); ax = fig.axes[0]
        seen.update(width=fig.get_figwidth(), title=ax.get_title(),
                    ticks={t.get_fontsize() for t in ax.get_xticklabels()},
                    legend={t.get_fontsize() for t in ax.get_legend().get_texts()})
        return real_close(*args, **kwargs)

    monkeypatch.setattr(plt, "close", capture)
    return seen


@pytest.mark.parametrize("n", [8, 40])
def test_title_and_sizes_at_print_width(tmp_path, monkeypatch, capsys, n):
    from mamey.figure_policy import PUBLICATION_PROFILES
    seen = _capture(monkeypatch)
    bf.plot_saccharide_adjusted(_rows(n), str(tmp_path / "fig.png"))
    assert "omitted" not in seen["title"]
    assert seen["title"] == "Per-strain BGCs: specialist and pure-saccharide BGCs"
    assert seen["ticks"] == {9.0} and seen["legend"] == {9.0}
    assert seen["width"] == PUBLICATION_PROFILES["DOUBLE_COLUMN"]["width_in"]
    assert capsys.readouterr().err == ""


def test_many_strains_widen_the_figure_and_say_so(tmp_path, monkeypatch, capsys):
    seen = _capture(monkeypatch)
    bf.plot_saccharide_adjusted(_rows(120), str(tmp_path / "fig.png"))
    assert seen["width"] > 7.2 and seen["ticks"] == {9.0}
    assert "falls below 8 pt" in capsys.readouterr().err
