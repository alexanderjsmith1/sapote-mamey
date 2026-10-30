"""Standard lead figures use the native governed theme/export pair."""
import csv
import json
from types import SimpleNamespace
import pytest
from PIL import Image
from mamey import figure_theme
from mamey.chatgpt_commands import render_figures_command

@pytest.mark.parametrize("style", ["default", "chatgpt-node-first"])
def test_native_governed_pair_preserves_identity_scores_and_global_style(tmp_path, monkeypatch, style):
    import matplotlib.pyplot as plt
    from matplotlib.colors import to_rgba
    package = tmp_path / "software-fixture" / "package"
    package.mkdir(parents=True)
    (package / "manifest.json").write_text(json.dumps({"strain_id": "software-fixture"}))
    row = {"BGC_ID": "BGC001", "Contig": "fixture_contig_part_1.7",
           "antiSMASH_Region": "region001", "AB_auto": "55", "AF_auto": "30"}
    with (package / "software-fixture_4_triage_board.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row));writer.writeheader();writer.writerow(row)
    before = {key: plt.rcParams[key] for key in ["font.family", "svg.fonttype", "figure.facecolor"]}
    observed = []
    native = figure_theme.save_figure_pair
    def capture(fig, stem, **kwargs):
        ax = fig.axes[0]
        observed.append({"labels": [t.get_text() for t in ax.get_yticklabels()],
                         "scores": [p.get_width() for p in ax.patches],
                         "color": ax.patches[0].get_facecolor()})
        return native(fig, stem, **kwargs)
    monkeypatch.setattr(figure_theme, "save_figure_pair", capture)
    out = tmp_path / "figures"
    assert render_figures_command(SimpleNamespace(package=str(package), outdir=str(out), top_n=10, style=style)) == 0
    assert len(observed) == 2
    assert [v["scores"] for v in observed] == [[55], [30]]
    identity = "software-fixture / fixture_contig_part_1.7 / region001 / BGC001"
    assert all([label.replace("\n", "") for label in v["labels"]] == [identity] for v in observed)
    palette = figure_theme.resolve_palette()
    assert [v["color"] for v in observed] == [to_rgba(palette["navy"]), to_rgba(palette["teal"])]
    for stem in ["top_antibacterial_leads", "top_antifungal_leads"]:
        with Image.open(out / (stem+".png")) as image:
            assert image.info["Software"] == "Sapote-Mamey governed figure theme"
        svg = (out / (stem+".svg")).read_text()
        assert "Sapote-Mamey governed figure theme" in svg
        assert all(part in svg for part in identity.split(" / "))
    assert before == {key: plt.rcParams[key] for key in before}
