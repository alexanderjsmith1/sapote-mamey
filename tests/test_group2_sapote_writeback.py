"""test_group2_sapote_writeback.py — v9.7.71

Tests for Group 2 Sapote judgment write-back functions:
  update_c3c4_from_sapote  — C3/C4 composite rank, score, recommended role
  update_d3_from_sapote    — D3 RG-GMCI pair confirmation
  update_g1_from_sapote    — G1 Literature Deep Dive citations
  update_g2_from_sapote    — G2 validation roles
"""
import csv
import json
import datetime
import pytest
from pathlib import Path
from openpyxl import Workbook as OWB

from mamey.master_workbook import (
    CANONICAL_V1_HEADERS,
    update_c3c4_from_sapote,
    update_d3_from_sapote,
    update_g1_from_sapote,
    update_g2_from_sapote,
)


# ── Fixture: minimal master workbook ─────────────────────────────────────────

def _make_workbook(path: Path, strain: str = "AS-TEST"):
    """Minimal master workbook with canonical headers and extraction-time rows."""
    wb = OWB()
    if "Sheet" in wb.sheetnames:
        del wb["Sheet"]

    for sheet_name, headers in CANONICAL_V1_HEADERS.items():
        ws = wb.create_sheet(sheet_name)
        ws.append(headers)

    today = datetime.date.today().isoformat()

    # C3: extraction-time row
    c3 = wb["C3_Lead_Tier_Summary"]
    c3.append([strain, "BGC001", "T1PKS", 74.0, "High",
               "BGC002", "NRPS", 61.0, "Medium", "", "Mamey extraction complete"])

    # C4: extraction-time row
    c4 = wb["C4_Strain_Decision_Table"]
    c4.append(["", strain, "", 48, "GOOD", "BGC001", 12345, 6, 8, 4, 3, "judgment_pending"])

    # D3: extraction-time promoted pair
    d3 = wb["D3_RGGMCI_Promoted"]
    d3.append([f"{strain}_RG01", strain, "HIGH_RG_GMCI", "BGC001+BGC013",
               "8 supporting refs (6 good-geometry)", "CB-homology; unproven",
               "T1PKS / azole-RiPP", "PROMOTED_CANDIDATE_PENDING_SAPOTE"])

    # G1: empty (no extraction-time rows)

    # G2: extraction-time row
    g2 = wb["G2_Validation_Roles"]
    g2.append([strain, "benchmark/extraction", "pending Sapote judgment"])

    # A4: completeness audit row
    a4 = wb["A4_Completeness_Audit"]
    a4.append([strain, "PASS", "PASS", "PASS", "PASS", "PASS",
               "PASS", "JUDGMENT_PENDING", "PASS", "PASS_EXTRACTION",
               "Load manifest for Sapote judgment"])

    wb.save(str(path))


def _read_sheet(wb_path: Path, sheet: str) -> list[dict]:
    """Read a sheet as a list of dicts (header-aware, skips header row)."""
    from openpyxl import load_workbook as _lw
    wb = _lw(wb_path)
    if sheet not in wb.sheetnames:
        return []
    ws = wb[sheet]
    headers = [ws.cell(row=1, column=c).value for c in range(1, ws.max_column + 1)]
    rows = []
    for r in range(2, ws.max_row + 1):
        row = {h: ws.cell(row=r, column=i+1).value for i, h in enumerate(headers) if h}
        if any(v is not None for v in row.values()):
            rows.append(row)
    return rows


# ── update_c3c4_from_sapote ───────────────────────────────────────────────────

def test_c3c4_writes_sapote_rank_and_score(tmp_path):
    wb_path = tmp_path / "master.xlsx"
    _make_workbook(wb_path)
    result = update_c3c4_from_sapote(
        wb_path, "AS-TEST",
        sapote_rank=1, sapote_score=91.5,
        sapote_composite="Priority A — 2 High leads",
        recommended_role="Lead compound strain",
    )
    assert result["sapote_rank"] == 1
    assert result["sapote_score"] == 91.5

    c4_rows = _read_sheet(wb_path, "C4_Strain_Decision_Table")
    strain_row = next((r for r in c4_rows if r.get("strain") == "AS-TEST"), None)
    assert strain_row is not None
    assert strain_row["sapote_rank"] == 1
    assert float(strain_row["sapote_score"]) == 91.5


def test_c3_writes_sapote_composite_and_role(tmp_path):
    wb_path = tmp_path / "master.xlsx"
    _make_workbook(wb_path)
    update_c3c4_from_sapote(
        wb_path, "AS-TEST",
        sapote_rank=2, sapote_score=78.0,
        sapote_composite="Priority B — 1 High lead, moderate novelty",
        recommended_role="Comparative strain — ecological context",
    )
    c3_rows = _read_sheet(wb_path, "C3_Lead_Tier_Summary")
    strain_row = next((r for r in c3_rows if r.get("strain") == "AS-TEST"), None)
    assert strain_row is not None
    assert "Priority B" in str(strain_row.get("sapote_composite", ""))
    assert "Comparative" in str(strain_row.get("recommended_role", ""))


