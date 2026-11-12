"""A strain without a TIGRFAM scan is "not scanned", not "none", and is left out of the diagnostic denominators."""
import json
import subprocess
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]


def _bank(tmp_path):
    bank = tmp_path / "bank"
    bank.mkdir()
    strains = {"S1": {"n50": 1000000, "corrected_bgcs": 1, "raw_bgcs": 1},
               "S2": {"n50": 1000000, "corrected_bgcs": 1, "raw_bgcs": 1}}
    bgcs = [{"sid": s, "products": "T1PKS", "bgc_id": "BGC001", "contig": "NODE_1", "region": "region001",
             "edge_status": "Interior", "kcb_cumulative": None} for s in strains]
    (bank / "bgc_data.json").write_text(json.dumps({"strains": strains, "bgcs": bgcs}))
    (bank / "tigrfam.json").write_text(json.dumps({"S1": {"present": {"TIGR03828": {}}}}))
    for name in ("gene_data.json", "deep_data.json", "rggmci_full.json"):
        (bank / name).write_text("{}")
    return bank


def _cells(path):
    wb = openpyxl.load_workbook(path)
    try:
        return [str(c.value) for ws in wb.worksheets for row in ws.iter_rows() for c in row if c.value is not None]
    finally:
        wb.close()


def test_unscanned_strain_is_not_counted_as_absent(tmp_path):
    out = tmp_path / "master.xlsx"
    wb = openpyxl.Workbook()
    wb.save(out)
    wb.close()
    r = subprocess.run([sys.executable, str(ROOT / "tools/add_xstrain_sheets.py"), "--banked-dir", str(_bank(tmp_path)),
                        "--out", str(out)], capture_output=True, text=True, cwd=str(ROOT), timeout=120)
    assert r.returncode == 0, r.stderr
    cells = _cells(out)
    assert "not scanned" in cells
    assert "1/1" in cells        # TIGR03828: one of the one scanned strain
    assert "0/1" in cells        # the other two diagnostics, over the scanned strain only
    assert any("1 strain(s) without a TIGRFAM scan are not counted" in c for c in cells)
