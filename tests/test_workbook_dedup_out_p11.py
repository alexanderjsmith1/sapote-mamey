"""OUT-P11 (v9.7.325): master-append idempotency for the sheets the old column-1 dropper missed.

The pre-fix drop_existing_strain keyed on column 1 and listed only 14 sheets, so:
  - C4_Strain_Decision_Table / D3_RGGMCI_Promoted (strain in column 2) silently no-op'd, and
  - B6/C1/C2/D2/E3 (strain in column 1, appended per strain) were not listed at all,
so re-ingesting the same strain DUPLICATED those rows. This locks the fix: header-located strain
column + the full per-strain allowlist, while append-log sheets stay untouched.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from mamey.workbook_dedup import drop_existing_strain
from mamey.master_workbook import CANONICAL_V1_HEADERS
import openpyxl


def _sheet(wb, name, headers):
    ws = wb.create_sheet(name)
    ws.append(headers)
    return ws


def _rows(ws):
    return [r for r in ws.iter_rows(min_row=2, values_only=True) if any(v not in (None, "") for v in r)]


def _real_headers(name):
    """Use the shipped canonical headers so the test tracks the real schema (incl. strain column)."""
    h = CANONICAL_V1_HEADERS[name]
    # B3's second element is a placeholder string, not a real column set; give it a concrete col.
    return ["strain", "ref1"] if name == "B3_Known_Cluster_Matrix" else list(h)


def _append_strain_row(ws, name, strain):
    hdr = _real_headers(name)
    row = ["" for _ in hdr]
    # place the strain id in whichever column the header calls "strain"
    row[hdr.index("strain")] = strain
    ws.append(row)


# sheets that MUST dedup, with their strain-column index (0-based) per the frozen schema
PER_STRAIN_COL2 = ["C4_Strain_Decision_Table", "D3_RGGMCI_Promoted"]         # strain in column 2
PER_STRAIN_COL1 = ["B6_Compound_Reference", "C1_DAPR_Antibacterial",
                   "C2_DAPR_Antifungal", "D2_RGGMCI_Top_Pairs", "E3_Megacluster_Registry"]


def _build():
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name in PER_STRAIN_COL1 + PER_STRAIN_COL2:
        ws = _sheet(wb, name, _real_headers(name))
        _append_strain_row(ws, name, "AS-40")   # first ingest
        _append_strain_row(ws, name, "AS-41")    # a different strain
    return wb


def test_reingest_does_not_duplicate_col1_and_col2_sheets():
    wb = _build()
    # simulate a re-ingest of AS-40: drop, then re-append its row (what update_master_workbook does)
    drop_existing_strain(wb, "AS-40")
    for name in PER_STRAIN_COL1 + PER_STRAIN_COL2:
        _append_strain_row(wb[name], name, "AS-40")
    # every sheet must have exactly one AS-40 row and the untouched AS-41 row
    for name in PER_STRAIN_COL1 + PER_STRAIN_COL2:
        hdr = _real_headers(name)
        sc = hdr.index("strain")
        strains = [r[sc] for r in _rows(wb[name])]
        assert strains.count("AS-40") == 1, f"{name}: AS-40 duplicated -> {strains}"
        assert strains.count("AS-41") == 1, f"{name}: AS-41 lost/duplicated -> {strains}"


def test_col2_sheet_rows_are_actually_removed():
    """Direct proof the column-2 keying works (the old dropper left these in place)."""
    wb = _build()
    removed = drop_existing_strain(wb, "AS-40")
    # one AS-40 row removed per listed sheet (7 sheets here)
    assert removed == len(PER_STRAIN_COL1 + PER_STRAIN_COL2)
    for name in PER_STRAIN_COL2:
        hdr = _real_headers(name)
        strains = [r[hdr.index("strain")] for r in _rows(wb[name])]
        assert "AS-40" not in strains, f"{name}: column-2 strain not removed"


def test_append_logs_are_preserved():
    """A3_Run_Manifest / H1_Handoff_Log accumulate history and must NOT be deduped."""
    wb = openpyxl.Workbook(); wb.remove(wb.active)
    a3 = _sheet(wb, "A3_Run_Manifest", list(CANONICAL_V1_HEADERS["A3_Run_Manifest"]))
    a3.append(["2026-07-18", "AS-40", "v1", "gold", "", "", "", "", "", ""])
    a3.append(["2026-07-18", "AS-40", "v1", "gold", "", "", "", "", "", ""])  # 2nd run of same strain
    h1 = _sheet(wb, "H1_Handoff_Log", list(CANONICAL_V1_HEADERS["H1_Handoff_Log"]))
    h1.append(["2026-07-18", "Mamey", "extract", "AS-40", "canonical", "", "PASS", ""])
    drop_existing_strain(wb, "AS-40")
    assert len(_rows(wb["A3_Run_Manifest"])) == 2, "run-manifest history must be preserved"
    assert len(_rows(wb["H1_Handoff_Log"])) == 1, "handoff log must be preserved"
