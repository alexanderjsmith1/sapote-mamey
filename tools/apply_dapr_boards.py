#!/usr/bin/env python3
"""apply_dapr_boards.py — re-apply the Sapote-layer DAPR judgment boards (C1/C2) to a workbook.

The DAPR antibacterial/antifungal leads are a judgment-layer artifact, not derivable from the
banked JSON, so a fresh deterministic build scaffolds C1/C2 empty. This restores them from the
banked board CSVs (cohort/c1_dapr_antibacterial.csv, cohort/c2_dapr_antifungal.csv).
Usage: python tools/apply_dapr_boards.py <workbook.xlsx> [--cohort cohort_dir]
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, os, openpyxl
from _wbio import atomic_save

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workbook")
    ap.add_argument("--cohort", default=os.path.join(os.path.dirname(__file__), "..", "cohort"))
    a = ap.parse_args()
    wb = openpyxl.load_workbook(a.workbook)
    for sheet, csvf in [("C1_DAPR_Antibacterial", "c1_dapr_antibacterial.csv"),
                        ("C2_DAPR_Antifungal", "c2_dapr_antifungal.csv")]:
        path = os.path.join(a.cohort, csvf)
        if sheet not in wb.sheetnames or not os.path.exists(path):
            emit(f"  skip {sheet} (sheet or CSV missing)"); continue
        ws = wb[sheet]; rows = list(csv.reader(open(path)))
        hdr, data = rows[0], rows[1:]
        if ws.max_row > 1:
            ws.delete_rows(2, ws.max_row - 1 + 5)
        for c, h in enumerate(hdr, 1):
            ws.cell(1, c, h)
        for i, r in enumerate(data, 2):
            for c, v in enumerate(r, 1):
                ws.cell(i, c, int(v) if c in (1, 5, 6) and str(v).strip().lstrip("-").isdigit() else (v or None))
        emit(f"  {sheet}: re-applied {len(data)} lead rows")
    atomic_save(wb, a.workbook)

if __name__ == "__main__":
    main()
