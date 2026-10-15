"""Card attine_452_t06_axis_reaches_lowest_value: the 16S-against-dDDH plot (T06) draws a 16S value below 95%.

The 16S axis was fixed at 95-100%, so an isolate below 95% fell outside the panel without warning. The axis still
starts at 95% by default; a lower value moves the start to the quarter percent below it. Synthetic IDs only.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/taxonomy_T06_figures.py"


def render(tmp_path, values, *extra):
    cohort, data = tmp_path / "cohort.tsv", tmp_path / "data.tsv"
    cohort.write_text("strain\tgenus\tblock\n" + "".join(f"AS-{970 + i}\tStreptomyces\tisolates\n" for i in range(len(values))))
    data.write_text("strain\tsimilarity\td4\n" + "".join(f"AS-{970 + i}\t{v}\t{30 + 5 * i}\n" for i, v in enumerate(values)))
    out = tmp_path / "fig"
    r = subprocess.run([sys.executable, str(TOOL), "--cohort", str(cohort), "--data", str(data), "--out", str(out),
                        "--layout", "moss", "--palette-set", "moss", "--dpi", "72", *extra], capture_output=True, text=True,
                       timeout=300)
    return r, out


def x_min(out):
    return json.loads(out.with_name(out.name + "_run.json").read_text())["x_min"]


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not installed")
def test_default_axis_start_stays_at_95(tmp_path):
    r, out = render(tmp_path, [98.9, 99.5])
    assert r.returncode == 0, r.stdout + r.stderr
    assert x_min(out) == 95.0


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not installed")
def test_a_value_below_95_moves_the_axis_start(tmp_path):
    r, out = render(tmp_path, [94.75, 99.5])
    assert r.returncode == 0, r.stdout + r.stderr
    assert x_min(out) == 94.5


def test_an_axis_start_at_or_above_the_lowest_value_is_refused(tmp_path):
    r, _ = render(tmp_path, [96.0, 99.5], "--x-min", "96")
    assert r.returncode != 0 and "must be below the lowest value" in r.stderr


def test_the_r_script_reads_the_axis_start():
    src = TOOL.read_text()
    assert "coord_cartesian(xlim=c(95,100))" not in src and "xlim=c(as.numeric(a[11]),100)" in src