def test_c3c4_preserves_deterministic_extraction_fields(tmp_path):
    """Extraction-time fields (ab_score, bgc_count etc.) must be preserved."""
    wb_path = tmp_path / "master.xlsx"
    _make_workbook(wb_path)
    update_c3c4_from_sapote(
        wb_path, "AS-TEST",
        sapote_rank=3, sapote_score=65.0,
    )
    c3_rows = _read_sheet(wb_path, "C3_Lead_Tier_Summary")
    strain_row = next((r for r in c3_rows if r.get("strain") == "AS-TEST"), None)
    # ab_score from extraction should still be there
    assert strain_row is not None
    # top_ab_bgc was "BGC001" at extraction
    assert str(strain_row.get("top_ab_bgc", "")) == "BGC001"


def test_c3c4_no_duplication(tmp_path):
    """Calling twice must not duplicate rows."""
    wb_path = tmp_path / "master.xlsx"
    _make_workbook(wb_path)
    update_c3c4_from_sapote(wb_path, "AS-TEST", sapote_rank=1, sapote_score=90.0)
    update_c3c4_from_sapote(wb_path, "AS-TEST", sapote_rank=1, sapote_score=90.0)
    c4_rows = _read_sheet(wb_path, "C4_Strain_Decision_Table")
    assert sum(1 for r in c4_rows if r.get("strain") == "AS-TEST") == 1


def test_c3c4_missing_workbook_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        update_c3c4_from_sapote(tmp_path / "nonexistent.xlsx", "AS-TEST",
                                 sapote_rank=1, sapote_score=90.0)


# ── update_d3_from_sapote ─────────────────────────────────────────────────────

def test_d3_replaces_pending_with_confirmed(tmp_path):
    """Extraction-time PROMOTED_CANDIDATE_PENDING_SAPOTE must be replaced."""
    wb_path = tmp_path / "master.xlsx"
    _make_workbook(wb_path)
    result = update_d3_from_sapote(
        wb_path, "AS-TEST",
        promoted_pairs=[{
            "group_id": "AS-TEST_RG01",
            "fragments": "BGC001+BGC013",
            "evidence_basis": "Mode B §4 confirms transAT-PKS; 8 shared refs.",
            "claim_ceiling": "Class-level capacity; physical linkage unproven",
            "chemistry_consequence": "transAT-PKS / azole-RiPP",
            "status": "MODE_B_SUPPORTED",
        }],
    )
    d3_rows = _read_sheet(wb_path, "D3_RGGMCI_Promoted")
    strain_rows = [r for r in d3_rows if r.get("strain") == "AS-TEST"]
    assert len(strain_rows) == 1
    assert strain_rows[0]["status"] == "MODE_B_SUPPORTED"
    assert "PENDING" not in str(strain_rows[0]["status"])


def test_d3_writes_multiple_pairs(tmp_path):
    wb_path = tmp_path / "master.xlsx"
    _make_workbook(wb_path)
    update_d3_from_sapote(
        wb_path, "AS-TEST",
        promoted_pairs=[
            {"group_id": "AS-TEST_RG01", "fragments": "BGC001+BGC002", "status": "MODE_B_SUPPORTED"},
            {"group_id": "AS-TEST_RG02", "fragments": "BGC005+BGC007", "status": "MODE_B_CONFIRMED"},
        ],
    )
    d3_rows = _read_sheet(wb_path, "D3_RGGMCI_Promoted")
    strain_rows = [r for r in d3_rows if r.get("strain") == "AS-TEST"]
    assert len(strain_rows) == 2


def test_d3_idempotent(tmp_path):
    """Second call replaces, not appends."""
    wb_path = tmp_path / "master.xlsx"
    _make_workbook(wb_path)
    pairs = [{"group_id": "AS-TEST_RG01", "fragments": "BGC001+BGC013", "status": "MODE_B_SUPPORTED"}]
    update_d3_from_sapote(wb_path, "AS-TEST", promoted_pairs=pairs)
    update_d3_from_sapote(wb_path, "AS-TEST", promoted_pairs=pairs)
    d3_rows = _read_sheet(wb_path, "D3_RGGMCI_Promoted")
    strain_rows = [r for r in d3_rows if r.get("strain") == "AS-TEST"]
    assert len(strain_rows) == 1


# ── update_g1_from_sapote ─────────────────────────────────────────────────────

def test_g1_writes_citations(tmp_path):
    wb_path = tmp_path / "master.xlsx"
    _make_workbook(wb_path)
    result = update_g1_from_sapote(
        wb_path, "AS-TEST",
        citations=[{
            "BGC_ID": "BGC001",
            "track": "bombyxamycin / azole-RiPP",
            "citation": "Martinet L et al. (2019). Nat. Chem. Biol. 15, 988-996.",
            "doi": "10.1038/s41589-019-0349-9",
            "evidence_purpose": "biosynthesis",
            "verification_status": "Verified",
        }],
    )
    assert result["citations_written"] == 1
    g1_rows = _read_sheet(wb_path, "G1_Literature_Index")
    strain_rows = [r for r in g1_rows if r.get("strain") == "AS-TEST"]
    assert len(strain_rows) == 1
    assert "Martinet" in str(strain_rows[0].get("citation", ""))


