"""The workbook BGC_Inventory sheet carries every inventory CSV column.

The sheet had 31 headers and the CSV 53. The claim limits (`product_claim_ceiling`,
`needs_manual_kcb_check`, `claim_ceiling`, `safe_claim`) and KCB provenance were only in the
CSV, so a workbook reader saw "KCB top" without its ceiling.
"""
from __future__ import annotations

import pytest

openpyxl = pytest.importorskip("openpyxl")

from mamey.workbook import _INVENTORY_CSV_SHOWN, _append_inventory_csv_columns


def _sheet():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Node/contig ID", "BGC", "KCB top", "Strain"])
    ws.append(["CTG_A", "BGC001", "examplomycin", "EXAMPLE"])
    ws.append(["CTG_B", "BGC002", "", "EXAMPLE"])
    return ws


def test_csv_only_columns_are_appended_and_joined_on_bgc_id(tmp_path):
    (tmp_path / "EXAMPLE_2_inventory.csv").write_text(
        "BGC_ID,Contig,KCB_top,product_claim_ceiling,needs_manual_kcb_check,safe_claim,Strain\n"
        "BGC002,CTG_B,,unresolved,yes,,EXAMPLE\n"
        "BGC001,CTG_A,examplomycin,class-level only,no,capacity consistent with a class,EXAMPLE\n",
        encoding="utf-8")
    ws = _sheet()
    added = _append_inventory_csv_columns(ws, tmp_path, "EXAMPLE")
    assert added == ["product_claim_ceiling", "needs_manual_kcb_check", "safe_claim"]
    header = [c.value for c in ws[1]]
    assert header[:4] == ["Node/contig ID", "BGC", "KCB top", "Strain"]
    row1 = dict(zip(header, [c.value for c in ws[2]]))
    row2 = dict(zip(header, [c.value for c in ws[3]]))
    assert row1["product_claim_ceiling"] == "class-level only"
    assert row2["needs_manual_kcb_check"] == "yes"
    assert row2["safe_claim"] in ("", None)  # blank stays blank


def test_no_csv_appends_nothing(tmp_path):
    ws = _sheet()
    assert _append_inventory_csv_columns(ws, tmp_path, "EXAMPLE") == []
    assert ws.max_column == 4


def test_shown_columns_cover_the_sheet_s_own_fields():
    for name in ("BGC_ID", "KCB_top", "KCB_score", "Boundary", "Strain"):
        assert name in _INVENTORY_CSV_SHOWN
    for name in ("product_claim_ceiling", "needs_manual_kcb_check", "claim_ceiling", "safe_claim"):
        assert name not in _INVENTORY_CSV_SHOWN


def test_whole_numbers_become_numbers_and_other_values_stay_text():
    from mamey.workbook import _csv_cell
    assert _csv_cell("1") == 1 and _csv_cell("-3") == -3 and _csv_cell("0") == 0
    for text in ("007", "1.5", "1e5", "yes", "", "NaN"):
        assert _csv_cell(text) == text
    assert _csv_cell(None) == ""


def test_write_per_strain_workbook_carries_the_claim_ceiling(tmp_path):
    """End to end: fails if write_per_strain_workbook stops calling the append helper."""
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location(
        "reporting_fixture", Path(__file__).with_name("test_reporting_evidence_v2.py"))
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    from mamey.antismash_evidence import extract_rrefinder_hits
    from mamey.antismash_tables import build_structured_tables
    from mamey.workbook import write_per_strain_workbook
    from types import SimpleNamespace
    archive = fixture._rre_zip(tmp_path, [fixture._record("NODE_1", {})])
    bgc = SimpleNamespace(bgc_id="BGC001", contig="NODE_1", start=100, end=1000,
                          products=["RiPP"], source_gbk="")
    structured = build_structured_tables(archive, {"rrefinder_hits": extract_rrefinder_hits(archive)}, [bgc])
    run = fixture._FakeRun(archive, structured)
    run.context.strain_id = "EXAMPLE"
    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "EXAMPLE_2_inventory.csv").write_text(
        "BGC_ID,KCB_top,kcb_hit_rank,product_claim_ceiling\n"
        "BGC001,examplomycin,1,class-level only\n", encoding="utf-8")
    out = pkg / "EXAMPLE_5_workbook.xlsx"
    write_per_strain_workbook(run, out)
    wb = openpyxl.load_workbook(out, read_only=True)
    rows = list(wb["BGC_Inventory"].iter_rows(values_only=True))
    wb.close()
    header = list(rows[0])
    assert "product_claim_ceiling" in header and "kcb_hit_rank" in header
    row = dict(zip(header, rows[1]))
    assert row["product_claim_ceiling"] == "class-level only"
    assert row["kcb_hit_rank"] == 1
