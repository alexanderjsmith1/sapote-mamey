"""BC2 .399 audit: mamey/master_workbook.py::_update_class_matrix() merges real (raw-cased)
antiSMASH product tokens directly into its class-column list alongside the curated ALL_AS_CLASSES
list, without case normalization. Real antiSMASH tokens are lowercase for several of
ALL_AS_CLASSES's own entries ("NRPS", "T1PKS", "T2PKS", "T3PKS", ...) -- confirmed against
mamey/class_architecture.py::_REAL_CLASSES. Before this fix, that produced TWO columns per such
class: the curated uppercase one (always empty -- no real product ever matches it exactly) and
a separately-created lowercase one (holding the real counts). No data was lost, but the
canonical column silently read as zero, and the real signal hid under an undocumented
duplicate column.

Zero prior test coverage existed for this function.
"""
from __future__ import annotations

import pathlib
import sys

from openpyxl import Workbook

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mamey.master_workbook import _update_class_matrix, ALL_AS_CLASSES  # noqa: E402
from mamey.models import BGCRecord  # noqa: E402


def _bgc(bid, products):
    return BGCRecord(bgc_id=bid, contig="c1", region_number=1, start=1, end=100,
                      contig_length=1000, products=products, mibig_hits=[],
                      edge_status="internal", architecture_confidence="",
                      architecture_rationale="", architecture_capacity="",
                      architecture_class_confidence="", antismash_region="region001")


def _headers(ws):
    return [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]


def _row(ws, r):
    return [ws.cell(r, c).value for c in range(1, ws.max_column + 1)]


def test_realistic_lowercase_products_route_into_the_canonical_uppercase_column():
    """The consequential proof: a real lowercase 'nrps'/'t1pks' token must land in the
    curated ALL_AS_CLASSES column, not spawn a second lowercase duplicate."""
    wb = Workbook()
    _update_class_matrix(wb, "AS-TEST", [_bgc("BGC001", ["nrps"]), _bgc("BGC002", ["t1pks"])])
    ws = wb["BGC_Class_Matrix"]
    headers = _headers(ws)
    row2 = _row(ws, 2)

    assert "NRPS" in headers
    assert "nrps" not in headers, f"duplicate lowercase column created: {headers}"
    assert row2[headers.index("NRPS")] == 1

    assert "T1PKS" in headers
    assert "t1pks" not in headers, f"duplicate lowercase column created: {headers}"
    assert row2[headers.index("T1PKS")] == 1


def test_genuinely_novel_class_still_gets_its_own_column():
    """No regression: a product genuinely outside ALL_AS_CLASSES (any case) still gets its
    own new column, matching the original append-new-classes behavior."""
    wb = Workbook()
    _update_class_matrix(wb, "AS-TEST", [_bgc("BGC001", ["a-genuinely-novel-class"])])
    ws = wb["BGC_Class_Matrix"]
    headers = _headers(ws)
    assert "a-genuinely-novel-class" in headers


def test_existing_sheet_header_casing_is_respected_over_all_as_classes():
    """An already-established sheet header entry (e.g. from a prior, differently-cased run)
    is matched first, so an existing real workbook's columns are not further fragmented."""
    wb = Workbook()
    ws = wb.active
    ws.title = "BGC_Class_Matrix"
    ws.append(["Strain", "nrps", "Total classified calls"])  # pre-existing lowercase column
    _update_class_matrix(wb, "AS-NEW", [_bgc("BGC001", ["nrps"])])
    headers = _headers(ws)
    assert headers.count("nrps") == 1
    assert "NRPS" not in headers, f"created a second, differently-cased column: {headers}"
