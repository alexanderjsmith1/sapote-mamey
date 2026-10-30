"""Full identities remain readable when the native figure is placed six inches wide."""
from pathlib import Path
from types import SimpleNamespace
import csv
import json
import importlib.util
import pytest
from mamey import figure_theme
from mamey.chatgpt_commands import render_figures_command

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

@pytest.mark.parametrize("count, long_node", [(1, False), (6, True)])
def test_six_inch_text_and_full_labels(tmp_path, monkeypatch, count, long_node):
    package = make_package(tmp_path, count)
    table = next(package.glob("*_4_triage_board.csv"))
    rows = list(csv.DictReader(table.open()))
    if long_node:
        for row in rows: row["Contig"] = "fixture_contig_" + "part_"*25 + "v1.7"
        with table.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    expected = {f"software-fixture / {row['Contig']} / {row['antiSMASH_Region']} / {row['BGC_ID']}" for row in rows}
    native = figure_theme.save_figure_pair
    observed = []
    def capture(fig, stem, **kwargs):
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        labels = fig.axes[0].get_yticklabels()
        assert {t.get_text().replace("\n", "") for t in labels} == expected
        boxes = [t.get_window_extent(renderer) for t in labels]
        assert all(not a.overlaps(b) for i,a in enumerate(boxes) for b in boxes[i+1:]), "identity labels overlap"
        observed.append(True)
        return native(fig, stem, **kwargs)
    monkeypatch.setattr(figure_theme, "save_figure_pair", capture)
    out = tmp_path/"figures"
    assert render_figures_command(SimpleNamespace(package=str(package),outdir=str(out),top_n=10,style="default")) == 0
    tool = Path(__file__).resolve().parents[1]/"tools/_min_text_check.py"
    spec = importlib.util.spec_from_file_location("native_lead_min_text", tool)
    checker = importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
    for svg in out.glob("*.svg"):
        result = checker.printed_min_text(svg.read_bytes(), "svg", 6)
        assert result["smallest_pt"] is not None
        assert result["smallest_pt"] >= 7.95, result
    assert len(observed) == 2
