"""Directed Study Workbook full output.

Creates a multi-sheet workbook for Directed PKS studies. The writer accepts paths
to the CSV/JSON/Markdown artifacts emitted by Directed PKS Study Mode and packs
them into a single audit-friendly `.xlsx`.

The implementation uses openpyxl when available and falls back to a minimal
valid XLSX writer using the Python standard library.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import csv
import json
import os
import re
import zipfile
from xml.sax.saxutils import escape
from mamey.xlsx_determinism import save_workbook_safely as _save_wb_safely


def _discard_tmp(tmp: str) -> None:
    """AUDIT_374: remove a partial temp file on a failed write."""
    try:
        if os.path.exists(tmp):
            os.remove(tmp)
    except OSError:
        pass

REQUIRED_SHEETS = [
    "Overview",
    "Gene_Evidence",
    "Group_Machinery",
    "EFLS_Linkage",
    "EFLS_Fragments",
    "Comparator_Tracks",
    "LCMS_Handles",
    "Citation_Workorder",
    "Figure_QA",
    "Excluded_BGCs",
    "Next_Actions",
]

TEXT_HEAVY_SHEETS = {"Overview", "Next_Actions", "Figure_QA"}

def validate_required_sheets(sheet_names: list[str]) -> list[str]:
    return [sheet for sheet in REQUIRED_SHEETS if sheet not in sheet_names]

def _read_csv_rows(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        return list(csv.DictReader(handle))

def _read_json(path: Path | None) -> Any:
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(errors="replace"))

def _rows_from_json(value: Any, prefix: str = "") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(value, dict):
        flat: dict[str, Any] = {}
        for k, v in value.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, (dict, list)):
                rows.extend(_rows_from_json(v, key))
            else:
                flat[key] = v
        if flat:
            rows.append(flat)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            rows.extend(_rows_from_json(item, f"{prefix}[{i}]"))
    else:
        rows.append({prefix or "value": value})
    return rows

def _normalize_rows(rows: list[dict[str, Any]], default_message: str) -> tuple[list[str], list[list[Any]]]:
    if not rows:
        return ["status"], [[default_message]]
    headers: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in headers:
                headers.append(key)
    data = [[row.get(header, "") for header in headers] for row in rows]
    return headers, data

def build_workbook_tables(
    *,
    study_id: str,
    gene_evidence_csv: Path | None = None,
    group_machinery_csv: Path | None = None,
    efls_linkage_csv: Path | None = None,
    efls_fragments_csv: Path | None = None,
    comparator_tracks_csv: Path | None = None,
    lcms_handles_csv: Path | None = None,
    citation_workorder_csv: Path | None = None,
    figure_receipt_json: Path | None = None,
    excluded_bgc_csv: Path | None = None,
    directed_receipt_json: Path | None = None,
) -> dict[str, tuple[list[str], list[list[Any]]]]:
    """Build sheet tables from Directed PKS artifacts."""
    receipt = _read_json(directed_receipt_json)
    overview_rows = [
        {"field": "study_id", "value": study_id},
        {"field": "status", "value": receipt.get("status", "not_supplied") if isinstance(receipt, dict) else "not_supplied"},
        {"field": "claim_rule", "value": "comparator_context is not product_identity; functional_grouping is not physical linkage"},
    ]
    tables: dict[str, tuple[list[str], list[list[Any]]]] = {
        "Overview": _normalize_rows(overview_rows, "no overview rows"),
        "Gene_Evidence": _normalize_rows(_read_csv_rows(gene_evidence_csv), "gene evidence not supplied"),
        "Group_Machinery": _normalize_rows(_read_csv_rows(group_machinery_csv), "group machinery not supplied"),
        "EFLS_Linkage": _normalize_rows(_read_csv_rows(efls_linkage_csv), "EFLS linkage not supplied"),
        "EFLS_Fragments": _normalize_rows(_read_csv_rows(efls_fragments_csv), "EFLS fragments not supplied"),
        "Comparator_Tracks": _normalize_rows(_read_csv_rows(comparator_tracks_csv), "comparator tracks not supplied"),
        "LCMS_Handles": _normalize_rows(_read_csv_rows(lcms_handles_csv), "LCMS handles not supplied"),
        "Citation_Workorder": _normalize_rows(_read_csv_rows(citation_workorder_csv), "citation workorder not supplied"),
        "Figure_QA": _normalize_rows(_rows_from_json(_read_json(figure_receipt_json)), "figure QA not supplied"),
        "Excluded_BGCs": _normalize_rows(_read_csv_rows(excluded_bgc_csv), "excluded BGCs not supplied"),
        "Next_Actions": _normalize_rows([
            {"priority": 1, "next_action": "Integrate comparator tracks into directed study workbook"},
            {"priority": 2, "next_action": "Resolve citation work order primary references"},
            {"priority": 3, "next_action": "Use EFLS classifications to decide functional grouping vs split pathway"},
        ], "no next actions"),
    }
    return tables

def _safe_sheet_name(name: str) -> str:
    cleaned = re.sub(r"[\[\]\:\*\?\/\\]", "_", name)[:31]
    return cleaned or "Sheet"

def _write_with_openpyxl(tables: dict[str, tuple[list[str], list[list[Any]]]], out_xlsx: Path) -> Path:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.table import Table, TableStyleInfo

    wb = Workbook()
    default = wb.active
    wb.remove(default)

    header_fill = PatternFill("solid", fgColor="1F4E78")
    header_font = Font(color="FFFFFF", bold=True)
    thin = Side(style="thin", color="D9E2F3")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for sheet_name in REQUIRED_SHEETS:
        headers, data = tables.get(sheet_name, (["status"], [["not supplied"]]))
        ws = wb.create_sheet(_safe_sheet_name(sheet_name))
        ws.append(headers)
        for row in data:
            ws.append(["" if value is None else value for value in row])

        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = border

        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = Alignment(vertical="top", wrap_text=True)
                cell.border = border

        ws.freeze_panes = "A2"
        max_row = max(ws.max_row, 1)
        max_col = max(ws.max_column, 1)
        if max_row >= 2 and max_col >= 1:
            ref = f"A1:{get_column_letter(max_col)}{max_row}"
            table_name = re.sub(r"[^A-Za-z0-9_]", "", sheet_name)[:20] + "Table"
            tab = Table(displayName=table_name, ref=ref)
            style = TableStyleInfo(name="TableStyleMedium2", showFirstColumn=False, showLastColumn=False, showRowStripes=True, showColumnStripes=False)
            tab.tableStyleInfo = style
            try:
                ws.add_table(tab)
            except Exception:
                pass

        for col_idx, column_cells in enumerate(ws.columns, start=1):
            max_len = 0
            for cell in column_cells:
                text = str(cell.value or "")
                max_len = max(max_len, min(len(text), 72))
            width = min(max(max_len + 2, 10), 42 if sheet_name not in TEXT_HEAVY_SHEETS else 60)
            ws.column_dimensions[get_column_letter(col_idx)].width = width

    out_xlsx.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(out_xlsx) + ".tmp"
    try:
        _save_wb_safely(wb, tmp)
    except BaseException:
        _discard_tmp(tmp)
        raise
    os.replace(tmp, str(out_xlsx))
    return out_xlsx

def _col_name(index: int) -> str:
    name = ""
    while index:
        index, rem = divmod(index - 1, 26)
        name = chr(65 + rem) + name
    return name

def _minimal_xlsx(tables: dict[str, tuple[list[str], list[list[Any]]]], out_xlsx: Path) -> Path:
    """Write a minimal valid XLSX using inline strings."""
    out_xlsx.parent.mkdir(parents=True, exist_ok=True)
    sheet_names = REQUIRED_SHEETS
    tmp = str(out_xlsx) + ".tmp"
    try:
        _write_minimal_xlsx_zip(tmp, tables, sheet_names)
    except BaseException:
        _discard_tmp(tmp)
        raise
    os.replace(tmp, str(out_xlsx))
    return out_xlsx

def _write_minimal_xlsx_zip(zip_path: str, tables: dict[str, tuple[list[str], list[list[Any]]]], sheet_names: list[str]) -> None:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
""" + "".join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1, len(sheet_names)+1)) + """
</Types>""")
        z.writestr("_rels/.rels", """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""")
        z.writestr("xl/_rels/workbook.xml.rels", """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
""" + "".join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1, len(sheet_names)+1)) + """
</Relationships>""")
        z.writestr("xl/workbook.xml", """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>
""" + "".join(f'<sheet name="{escape(_safe_sheet_name(name))}" sheetId="{i}" r:id="rId{i}"/>' for i, name in enumerate(sheet_names, start=1)) + """
</sheets></workbook>""")
        for i, name in enumerate(sheet_names, start=1):
            headers, data = tables.get(name, (["status"], [["not supplied"]]))
            rows = [headers] + data
            row_xml = []
            for r_idx, row in enumerate(rows, start=1):
                cells = []
                for c_idx, value in enumerate(row, start=1):
                    ref = f"{_col_name(c_idx)}{r_idx}"
                    cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(value or ""))}</t></is></c>')
                row_xml.append(f'<row r="{r_idx}">' + "".join(cells) + "</row>")
            z.writestr(f"xl/worksheets/sheet{i}.xml", """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>
""" + "".join(row_xml) + """
</sheetData></worksheet>""")

def write_directed_study_workbook(out_xlsx: Path, rows_by_sheet: dict[str, list[dict]] | None = None, **artifact_paths: Any) -> Path:
    """Write a Directed Study workbook.

    Two modes:
    - rows_by_sheet supplied: write those rows under matching required sheets.
    - artifact_paths supplied: build sheets from Directed PKS output paths.
    """
    if rows_by_sheet is not None:
        tables = {
            sheet: _normalize_rows(rows_by_sheet.get(sheet, []), "no_rows_supplied")
            for sheet in REQUIRED_SHEETS
        }
    else:
        tables = build_workbook_tables(**artifact_paths)

    try:
        return _write_with_openpyxl(tables, out_xlsx)
    except Exception:
        return _minimal_xlsx(tables, out_xlsx)
