"""Screening concentration figures state only what the renderer checked.

Before: the concentration captions always said crudes and unresolved identity conflicts were
excluded, and the subtitle always said 384-well, although the renderer checks neither. Now those
statements come from `render_context.csv` (`assay_format`, `admission_statement`) when the owner
states them; otherwise the caption says the admission was not checked here.
"""
import csv
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "render_screening_exploration.R"
FIELDS = ["dataset", "organism", "concentration_ug_ml", "inhibition_pct",
          "assay_plate", "fraction_plate", "source_well"]


@pytest.fixture(scope="module")
def rscript():
    binary = shutil.which("Rscript")
    if not binary:
        pytest.skip("Optional R runtime unavailable")
    probe = subprocess.run([binary, "-e", 'quit(status=ifelse(requireNamespace("ggplot2",quietly=TRUE)'
                            '&&requireNamespace("patchwork",quietly=TRUE),0,1))'], capture_output=True)
    if probe.returncode:
        pytest.skip("Optional ggplot2/patchwork unavailable")
    return binary


def _write(folder, name, fields, rows):
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / name).open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(fields)
        writer.writerows(rows)


def _render(rscript, tmp_path, context=None):
    src, out = tmp_path / "in", tmp_path / "out"
    _write(src, "concentration_observations.csv", FIELDS,
           [["Example", "Target", c, v, 1, 1, "A1"] for c, v in zip([15, 30, 60, 120], [5, 10, 40, 80])])
    if context:
        _write(src, "render_context.csv", ["key", "value"], context)
    proc = subprocess.run([rscript, str(SCRIPT), str(src), str(out)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return [(out / f"03_concentrations_example{suffix}_caption.txt").read_text()
            for suffix in ("", "_zoom")]


def test_default_captions_do_not_claim_unchecked_exclusions(rscript, tmp_path):
    for caption in _render(rscript, tmp_path):
        assert "Crudes, incomplete records and unresolved identity conflicts are excluded" not in caption
        assert "this renderer does not check it" in caption


def test_owner_stated_admission_is_quoted_as_stated(rscript, tmp_path):
    captions = _render(rscript, tmp_path, [["assay_format", "384-well"],
                                           ["admission_statement", "crude extracts removed upstream"]])
    for caption in captions:
        assert "as stated in render_context.csv: crude extracts removed upstream" in caption
