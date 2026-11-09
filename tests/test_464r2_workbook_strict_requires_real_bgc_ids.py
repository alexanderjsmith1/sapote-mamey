"""`validate --workbook-strict` counts a primary-key cell only when it is a BGC ID of the package.

Before this card any cell that was neither blank nor PENDING counted as a populated row, so
"x", "TODO" or another package's alias passed the gate.
"""
from __future__ import annotations

import pytest

openpyxl = pytest.importorskip("openpyxl")

from mamey.validate import validate_workbook_content

SHEETS = ("BGC_Inventory", "Triage_Board", "WetLab_Decision_Matrix", "Mode_B_Summary")


def _workbook(tmp_path, values, triage_name="Triage_Board", inventory_ids=("BGC001", "BGC002")):
    pkg = tmp_path / "package"
    pkg.mkdir(parents=True)
    if inventory_ids is not None:
        (pkg / "EXAMPLE_2_inventory.csv").write_text(
            "BGC_ID,Contig\n" + "".join(f"{i},CTG_A\n" for i in inventory_ids), encoding="utf-8")
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name in SHEETS:
        ws = wb.create_sheet(triage_name if name == "Triage_Board" else name)
        ws.append(["BGC_ID", "Other"])
        for value in values.get(name, ["BGC001"]):
            ws.append([value, "v"])
    path = pkg / "EXAMPLE_5_workbook.xlsx"
    wb.save(path)
    return path


def test_real_inventory_ids_pass(tmp_path):
    result = validate_workbook_content(_workbook(tmp_path, {}))
    assert result["status"] == "PASS"
    assert result["bgc_id_authority"] == "PACKAGE_INVENTORY"


def test_a_non_id_value_fails_the_sheet(tmp_path):
    result = validate_workbook_content(_workbook(tmp_path, {"Mode_B_Summary": ["x"]}))
    sheet = result["sheets"]["Mode_B_Summary"]
    assert result["status"] == "FAIL"
    assert sheet["status"] == "FAIL_unrecognized_primary_key"
    assert sheet["unrecognized_examples"] == ["x"]


def test_a_well_formed_id_absent_from_the_inventory_fails(tmp_path):
    result = validate_workbook_content(_workbook(tmp_path, {"Triage_Board": ["BGC001", "BGC099"]}))
    sheet = result["sheets"]["Triage_Board"]
    assert sheet["status"] == "FAIL_unrecognized_primary_key"
    assert sheet["real_rows"] == 1 and sheet["unrecognized_rows"] == 1


def test_without_an_inventory_the_id_format_is_checked_and_reported(tmp_path):
    ok = validate_workbook_content(_workbook(tmp_path / "a", {}, inventory_ids=None))
    assert ok["status"] == "PASS" and ok["bgc_id_authority"] == "FORMAT_ONLY"
    bad = validate_workbook_content(_workbook(tmp_path / "b", {"BGC_Inventory": ["TODO"]}, inventory_ids=None))
    assert bad["sheets"]["BGC_Inventory"]["status"] == "FAIL_unrecognized_primary_key"


def test_the_older_triage_sheet_name_is_accepted_and_flagged(tmp_path):
    result = validate_workbook_content(_workbook(tmp_path, {}, triage_name="Triage_First_Board"))
    triage = result["sheets"]["Triage_Board"]
    assert triage["status"] == "PASS"
    assert triage["sheet"] == "Triage_First_Board"
    assert triage["legacy_alias"] is True
    assert result["sheets"]["BGC_Inventory"]["legacy_alias"] is False


def test_pending_and_blank_rows_still_do_not_count(tmp_path):
    result = validate_workbook_content(_workbook(tmp_path, {"Mode_B_Summary": ["PENDING", ""]}))
    assert result["sheets"]["Mode_B_Summary"]["status"] == "FAIL_all_pending"


def test_an_inventory_saved_with_a_bom_is_still_the_authority(tmp_path):
    path = _workbook(tmp_path, {"Mode_B_Summary": ["BGC777"]})
    inv = path.parent / "EXAMPLE_2_inventory.csv"
    inv.write_bytes(b"\xef\xbb\xbf" + inv.read_bytes())
    result = validate_workbook_content(path)
    assert result["bgc_id_authority"] == "PACKAGE_INVENTORY"
    assert result["sheets"]["Mode_B_Summary"]["status"] == "FAIL_unrecognized_primary_key"


def test_a_bad_key_after_row_200_is_found(tmp_path):
    ids = [f"BGC{i:03d}" for i in range(1, 251)]
    path = _workbook(tmp_path, {"Mode_B_Summary": ids[:249] + ["junk"]}, inventory_ids=ids)
    sheet = validate_workbook_content(path)["sheets"]["Mode_B_Summary"]
    assert sheet["rows_checked"] == 250
    assert sheet["status"] == "FAIL_unrecognized_primary_key"
    assert sheet["unrecognized_examples"] == ["junk"]


def test_strict_validate_warns_when_ids_were_checked_for_form_only(tmp_path):
    import subprocess
    import sys
    from pathlib import Path
    bundle = Path(__file__).resolve().parents[1]
    path = _workbook(tmp_path, {}, inventory_ids=None)
    out = subprocess.run([sys.executable, "mamey_run.py", "validate", str(path.parent), "--workbook-strict"],
                         cwd=bundle, capture_output=True, text=True, timeout=300).stdout
    assert "WORKBOOK_ID_AUTHORITY_WARNING" in out
    assert '"bgc_id_authority": "FORMAT_ONLY"' in out
