"""test_exclusion_gate.py — the governed-output leak gate catches an injected AS-920 row.

AMBER_EXCLUSION_HARDENING (.353 candidate). Proves that a hard-excluded strain id
(governed_excluded() == {AS-920}) is refused at the governed output boundary, while
a governed-legitimate strain (AS-922, decontam strain-of-record) and clean tables pass.
"""
import csv

import pytest

from mamey import exclusion_gate, exclusions


# ── in-memory rows ────────────────────────────────────────────────────────────
def test_clean_rows_pass():
    rows = [["strain", "bgc_id", "class"],
            ["AS-40", "AS-40_BGC1", "NRPS"],
            ["AS-696", "AS-696_BGC2", "PKS"]]
    assert exclusion_gate.scan_rows(rows) == set()


def test_injected_as260_row_is_caught():
    rows = [["strain", "bgc_id", "class"],
            ["AS-40", "AS-40_BGC1", "NRPS"],
            ["AS-920", "AS-920_BGC3", "RiPP"]]  # <-- injected excluded strain
    assert exclusion_gate.scan_rows(rows) == {"AS-920"}


def test_id_embedded_in_a_larger_cell_is_caught():
    # a path/id like runs/AS-920/package or AS-920_BGC3 must still trip the gate
    assert exclusion_gate.excluded_ids_in_row(["runs/AS-920/package/_4_triage_board.csv"]) == {"AS-920"}
    assert exclusion_gate.excluded_ids_in_row({"col": "AS-920_BGC3"}) == {"AS-920"}


def test_boundary_ids_do_not_false_positive():
    # AS-9201 / AS-92 must NOT match AS-920
    assert exclusion_gate.scan_rows([["AS-9201", "AS-92", "xAS-920y"]]) == set()


def test_as683_is_governed_and_does_not_trip_the_governed_gate():
    # SSOT: AS-922 was ratified INTO governed (decontam strain-of-record).
    assert "AS-922" not in exclusions.governed_excluded()
    assert exclusion_gate.scan_rows([["AS-922", "AS-922_BGC1"]]) == set()


def test_as683_trips_the_raw_scope_when_that_set_is_passed():
    # raw-data modules pass raw_analysis_excluded() = {AS-920, AS-922}
    raw = exclusions.raw_analysis_excluded()
    assert exclusion_gate.scan_rows([["AS-922", "AS-922_BGC1"]], exclude=raw) == {"AS-922"}


# ── file-level gate: CSV ──────────────────────────────────────────────────────
def test_gate_fails_on_csv_with_injected_as260(tmp_path):
    board = tmp_path / "BGC_Master_governed.csv"
    with board.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["strain", "bgc_id", "tier"])
        w.writerow(["AS-40", "AS-40_BGC1", "Lead"])
        w.writerow(["AS-920", "AS-920_BGC3", "Lead"])  # leak
    result = exclusion_gate.gate_governed_outputs([board])
    assert result["status"] == "FAIL"
    assert result["offenders"][str(board)]["*"] == ["AS-920"]


def test_gate_passes_on_clean_csv(tmp_path):
    board = tmp_path / "BGC_Master_clean.csv"
    with board.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["strain", "bgc_id", "tier"])
        w.writerow(["AS-40", "AS-40_BGC1", "Lead"])
        w.writerow(["AS-922", "AS-922_BGC1", "Lead"])  # governed-legit
    result = exclusion_gate.gate_governed_outputs([board])
    assert result["status"] == "PASS"
    assert result["offenders"] == {}


# ── file-level gate: XLSX (mirrors the master workbook) ───────────────────────
def test_gate_fails_on_xlsx_with_injected_as260(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "BGC_Master"
    ws.append(["strain", "bgc_id", "tier"])
    ws.append(["AS-40", "AS-40_BGC1", "Lead"])
    ws.append(["AS-920", "AS-920_BGC3", "Lead"])  # injected leak into a governed sheet
    xlsx = tmp_path / "project_master.xlsx"
    wb.save(xlsx)

    sheet_hits = exclusion_gate.scan_xlsx(xlsx)
    assert sheet_hits == {"BGC_Master": {"AS-920"}}

    result = exclusion_gate.gate_governed_outputs([xlsx])
    assert result["status"] == "FAIL"
    assert result["offenders"][str(xlsx)]["BGC_Master"] == ["AS-920"]


# ── source-side guard (models the master_workbook.update_master_workbook wiring) ─
def test_assert_strain_governable_refuses_as260():
    with pytest.raises(ValueError):
        exclusion_gate.assert_strain_governable("AS-920")


def test_assert_strain_governable_allows_governed_strains():
    exclusion_gate.assert_strain_governable("AS-922")  # governed
    exclusion_gate.assert_strain_governable("AS-40")   # normal


# ── integration: the WIRED update_master_workbook guard refuses AS-920 ─────────
def test_wired_master_workbook_refuses_as260(tmp_path):
    """The .353 diff routes update_master_workbook through assert_strain_governable,
    which raises before any sheet is written when the strain is hard-excluded."""
    from types import SimpleNamespace
    from mamey import master_workbook
    fake_run = SimpleNamespace(context=SimpleNamespace(strain_id="AS-920"))
    with pytest.raises(ValueError):
        master_workbook.update_master_workbook(
            fake_run, tmp_path / "master.xlsx", tmp_path / "out.xlsx")
    # no governed workbook was produced for the excluded strain
    assert not (tmp_path / "out.xlsx").exists()

