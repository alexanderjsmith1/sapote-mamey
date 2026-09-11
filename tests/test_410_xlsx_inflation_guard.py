"""v9.7.410 hostile audit (round 6) — workbook decompression bomb through the master readers.

A 113 KB .xlsx made of one 60 KB shared string repeated 1,000 times cost 51 MB of RSS in
openpyxl.load_workbook (450x); the operator-supplied master path is where such a file arrives.
The five master/cohort readers now preflight the archive's declared inflated size."""
from __future__ import annotations

import openpyxl
import pytest

from mamey import xlsx_determinism as xlsx_guard
from mamey.xlsx_determinism import WorkbookTooLargeError, guard_workbook_size


def _bomb(path, reps=1000):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "B5_BLASTp_Hits"
    ws.append(["strain", "BGC_ID", "query_locus", "hit_rank", "subject_acc"])
    big = "A" * 60_000
    for i in range(reps):
        ws.append(["AS-1", "BGC001", f"q{i}", 1, big])
    wb.save(path)


def test_declared_inflation_is_measured_and_capped(tmp_path, monkeypatch):
    p = tmp_path / "m.xlsx"
    _bomb(p)
    assert p.stat().st_size < 400_000
    assert guard_workbook_size(p) > 20_000_000            # declared ~33 MB (RSS ~51 MB) for a 113 KB file; under the default cap
    monkeypatch.setenv("MAMEY_XLSX_MAX_INFLATED_BYTES", "10000000")
    with pytest.raises(WorkbookTooLargeError, match="XLSX_INFLATION_GUARD_REFUSED"):
        guard_workbook_size(p)


def test_ingest_refuses_the_bomb_before_loading(tmp_path, monkeypatch):
    from mamey import blastp_ingest as bi
    p = tmp_path / "master.xlsx"
    _bomb(p)
    csvp = tmp_path / "h.csv"
    csvp.write_text("BGC001_ctg1_2,WP_1,66.1,340,115,0,1,340,1,340,8.8e-152,441,75.2\n")
    monkeypatch.setenv("MAMEY_XLSX_MAX_INFLATED_BYTES", "10000000")
    with pytest.raises(WorkbookTooLargeError):
        bi.ingest_blastp(p, "AS-1", csvp, None, top_n=10)


def test_ordinary_workbook_and_non_zip_pass_through(tmp_path):
    p = tmp_path / "small.xlsx"
    wb = openpyxl.Workbook()
    wb.active.append(["a", 1])
    wb.save(p)
    assert 0 < guard_workbook_size(p) < 100_000
    junk = tmp_path / "junk.xlsx"
    junk.write_bytes(b"not a zip")
    assert guard_workbook_size(junk) == 0            # left for openpyxl to report
    assert xlsx_guard.max_inflated_bytes() == xlsx_guard.DEFAULT_MAX_INFLATED_BYTES
