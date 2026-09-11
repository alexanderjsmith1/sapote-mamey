"""Regression: the cohort front-door must auto-locate a master named with a
capital "Master" (the master-workbook step's actual convention).

Before: _locate_master globbed "*master*.xlsx" (lowercase, case-sensitive),
which silently missed Mamey_Master.xlsx / Mamey_v*.*_Master_After_*.xlsx — so
`mamey cohort` fell back to "no master found" even when one was present.
"""
from pathlib import Path
import mamey.cohort_deliverable as cd


def test_locates_capital_master(tmp_path):
    (tmp_path / "Mamey_Master.xlsx").write_bytes(b"x")
    got = cd._locate_master(tmp_path, None)
    assert got is not None and got.name == "Mamey_Master.xlsx"


def test_locates_versioned_master_and_picks_last(tmp_path):
    (tmp_path / "Mamey_v1.9.111_Master_After_AS-421.xlsx").write_bytes(b"x")
    (tmp_path / "Mamey_v1.9.111_Master_After_AS-660.xlsx").write_bytes(b"x")
    got = cd._locate_master(tmp_path, None)
    assert got is not None and "Master" in got.name


def test_ignores_excel_lock_files(tmp_path):
    (tmp_path / "Mamey_Master.xlsx").write_bytes(b"x")
    (tmp_path / "~$Mamey_Master.xlsx").write_bytes(b"x")
    got = cd._locate_master(tmp_path, None)
    assert got is not None and not got.name.startswith("~$")


def test_explicit_path_still_wins(tmp_path):
    p = tmp_path / "custom.xlsx"
    p.write_bytes(b"x")
    assert cd._locate_master(tmp_path, str(p)) == p


def test_none_when_absent(tmp_path):
    assert cd._locate_master(tmp_path, None) is None
