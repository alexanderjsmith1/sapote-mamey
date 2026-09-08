"""test_workbook_populated_sheet_gate.py — STEP 4 (SM-P1-008): Workbook populated-sheet gate.

Uses openpyxl.Workbook() fixtures per the spec. Tests:
  1. All four required sheets present with populated rows → PASS
  2. A sheet with all PENDING primary keys → FAIL_all_pending
  3. A missing required sheet → MISSING
  4. An empty sheet (header only, no rows) → FAIL_empty
  5. mamey validate --workbook-strict flag exists
"""
import sys
import tempfile
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

pytestmark = pytest.mark.skipif(not HAS_OPENPYXL, reason="openpyxl not installed")

from mamey.validate import validate_workbook_content


# ── Fixture helpers ────────────────────────────────────────────────────────────
def _make_wb_all_pass():
    """Four required sheets, each with a real primary key row."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # remove default Sheet

    for sheet_name, pk in [
        ("BGC_Inventory", "BGC_ID"),
        ("Triage_Board", "BGC_ID"),
        ("WetLab_Decision_Matrix", "BGC_ID"),
        ("Mode_B_Summary", "BGC_ID"),
    ]:
        ws = wb.create_sheet(sheet_name)
        ws.append([pk, "Other_Col"])
        ws.append(["BGC001", "some_value"])  # real row
    return wb


def _make_wb_all_pending():
    """One sheet where all pk values are 'PENDING'."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for sheet_name in ("BGC_Inventory", "Triage_Board", "WetLab_Decision_Matrix", "Mode_B_Summary"):
        ws = wb.create_sheet(sheet_name)
        ws.append(["BGC_ID", "Other_Col"])
        ws.append(["PENDING", "some_value"])
        ws.append(["pending", "another"])  # case-insensitive
    return wb


def _make_wb_missing_sheet():
    """Missing WetLab_Decision_Matrix."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for sheet_name in ("BGC_Inventory", "Triage_Board", "Mode_B_Summary"):
        ws = wb.create_sheet(sheet_name)
        ws.append(["BGC_ID", "Other_Col"])
        ws.append(["BGC001", "value"])
    return wb


def _make_wb_empty_sheet():
    """One sheet with header only, no data rows."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for sheet_name in ("BGC_Inventory", "Triage_Board", "WetLab_Decision_Matrix", "Mode_B_Summary"):
        ws = wb.create_sheet(sheet_name)
        ws.append(["BGC_ID", "Other_Col"])
        if sheet_name != "Mode_B_Summary":
            ws.append(["BGC001", "value"])
        # Mode_B_Summary: header only
    return wb


# ── Tests ──────────────────────────────────────────────────────────────────────
def test_all_pass():
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = f.name
    try:
        _make_wb_all_pass().save(path)
        result = validate_workbook_content(path)
        assert result["status"] == "PASS", f"Expected PASS: {result}"
        assert all(v["status"] == "PASS" for v in result["sheets"].values()), result
    finally:
        Path(path).unlink(missing_ok=True)


def test_all_pending_fails():
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = f.name
    try:
        _make_wb_all_pending().save(path)
        result = validate_workbook_content(path)
        assert result["status"] == "FAIL", f"Expected FAIL: {result}"
        # Every sheet should be FAIL_all_pending
        assert any(v["status"] == "FAIL_all_pending" for v in result["sheets"].values()), result
    finally:
        Path(path).unlink(missing_ok=True)


def test_missing_sheet_fails():
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = f.name
    try:
        _make_wb_missing_sheet().save(path)
        result = validate_workbook_content(path)
        assert result["status"] == "FAIL", f"Expected FAIL: {result}"
        assert any(v["status"] == "MISSING" for v in result["sheets"].values()), result
    finally:
        Path(path).unlink(missing_ok=True)


def test_empty_sheet_fails():
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = f.name
    try:
        _make_wb_empty_sheet().save(path)
        result = validate_workbook_content(path)
        assert result["status"] == "FAIL", f"Expected FAIL: {result}"
        assert any(v["status"] == "FAIL_empty" for v in result["sheets"].values()), result
    finally:
        Path(path).unlink(missing_ok=True)


