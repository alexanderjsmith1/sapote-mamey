"""Native lead exports report actual raster dimensions at publication resolution."""
import csv
import json
from types import SimpleNamespace
import pytest
from PIL import Image
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


@pytest.mark.parametrize("count", [1, 6])
def test_standard_lead_dpi_and_dimensions_are_real(tmp_path, count):
    package = make_package(tmp_path, count)
    out = tmp_path / "figures"
    args = SimpleNamespace(package=str(package), outdir=str(out), top_n=10, style="default")
    assert render_figures_command(args) == 0
    records = list(csv.DictReader((out / "figure_manifest.csv").open()))
    assert len(records) == 2
    for row in records:
        with Image.open(out / row["filename"]) as image:
            assert all(abs(float(dpi)-300) < 1 for dpi in image.info["dpi"])
            assert image.width / 6 >= 300
            assert row["dimensions"] == f"{image.width}x{image.height}"
        assert int(row["row_count"]) == count
