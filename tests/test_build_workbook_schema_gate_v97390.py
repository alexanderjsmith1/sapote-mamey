"""v9.7.390 regression coverage for the master-workbook schema release gate."""
from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "build_workbook.py"


def _module():
    spec = importlib.util.spec_from_file_location("build_workbook_v97390_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _completed(report, returncode=0):
    return subprocess.CompletedProcess(["schema"], returncode, stdout=json.dumps(report), stderr="")


def test_schema_gate_always_requests_v12(monkeypatch):
    module = _module()
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return _completed({"status": "PASS", "v1_2_errors": [], "sheets_missing": [], "column_errors": [], "consistency_errors": []})

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    module.validate_workbook("master.xlsx")
    assert calls[0][0] == [module.sys.executable, module.SCHEMA_CHECK, "--v12", "master.xlsx"]
    assert calls[0][1] == {"capture_output": True, "text": True}


@pytest.mark.parametrize(
    "report,returncode",
    [
        ({"status": "FAIL", "v1_2_errors": ["D5 missing"], "sheets_missing": [], "column_errors": [], "consistency_errors": []}, 1),
        ({"status": "FAIL", "v1_2_errors": [], "sheets_missing": ["A2"], "column_errors": [], "consistency_errors": []}, 1),
        ({"status": "PASS", "v1_2_errors": [], "sheets_missing": [], "column_errors": [], "consistency_errors": []}, 2),
    ],
)
def test_schema_gate_fails_closed(monkeypatch, report, returncode):
    module = _module()
    monkeypatch.setattr(module.subprocess, "run", lambda *_args, **_kwargs: _completed(report, returncode))
    with pytest.raises(SystemExit, match="FAILED at schema validation"):
        module.validate_workbook("master.xlsx")


def test_non_json_validator_output_fails_closed(monkeypatch):
    module = _module()
    bad = subprocess.CompletedProcess(["schema"], 1, stdout="traceback", stderr="broken")
    monkeypatch.setattr(module.subprocess, "run", lambda *_args, **_kwargs: bad)
    with pytest.raises(SystemExit, match="non-JSON"):
        module.validate_workbook("master.xlsx")


def test_diagnostic_escape_hatch_is_explicit(monkeypatch):
    module = _module()
    report = {"status": "FAIL", "v1_2_errors": ["D5 missing"], "sheets_missing": [], "column_errors": [], "consistency_errors": []}
    monkeypatch.setattr(module.subprocess, "run", lambda *_args, **_kwargs: _completed(report, 1))
    assert module.validate_workbook("master.xlsx", allow_schema_issues=True) == report
