"""validate --workbook-strict with no workbook to check is a typed failure, not a SKIP."""
from argparse import Namespace

import pytest

import mamey.cli as cli
import mamey.validate as validate_mod


@pytest.fixture
def package_status(monkeypatch):
    state = {"status": "PASS"}
    monkeypatch.setattr(cli, "validate_package", lambda *a, **k: {"status": state["status"]})
    return state


def _validate(pkg, strict):
    return cli.validate_command(Namespace(package_dir=str(pkg), manifest_contract=False, workbook_strict=strict))


def test_strict_without_workbook_fails_typed(tmp_path, capsys, package_status):
    assert _validate(tmp_path, True) == 1
    out = capsys.readouterr().out
    assert "FAIL_WORKBOOK_MISSING" in out and '"SKIP"' not in out


def test_ordinary_validation_without_workbook_still_skips(tmp_path, capsys, package_status):
    assert _validate(tmp_path, False) == 0
    out = capsys.readouterr().out
    assert '"SKIP"' in out and "FAIL_WORKBOOK_MISSING" not in out


@pytest.mark.parametrize("wb_status,strict,expected", [
    ("PASS", True, 0), ("FAIL", True, 1), ("FAIL", False, 0), ("PASS", False, 0),
])
def test_present_workbook_gate_unchanged(tmp_path, monkeypatch, package_status, wb_status, strict, expected):
    (tmp_path / "SYN-1_5_workbook.xlsx").write_bytes(b"")
    monkeypatch.setattr(validate_mod, "validate_workbook_content", lambda p: {"status": wb_status, "sheets": {}})
    assert _validate(tmp_path, strict) == expected


def test_failed_package_still_fails_without_strict(tmp_path, package_status):
    package_status["status"] = "FAIL"
    assert _validate(tmp_path, False) == 1