def test_workbook_strict_flag_in_cli():
    """mamey validate --workbook-strict flag must exist in cli.py."""
    src = (_ROOT / "mamey" / "cli.py").read_text(encoding="utf-8")
    assert "workbook-strict" in src or "workbook_strict" in src, \
        "mamey validate --workbook-strict flag not found in cli.py"


def test_pending_case_insensitive():
    """'PENDING', 'pending', 'Pending' are all treated as PENDING."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for sheet_name in ("BGC_Inventory", "Triage_Board", "WetLab_Decision_Matrix", "Mode_B_Summary"):
        ws = wb.create_sheet(sheet_name)
        ws.append(["BGC_ID"])
        ws.append(["Pending"])
        ws.append(["PENDING"])
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = f.name
    try:
        wb.save(path)
        result = validate_workbook_content(path)
        assert result["status"] == "FAIL"
    finally:
        Path(path).unlink(missing_ok=True)


def test_empty_pk_treated_as_pending():
    """Empty string primary key also counts as PENDING."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for sheet_name in ("BGC_Inventory", "Triage_Board", "WetLab_Decision_Matrix", "Mode_B_Summary"):
        ws = wb.create_sheet(sheet_name)
        ws.append(["BGC_ID"])
        ws.append([""])  # empty pk
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = f.name
    try:
        wb.save(path)
        result = validate_workbook_content(path)
        assert result["status"] == "FAIL"
    finally:
        Path(path).unlink(missing_ok=True)



def _make_wb_wrong_pk_header():
    """A sheet that exists but whose header lacks the required BGC_ID primary-key column."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for sheet_name in ("BGC_Inventory", "Triage_Board", "WetLab_Decision_Matrix", "Mode_B_Summary"):
        ws = wb.create_sheet(sheet_name)
        if sheet_name == "BGC_Inventory":
            ws.append(["Wrong_Header", "Other_Col"])   # no BGC_ID column
            ws.append(["BGC001", "value"])
        else:
            ws.append(["BGC_ID", "Other_Col"])
            ws.append(["BGC001", "value"])
    return wb


def test_missing_primary_key_header_fails():
    """SM-P1-008 DEFECT-2 fix: a sheet missing its BGC_ID header must flag
    FAIL_missing_primary_key, not silently read column 0."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = f.name
    try:
        _make_wb_wrong_pk_header().save(path)
        result = validate_workbook_content(path)
        assert result["status"] == "FAIL", f"Expected FAIL: {result}"
        inv = result["sheets"]["BGC_Inventory"]
        assert inv["status"] == "FAIL_missing_primary_key", inv
    finally:
        Path(path).unlink(missing_ok=True)


def test_current_node_first_workbook_aliases_pass():
    """A populated v9.7.x extraction workbook may use node-first sheet names/headers.
    The content gate should pass when it can prove populated BGC rows are present (v9.7.128)."""
    import openpyxl, tempfile
    from pathlib import Path
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet("BGC_Inventory")
    ws.append(["Node/contig ID", "Assembly locator", "BGC"])
    ws.append(["NODE_1", "NODE_1 region001 (BGC001)", "BGC001"])
    ws = wb.create_sheet("Triage_First_Board")
    ws.append(["BGC", "AB score", "AF score"])
    ws.append(["BGC001", 10, 20])
    ws = wb.create_sheet("WetLab_Decision_Matrix")
    ws.append(["BGC_ID", "Decision_status"])
    ws.append(["BGC001", "MAMEY_EXTRACTION_TRIAGE"])
    ws = wb.create_sheet("Mode_B_Summary")
    ws.append(["BGC_ID", "Mode_B_status"])
    ws.append(["BGC001", "JUDGMENT_PENDING"])
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        path = f.name
    try:
        wb.save(path)
        result = validate_workbook_content(path)
        assert result["status"] == "PASS", result
        assert result["sheets"]["Triage_Board"]["sheet"] == "Triage_First_Board"
    finally:
        Path(path).unlink(missing_ok=True)
