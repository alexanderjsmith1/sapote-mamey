"""The cohort version gate reads every manifest row and can bind the intended workbook roster."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

openpyxl = pytest.importorskip("openpyxl")

PATH = Path(__file__).resolve().parents[1] / "tools" / "cohort_scoring_version_gate.py"
_spec = importlib.util.spec_from_file_location("cohort_gate_r3d", PATH)
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)


def _workbook(path, versions):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "A3_Run_Manifest"
    ws.append(["strain", "version"])
    for index, version in enumerate(versions):
        ws.append([f"row{index}", version])
    wb.save(path)


def test_a_later_manifest_row_under_another_engine_fails(tmp_path, capsys):
    _workbook(tmp_path / "STRAIN_A.xlsx", ["Mamey v1.9.96", "Mamey v1.9.91"])
    _workbook(tmp_path / "STRAIN_B.xlsx", ["Mamey v1.9.96"])
    assert G.main(["--workbooks-dir", str(tmp_path), "--engine", "1.9.96"]) == 1
    assert "1.9.91" in capsys.readouterr().err


def test_roster_mismatch_fails_even_when_every_read_row_matches(tmp_path, capsys):
    _workbook(tmp_path / "STRAIN_A.xlsx", ["Mamey v1.9.96"])
    roster = tmp_path / "roster.txt"
    roster.write_text("STRAIN_A\nSTRAIN_B\n")
    assert G.main(["--workbooks-dir", str(tmp_path), "--engine", "1.9.96", "--roster", str(roster)]) == 1
    assert "missing workbooks: STRAIN_B" in capsys.readouterr().err


def test_matching_roster_passes_and_says_what_was_read(tmp_path, capsys):
    _workbook(tmp_path / "STRAIN_A.xlsx", ["Mamey v1.9.96", "Mamey v1.9.96"])
    roster = tmp_path / "roster.txt"
    roster.write_text("STRAIN_A\n")
    assert G.main(["--workbooks-dir", str(tmp_path), "--engine", "1.9.96", "--roster", str(roster)]) == 0
    out = capsys.readouterr().out
    assert "2 manifest version record(s)" in out and "match the intended roster" in out


def test_without_a_roster_the_pass_says_no_roster_was_checked(tmp_path, capsys):
    _workbook(tmp_path / "STRAIN_A.xlsx", ["Mamey v1.9.96"])
    assert G.main(["--workbooks-dir", str(tmp_path), "--engine", "1.9.96"]) == 0
    assert "no intended roster was checked" in capsys.readouterr().out
