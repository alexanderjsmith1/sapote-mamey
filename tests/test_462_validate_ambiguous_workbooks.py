"""DREL-016: validate never checks one of several matching workbooks and ignores the rest."""
from argparse import Namespace

import openpyxl
import pytest

import mamey.cli as cli


@pytest.fixture(autouse=True)
def package_passes(monkeypatch):
    monkeypatch.setattr(cli, "validate_package", lambda *a, **k: {"status": "PASS"})


def _workbook(path):
    wb = openpyxl.Workbook()
    wb.active.title = "BGC_Inventory"
    wb.active.append(["BGC_ID"])
    wb.save(path)


def _validate(pkg, strict):
    return cli.validate_command(Namespace(package_dir=str(pkg), manifest_contract=False, workbook_strict=strict))


def test_two_workbooks_fail_strict_and_are_both_named(tmp_path, capsys):
    _workbook(tmp_path / "SYN-1_5_workbook.xlsx")
    _workbook(tmp_path / "SYN-2_5_workbook.xlsx")
    assert _validate(tmp_path, True) == 1
    out = capsys.readouterr().out
    assert "FAIL_WORKBOOK_AMBIGUOUS" in out
    assert "SYN-1_5_workbook.xlsx" in out and "SYN-2_5_workbook.xlsx" in out


def test_two_workbooks_are_reported_without_strict(tmp_path, capsys):
    _workbook(tmp_path / "SYN-1_5_workbook.xlsx")
    _workbook(tmp_path / "SYN-2_5_workbook.xlsx")
    assert _validate(tmp_path, False) == 0
    assert "FAIL_WORKBOOK_AMBIGUOUS" in capsys.readouterr().out


def test_single_workbook_is_still_content_checked(tmp_path, capsys):
    _workbook(tmp_path / "SYN-1_5_workbook.xlsx")
    _validate(tmp_path, False)
    assert "FAIL_WORKBOOK_AMBIGUOUS" not in capsys.readouterr().out
