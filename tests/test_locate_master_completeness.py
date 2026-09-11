"""Regression test for F5: _locate_master must pick the MOST COMPLETE master, not the
alphabetically-last file (which was a partial per-append snapshot → silent under-coverage)."""
import os, time, tempfile
from pathlib import Path
from openpyxl import Workbook
from mamey.cohort_deliverable import _locate_master


def _make(d, name, n_strains, mtime):
    wb = Workbook(); ws = wb.active; ws.title = "A2_Strain_Registry"; ws.append(["strain_id"])
    for i in range(n_strains):
        ws.append([f"AS-{100+i}"])
    p = Path(d) / name; wb.save(p); os.utime(p, (mtime, mtime)); return p


def test_picks_complete_master_over_alpha_last_partial(tmp_path):
    now = time.time()
    _make(tmp_path, "Mamey_Master.xlsx", 9, now - 100)                       # complete, older
    _make(tmp_path, "Mamey_v1.9.111_Master_After_AS-421.xlsx", 5, now - 50)  # partial
    _make(tmp_path, "Mamey_v1.9.111_Master_After_AS-958.xlsx", 4, now - 10)  # alpha-last, newest, fewest
    picked = _locate_master(tmp_path, None)
    assert picked is not None and picked.name == "Mamey_Master.xlsx"


def test_mtime_tiebreak_when_equally_complete(tmp_path):
    now = time.time()
    _make(tmp_path, "Mamey_Master_a.xlsx", 6, now - 100)
    newer = _make(tmp_path, "Mamey_Master_b.xlsx", 6, now - 10)
    assert _locate_master(tmp_path, None).name == newer.name


def test_explicit_path_wins(tmp_path):
    p = _make(tmp_path, "Mamey_Master.xlsx", 9, time.time())
    assert _locate_master(tmp_path, str(p)) == p


def test_none_when_no_master(tmp_path):
    assert _locate_master(tmp_path, None) is None
