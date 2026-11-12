"""Each rarefaction value in Pangenome_Summary.md is labeled with the strain count of its CSV row.

mean[i] is the value after i + 1 strains. The summary used to label mean[n // 2] as n // 2 strains and to
measure "the last 10 strains" from mean[n - 10], which spans 9 additions.
"""
from __future__ import annotations
import importlib.util
from pathlib import Path

_TOOL = Path(__file__).resolve().parents[1] / "tools" / "build_pangenome.py"
_spec = importlib.util.spec_from_file_location("build_pangenome_465", _TOOL)
_m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_m)


def test_even_cohort_labels_match_csv_rows():
    mean = list(range(1, 13))                     # 12 strains; row n_strains=k holds k
    line = _m._rarefaction_line(mean)
    assert "1 -> 6 -> 12 at 1 / 6 / 12" in line
    assert "+10 families over the last 10 strains" in line


def test_odd_cohort_uses_the_floor_half():
    line = _m._rarefaction_line([3, 5, 6, 8, 9])  # 5 strains
    assert "3 -> 5 -> 9 at 1 / 2 / 5" in line
    assert "+9 families over the last 5 strains" in line


def test_small_cohorts():
    assert "at 1 / 1 / 1" in _m._rarefaction_line([4])
    assert "+4 families over the last 1 strain" in _m._rarefaction_line([4])
    assert "No strains" in _m._rarefaction_line([])
