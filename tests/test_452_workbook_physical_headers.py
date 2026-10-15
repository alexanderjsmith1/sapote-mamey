import openpyxl
from mamey import workbook_schema_check as mod

def test_blank_header_cannot_shift_physical_column_contract(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "CANONICAL_REQUIRED", {"A2_Test"})
    monkeypatch.setattr(mod, "REQUIRED_SHEETS", {"A2_Test": {"columns": ["strain", "value"], "type": "fixed"}})
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "A2_Test"
    sheet.append([None, "strain", "value"])
    sheet.append([None, "SYN-A", 1])
    target = tmp_path / "shifted.xlsx"
    book.save(target)
    result = mod.validate(str(target))
    assert result["status"] == "FAIL"
    assert result["column_errors"][0]["mismatches"][0]["position"] == 1
