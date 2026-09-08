"""SCHEMA-P03 / SCHEMA-P04 (v9.7.328): workbook_schema_check.validate must not crash — and must
not leak the read_only zip handle — on a master workbook whose worksheets omit the stored
<dimension> element. In openpyxl read_only mode that makes ws.max_row / ws.max_column return None,
so the old code did `range(1, None + 1)` / `None - 1` -> TypeError (past any caller guard), and
because the body was not under try/finally the open archive handle leaked.
"""
import os
import re
import gc
import sys
import zipfile
import warnings

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
openpyxl = pytest.importorskip("openpyxl")
from mamey.workbook_schema_check import validate, CANONICAL_REQUIRED


def _make_master(path, strip_dimension):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for sheet in sorted(CANONICAL_REQUIRED):
        ws = wb.create_sheet(sheet)
        ws.append(["col1", "col2"])
        ws.append(["AS-001", "x"])
    wb.save(path)
    if not strip_dimension:
        return path
    with zipfile.ZipFile(path) as zin:
        names = zin.namelist()
        data = {n: zin.read(n) for n in names}
    for n in list(data):
        if re.match(r"xl/worksheets/sheet\d+\.xml$", n):
            data[n] = re.sub(rb"<dimension[^/]*/>", b"", data[n])
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zout:
        for n in names:
            zout.writestr(n, data[n])
    return path


def test_missing_dimension_does_not_crash(tmp_path):
    nodim = _make_master(str(tmp_path / "master_nodim.xlsx"), strip_dimension=True)
    good = _make_master(str(tmp_path / "master_good.xlsx"), strip_dimension=False)
    # Both must return a structured result (no TypeError), and the dimension scan must recover the
    # same picture the stored-dimension workbook gives.
    r_nodim = validate(nodim)
    r_good = validate(good)
    assert r_nodim["sheets_found"] == r_good["sheets_found"] == len(CANONICAL_REQUIRED)
    assert r_nodim["strain_count"] == r_good["strain_count"] == 1


def test_missing_dimension_does_not_leak_handle(tmp_path):
    nodim = _make_master(str(tmp_path / "master_nodim.xlsx"), strip_dimension=True)
    with warnings.catch_warnings():
        warnings.simplefilter("error", ResourceWarning)
        validate(nodim)
        gc.collect()  # would raise ResourceWarning-as-error if the read_only archive leaked
