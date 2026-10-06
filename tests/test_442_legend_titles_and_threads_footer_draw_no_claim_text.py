"""Legend titles and the threads figure carry no claim wording (2026-09-24).

The shared text extractor behind the .442 save-path refusal skipped legend titles and any legend
kept with ax.add_artist(), so banned wording there saved without a refusal even through
save_figure. The cross-strain threads figure drew banned wording in its title, legend title and a
footer built in a variable, which a literal scan of draw calls cannot see. Generic fixtures.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.text import Text  # noqa: E402

from mamey.figure_policy import figure_text_violations, matplotlib_visible_text  # noqa: E402


def _drawn_violations(monkeypatch):
    """Record banned wording in every Text a figure draws, at savefig time."""
    seen = []
    orig = Figure.savefig

    def spy(self, *a, **k):
        seen.extend(figure_text_violations(t.get_text() for t in self.findobj(Text) if t.get_visible()))
        return orig(self, *a, **k)

    monkeypatch.setattr(Figure, "savefig", spy)
    return seen


def test_extractor_reads_legend_titles_and_add_artist_legends():
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1], label="PKS")
    ax.legend(title="thread (class-level)")
    assert figure_text_violations(matplotlib_visible_text(fig)) == ["class-level"]
    fig2, ax2 = plt.subplots()
    first = ax2.legend(handles=[Line2D([0], [0], label="similarity is not identity")], loc="upper left")
    ax2.add_artist(first)
    ax2.legend(handles=[Line2D([0], [0], label="group A")], loc="lower left")
    assert figure_text_violations(matplotlib_visible_text(fig2)) == ["similarity is not identity"]
    plt.close("all")


def test_threads_figure_draws_no_claim_text_and_keeps_the_ceiling_off_canvas(tmp_path, monkeypatch):
    from mamey.cross_strain_threads import render_threads_figure
    seen = _drawn_violations(monkeypatch)
    rows = [{"strain": f"GEN-{i}", "host": h, "lanthipeptide": 1, "ranthipeptide": 1}
            for i, h in enumerate(["bee", "bee", "wasp", "moss"], 1)]
    res = render_threads_figure(rows, tmp_path / "threads.png", strain_label="SYNTHETIC")
    assert res["status"] == "PASS"
    assert seen == []
    assert "not product identity" in res["claim_ceiling"]

