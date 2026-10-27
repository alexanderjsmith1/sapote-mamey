"""A NaN or infinite correlation is 'not measurable', never labeled 'mild'.

When every strain has the same contig count the log-contig series has no spread, the
correlation is NaN, and every comparison against NaN is false. The old label chain fell
through to 'mild'. The ranking row now carries a blank correlation and the regime
'not measurable'; the figure draws no bar for it.
"""
import importlib.util
import math
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "build_normalization_matrix.py"


@pytest.fixture(scope="module")
def nm():
    spec = importlib.util.spec_from_file_location("build_normalization_matrix_459", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def rows_for(nm, contigs, nrps_counts):
    out = []
    for i, (c, n) in enumerate(zip(contigs, nrps_counts)):
        r = {"sid": f"S{i}", "organism": "x", "contigs": c, "genome_Mbp": 8 + i, "raw_BGC": 20 + i,
             "corrected_BGC": 20 + i, "den_ecto+napaa": 1, "den_terpene": 1, "den_halogenase": 1}
        for k in nm.CLASSES:
            r[f"cls_{k}"] = 0
        r["cls_NRPS"] = n
        out.append(r)
    return out


def test_constant_contig_count_is_not_measurable_not_mild(nm):
    rows = rows_for(nm, [10] * 12, [1, 2, 3, 4, 5, 6, 1, 2, 3, 4, 5, 6])
    ranking, matrix, _ = nm.derive(rows)
    nrps = next(r for r in ranking if r["class"] == "NRPS")
    assert nrps["regime"] == "not measurable"
    assert nrps["corr_fragmentation"] == ""
    assert next(m for m in matrix if m["class"] == "NRPS")["raw"] == ""


def test_measurable_correlation_still_gets_its_label(nm):
    rows = rows_for(nm, [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048], [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
    nrps = next(r for r in nm.derive(rows)[0] if r["class"] == "NRPS")
    assert nrps["regime"] == "inflates" and math.isfinite(nrps["corr_fragmentation"])


@pytest.mark.parametrize("rr,expect", [(float("nan"), "not measurable"), (float("inf"), "not measurable"),
                                       (float("-inf"), "not measurable"), (0.2, "mild"), (0.05, "robust"),
                                       (0.5, "inflates"), (-0.4, "deflates")])
def test_regime_of(nm, rr, expect):
    assert nm.regime_of(rr) == expect


def test_unmeasurable_rows_plot_without_a_bar(nm, tmp_path):
    pytest.importorskip("matplotlib")
    rows = rows_for(nm, [10] * 12, [1, 2, 3, 4, 5, 6, 1, 2, 3, 4, 5, 6])
    for i, r in enumerate(rows):
        r["cls_T1PKS"] = i + 1
    ranking, matrix, dens = nm.derive(rows)
    assert {r["class"] for r in ranking} == {"NRPS", "T1PKS"}
    assert all(r["regime"] == "not measurable" for r in ranking)
    nm.plot(ranking, matrix, dens, str(tmp_path))
    assert (tmp_path / "fig_class_fragmentation.png").stat().st_size > 0
