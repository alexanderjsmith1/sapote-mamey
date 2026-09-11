import importlib
wsc = importlib.import_module("mamey.workbook_schema_check")

def test_run_manifest_has_antismash_profile_column():
    cols = wsc.REQUIRED_SHEETS["A3_Run_Manifest"]["columns"]
    assert "antismash_profile" in cols
    assert cols.index("antismash_profile") == 4   # locked position: after 'mode'
