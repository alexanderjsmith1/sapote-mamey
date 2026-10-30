"""The limit is not the number of eligible rows actually plotted."""
from types import SimpleNamespace
import pytest
from mamey import figure_theme
from mamey.chatgpt_commands import render_figures_command
import csv
import json

def make_package(tmp_path, count):
    package = tmp_path / "software-fixture" / "package"
    package.mkdir(parents=True)
    (package / "manifest.json").write_text(json.dumps({"strain_id": "software-fixture"}))
    rows = [{"BGC_ID": f"BGC{i:03d}", "Contig": "fixture_contig_part_1.7",
             "antiSMASH_Region": f"region{i:03d}", "AB_auto": str(60-i),
             "AF_auto": str(30+i), "Standing_rule": "", "Primary_metab_flag": ""}
            for i in range(1, count+1)]
    with (package / "software-fixture_4_triage_board.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    return package

@pytest.mark.parametrize("count, limit", [(1, 10), (6, 10), (6, 3)])
def test_title_counts_plotted_rows_and_axis_names_only_the_score(tmp_path, monkeypatch, count, limit):
    package = make_package(tmp_path, count)
    observed = []
    native = figure_theme.save_figure_pair
    def capture(fig, stem, **kwargs):
        ax = fig.axes[0]
        observed.append((ax.get_title(), ax.get_xlabel(), len(ax.patches)))
        return native(fig, stem, **kwargs)
    monkeypatch.setattr(figure_theme, "save_figure_pair", capture)
    assert render_figures_command(SimpleNamespace(package=str(package), outdir=str(tmp_path/"figures"), top_n=limit, style="default")) == 0
    assert len(observed) == 2
    for title, xlabel, plotted in observed:
        assert plotted == min(count, limit)
        assert title.startswith(f"Top {plotted} ")
        assert "software-fixture" in title
        assert xlabel == "DAPR auto score"
