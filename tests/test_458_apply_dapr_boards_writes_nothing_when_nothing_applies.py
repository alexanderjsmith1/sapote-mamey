"""apply_dapr_boards leaves the workbook untouched when neither board can be applied.

Before: it re-saved the workbook through openpyxl even when both boards were skipped.
"""
import subprocess
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]


def test_no_board_no_write(tmp_path):
    wb_path = tmp_path / "master.xlsx"
    wb = openpyxl.Workbook(); wb.active.title = "Summary"; wb.save(wb_path)
    before = wb_path.read_bytes()
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "apply_dapr_boards.py"), str(wb_path),
                        "--cohort", str(tmp_path / "no_cohort")], capture_output=True, text=True)
    assert r.returncode == 1
    assert wb_path.read_bytes() == before
    assert "workbook not written" in r.stdout + r.stderr
