"""build_gcf_tags prints its coverage summary for an empty bank or an all-dark bank.

The summary divided by the BGC count and by the anchored count, so either being zero raised
ZeroDivisionError after GCF_Tags.csv was written, and the workbook step never ran.
"""
import importlib.util
import pathlib
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
_spec = importlib.util.spec_from_file_location("build_gcf_tags_458", ROOT / "tools" / "build_gcf_tags.py")
gt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gt)


def test_empty_bank():
    lines = gt._coverage_lines(Counter(), 0)
    assert "tagged 0 BGCs" in lines[0] and "n/a" in lines[1]


def test_all_dark_bank():
    lines = gt._coverage_lines(Counter({"DARK_no_family": 3}), 3)
    assert "3 (100%)" in lines[1]
    assert "of 0 anchored BGCs, 0 (n/a)" in lines[4]


def test_mixed_bank_unchanged_wording():
    lines = gt._coverage_lines(Counter({"DARK_no_family": 1, "streptomycin_family": 2, "NRPS_orphan": 1}), 4)
    assert lines[2] == "  resolved to a named GCF family: 2 (50%)"
    assert lines[4] == "  of 3 anchored BGCs, 2 (67%) got a specific family tag"
