"""A first-pass page for a package without a scan says the scan is not recorded; it does not print 0 or "none"."""
from __future__ import annotations
import importlib.util
from pathlib import Path

_TOOL = Path(__file__).resolve().parent.parent / "tools" / "build_first_pass_scans.py"
_spec = importlib.util.spec_from_file_location("build_first_pass_scans_465_unrecorded", _TOOL)
_m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_m)


def test_missing_chitinase_scan_prints_no_counts():
    text = _m._cgad({})
    assert "not recorded in this package" in text
    assert "GH18=0" not in text and "LPMO=0" not in text


def test_recorded_chitinase_counts_print_as_before():
    text = _m._cgad({"chitinase": {"counts": {"GH18": 0, "GH19": 1, "AA10_LPMO": 2}}})
    assert "GH18=0, LPMO=2" in text          # a scanned 0 is a real 0
    assert "not recorded" not in text


def test_recorded_counts_without_a_family_key_name_the_gap():
    text = _m._cgad({"chitinase": {"counts": {"GH19": 1}}})
    assert "GH18=not recorded, LPMO=not recorded" in text


def test_missing_orphan_list_is_not_none():
    text = _m._flbr({})
    assert "megasynthase candidates (Tier 1, KS-bearing): not recorded in this package" in text
    assert "KS-bearing): none" not in text


def test_recorded_empty_orphan_list_is_none():
    text = _m._flbr({"flbr": {"orphan_megasynthase_candidates": []}})
    assert "KS-bearing): none" in text