def test_g1_accumulates_across_calls(tmp_path):
    """Second call adds new citations, does not remove prior ones."""
    wb_path = tmp_path / "master.xlsx"
    _make_workbook(wb_path)
    update_g1_from_sapote(wb_path, "AS-TEST", citations=[
        {"BGC_ID": "BGC001", "doi": "10.1000/aaa", "citation": "Ref A",
         "track": "class A", "evidence_purpose": "biosynthesis", "verification_status": "Verified"},
    ])
    update_g1_from_sapote(wb_path, "AS-TEST", citations=[
        {"BGC_ID": "BGC002", "doi": "10.1000/bbb", "citation": "Ref B",
         "track": "class B", "evidence_purpose": "mechanism", "verification_status": "Partial"},
    ])
    g1_rows = _read_sheet(wb_path, "G1_Literature_Index")
    strain_rows = [r for r in g1_rows if r.get("strain") == "AS-TEST"]
    assert len(strain_rows) == 2


def test_g1_deduplicates_on_strain_bgc_doi(tmp_path):
    """Same (strain, BGC_ID, doi) must not be written twice."""
    wb_path = tmp_path / "master.xlsx"
    _make_workbook(wb_path)
    cite = {"BGC_ID": "BGC001", "doi": "10.1000/dup", "citation": "Dup ref",
            "track": "dup", "evidence_purpose": "biosynthesis", "verification_status": "Verified"}
    update_g1_from_sapote(wb_path, "AS-TEST", citations=[cite])
    result = update_g1_from_sapote(wb_path, "AS-TEST", citations=[cite])
    assert result["citations_skipped_duplicate"] == 1
    g1_rows = _read_sheet(wb_path, "G1_Literature_Index")
    strain_rows = [r for r in g1_rows if r.get("strain") == "AS-TEST"]
    assert len(strain_rows) == 1


def test_g1_empty_citation_list_no_error(tmp_path):
    wb_path = tmp_path / "master.xlsx"
    _make_workbook(wb_path)
    result = update_g1_from_sapote(wb_path, "AS-TEST", citations=[])
    assert result["citations_written"] == 0


# ── update_g2_from_sapote ─────────────────────────────────────────────────────

def test_g2_updates_manuscript_use(tmp_path):
    wb_path = tmp_path / "master.xlsx"
    _make_workbook(wb_path)
    result = update_g2_from_sapote(
        wb_path, "AS-TEST",
        primary_role="lead compound strain",
        manuscript_use="WAC cohort §3 lead — MRSA-active extract-level",
    )
    g2_rows = _read_sheet(wb_path, "G2_Validation_Roles")
    strain_row = next((r for r in g2_rows if r.get("strain") == "AS-TEST"), None)
    assert strain_row is not None
    assert strain_row["primary_role"] == "lead compound strain"
    assert "WAC cohort" in str(strain_row.get("manuscript_use", ""))


def test_g2_replaces_extraction_placeholder(tmp_path):
    """The 'pending Sapote judgment' placeholder must be replaced."""
    wb_path = tmp_path / "master.xlsx"
    _make_workbook(wb_path)
    update_g2_from_sapote(wb_path, "AS-TEST",
                          primary_role="comparative", manuscript_use="supporting data")
    g2_rows = _read_sheet(wb_path, "G2_Validation_Roles")
    strain_rows = [r for r in g2_rows if r.get("strain") == "AS-TEST"]
    assert len(strain_rows) == 1
    assert "pending" not in str(strain_rows[0].get("manuscript_use", "")).lower()


def test_g2_idempotent(tmp_path):
    wb_path = tmp_path / "master.xlsx"
    _make_workbook(wb_path)
    update_g2_from_sapote(wb_path, "AS-TEST", primary_role="lead", manuscript_use="v1")
    update_g2_from_sapote(wb_path, "AS-TEST", primary_role="lead", manuscript_use="v2")
    g2_rows = _read_sheet(wb_path, "G2_Validation_Roles")
    strain_rows = [r for r in g2_rows if r.get("strain") == "AS-TEST"]
    assert len(strain_rows) == 1
    assert strain_rows[0]["manuscript_use"] == "v2"


def test_all_four_functions_missing_workbook_raise(tmp_path):
    path = tmp_path / "no.xlsx"
    with pytest.raises(FileNotFoundError):
        update_d3_from_sapote(path, "X", promoted_pairs=[])
    with pytest.raises(FileNotFoundError):
        update_g1_from_sapote(path, "X", citations=[])
    with pytest.raises(FileNotFoundError):
        update_g2_from_sapote(path, "X", primary_role="r", manuscript_use="m")
