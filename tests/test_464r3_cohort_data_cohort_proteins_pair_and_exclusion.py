"""Cohort protein build refuses an existing receipt; compare reports real exclusions."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from mamey.cohort_proteins import build_catalog, compare_catalog

_spec = importlib.util.spec_from_file_location(
    "_cohort_fixture_464r3", Path(__file__).resolve().parent / "test_cohort_proteins_v9_7_377.py")
_fx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fx)

CORE = "MKTAYIAKQRQISFVKSHFSRQDILDLWIYHTQGYFP"


def test_existing_receipt_is_refused_without_replace(tmp_path: Path) -> None:
    empty = tmp_path / "empty_cohort"
    empty.mkdir()
    database = tmp_path / "catalog.sqlite"
    receipt = tmp_path / "catalog.receipt.json"
    receipt.write_text("earlier receipt\n", encoding="utf-8")
    with pytest.raises(FileExistsError):
        build_catalog([("C1", empty)], database)
    assert receipt.read_text(encoding="utf-8") == "earlier receipt\n"
    assert not database.exists()


def test_replace_rebuilds_both_and_receipt_binds_database(tmp_path: Path) -> None:
    empty = tmp_path / "empty_cohort"
    empty.mkdir()
    database = tmp_path / "catalog.sqlite"
    build_catalog([("C1", empty)], database)
    with pytest.raises(FileExistsError):
        build_catalog([("C1", empty)], database)
    stats = build_catalog([("C1", empty)], database, replace=True)
    saved = json.loads((tmp_path / "catalog.receipt.json").read_text(encoding="utf-8"))
    assert saved["database"]["sha256"] == stats["database"]["sha256"]
    assert not list(tmp_path.glob("*.tmp"))


def _two_cohorts(tmp_path: Path) -> tuple[Path, Path]:
    a, b = tmp_path / "a", tmp_path / "b"
    pkg = _fx._write_package(a, "STRAIN_Q", "NODE_1_length_9_cov_1", "region001", "BGC001",
                             [("q1", "core synthase", CORE)])
    _fx._write_package(a, "STRAIN_R", "NODE_2_length_9_cov_1", "region002", "BGC002",
                       [("r1", "core synthase", CORE[:-1] + "A")])
    # The same focal strain label also sits in the second cohort.
    _fx._write_package(b, "STRAIN_Q", "CONTIG_7", "region003", "BGC003",
                       [("x1", "core synthase", CORE)])
    database = tmp_path / "catalog.sqlite"
    build_catalog([("COHORT_A", a), ("COHORT_B", b)], database)
    return database, pkg


def test_misspelled_query_cohort_is_refused(tmp_path: Path) -> None:
    database, pkg = _two_cohorts(tmp_path)
    out = tmp_path / "out"
    with pytest.raises(ValueError, match="not a cohort label"):
        compare_catalog(database, pkg, "BGC001", out, query_cohort="COHORT_AA")
    assert not out.exists()


def test_query_cohort_without_focal_rows_is_refused(tmp_path: Path) -> None:
    a, b = tmp_path / "a", tmp_path / "b"
    pkg = _fx._write_package(a, "STRAIN_Q", "NODE_1", "region001", "BGC001", [("q1", "core synthase", CORE)])
    _fx._write_package(b, "STRAIN_Z", "NODE_9", "region009", "BGC009", [("z1", "core synthase", CORE)])
    database = tmp_path / "catalog.sqlite"
    build_catalog([("COHORT_A", a), ("COHORT_B", b)], database)
    with pytest.raises(ValueError, match="holds no rows for the focal strain"):
        compare_catalog(database, pkg, "BGC001", tmp_path / "out", query_cohort="COHORT_B")


def test_receipt_reports_actual_exclusion_and_cross_cohort_self_rows(tmp_path: Path) -> None:
    database, pkg = _two_cohorts(tmp_path)
    receipt = compare_catalog(database, pkg, "BGC001", tmp_path / "out", query_cohort="COHORT_A")
    assert receipt["target_strain_excluded_from_query_cohort"] is True
    assert receipt["focal_strain"] == "STRAIN_Q"
    assert receipt["focal_strain_excluded_cohorts"] == ["COHORT_A"]
    assert receipt["focal_strain_still_ranked_in_cohorts"] == ["COHORT_B"]
    assert receipt["focal_strain_rows_by_cohort"] == {"COHORT_A": 1, "COHORT_B": 1}


def test_no_query_cohort_reports_no_exclusion(tmp_path: Path) -> None:
    database, pkg = _two_cohorts(tmp_path)
    receipt = compare_catalog(database, pkg, "BGC001", tmp_path / "out")
    assert receipt["target_strain_excluded_from_query_cohort"] is False
    assert receipt["focal_strain_excluded_cohorts"] == []
