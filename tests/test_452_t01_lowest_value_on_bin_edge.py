"""Card attine_452_t01_lowest_value_on_bin_edge: T01 draws a cohort whose lowest 16S value is exactly 94.75%.

The first printed bin is 94.75-95.00% and counts a value on its left edge. The axis check required the axis start to
lie below the lowest value, but the start can't go below 94.75, so a value of exactly 94.75 was refused although it
fits the bins. Synthetic IDs only.
"""
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/taxonomy_T01_figures.py"


def render(tmp_path, values, *extra):
    cohort, data = tmp_path / "cohort.tsv", tmp_path / "data.tsv"
    cohort.write_text("strain\tgenus\tblock\n" + "".join(f"AS-{970 + i}\tStreptomyces\tisolates\n" for i in range(len(values))))
    data.write_text("strain\tsimilarity\n" + "".join(f"AS-{970 + i}\t{v}\n" for i, v in enumerate(values)))
    out = tmp_path / "fig"
    r = subprocess.run([sys.executable, str(TOOL), "--cohort", str(cohort), "--data", str(data), "--out", str(out),
                        "--layout", "moss", "--palette-set", "moss", "--dpi", "72", *extra], capture_output=True, text=True,
                       timeout=180)
    return r, out


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not installed")
def test_lowest_value_on_the_first_bin_edge_is_drawn_and_counted(tmp_path):
    r, out = render(tmp_path, [94.75, 94.92, 99.0])
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(out.with_name(out.name + "_run.json").read_text())["x_min"] == 94.75
    with out.with_name(out.name + "_numbers.tsv").open() as f:
        nums = {row["metric"]: row["count"] for row in csv.DictReader(f, delimiter="\t")}
    assert nums["plotted_rows"] == "3"
    assert nums["bin:94.75:95.00:Streptomyces"] == "2"


def test_values_below_the_bins_and_a_late_axis_start_are_still_refused(tmp_path):
    r, _ = render(tmp_path, [94.70, 99.0])
    assert r.returncode != 0 and "below printed histogram bins" in r.stderr
    (tmp_path / "b").mkdir()
    r, _ = render(tmp_path / "b", [95.3, 99.0], "--x-min", "95.3")
    assert r.returncode != 0 and "below the lowest value" in r.stderr
