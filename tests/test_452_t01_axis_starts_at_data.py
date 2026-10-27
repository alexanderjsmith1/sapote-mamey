"""Card 452_t01_axis_starts_at_data: the 16S similarity histogram (T01) draws its axis from the data.

The printed axis was fixed at 95-100%. On corrected identities (lowest 97.94% in one cohort) three quarters of the
panel was empty. The axis now starts one whole percent below the lowest value, never below the printed 94.75 bins;
bins and numbers are unchanged. Synthetic IDs only.
"""
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
    out = tmp_path / ("fig_override" if extra else "fig")
    r = subprocess.run([sys.executable, str(TOOL), "--cohort", str(cohort), "--data", str(data), "--out", str(out),
                        "--layout", "moss", "--palette-set", "moss", "--dpi", "72", *extra], capture_output=True, text=True,
                       timeout=180)
    return r, out


def axis_labels(pdf):
    pypdf = pytest.importorskip("pypdf")
    text = "".join(p.extract_text() for p in pypdf.PdfReader(str(pdf)).pages)
    return {f"{n}%" for n in range(94, 101) if f"{n}%" in text}


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not installed")
def test_axis_starts_one_percent_below_the_lowest_value(tmp_path):
    r, out = render(tmp_path, [97.94, 99.1, 100])
    assert r.returncode == 0, r.stdout + r.stderr
    run = json.loads(out.with_name(out.name + "_run.json").read_text())
    assert run["x_min"] == 96.75
    assert axis_labels(out.with_suffix(".pdf")) == {"97%", "98%", "99%", "100%"}


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not installed")
def test_low_values_keep_the_printed_range(tmp_path):
    r, out = render(tmp_path, [95.3, 99.0])
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(out.with_name(out.name + "_run.json").read_text())["x_min"] == 94.75
    assert "95%" in axis_labels(out.with_suffix(".pdf"))


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not installed")
def test_x_min_override_and_refusal(tmp_path):
    r, out = render(tmp_path, [97.94, 99.1], "--x-min", "94.75")
    assert r.returncode == 0 and json.loads(out.with_name(out.name + "_run.json").read_text())["x_min"] == 94.75
    (tmp_path / "b").mkdir()
    bad, _ = render(tmp_path / "b", [97.94, 99.1], "--x-min", "98.5")
    assert bad.returncode != 0 and "below the lowest value" in bad.stderr
