"""The judgment receipt accepts the checker's pass field only after a successful execution.

check_deliverable_suite exits 0 for pass and 1 for fail. A crash, an unexpected exit, or an
exit that disagrees with the printed pass field must leave the suite result unmeasured.
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
_spec = importlib.util.spec_from_file_location(
    "sapote_judgment_receipt_452", ROOT / "tools" / "sapote_judgment_receipt.py"
)
sjr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sjr)


def _call(monkeypatch, tmp_path, returncode, payload, stderr=""):
    manifest = tmp_path / "manifest.md"
    manifest.write_text("x", encoding="utf-8")
    (tmp_path / "check_deliverable_suite.py").write_text("", encoding="utf-8")
    monkeypatch.setattr(sjr.subprocess, "run", lambda args, **kwargs: subprocess.CompletedProcess(
        args, returncode, json.dumps(payload), stderr))
    return sjr.suite_pass(str(manifest), "gold", str(tmp_path))


def test_failed_execution_with_affirmative_field_is_unmeasured(monkeypatch, tmp_path):
    state, detail = _call(monkeypatch, tmp_path, 2, {"pass": True, "findings": []}, "Traceback")
    assert state is None
    assert "exit 2" in detail and "Traceback" in detail


def test_pass_field_disagreeing_with_exit_is_unmeasured(monkeypatch, tmp_path):
    state, _ = _call(monkeypatch, tmp_path, 1, {"pass": True, "findings": []})
    assert state is None


def test_successful_pass_is_accepted(monkeypatch, tmp_path):
    state, findings = _call(monkeypatch, tmp_path, 0, {"pass": True, "findings": []})
    assert state is True and findings == []


def test_measured_fail_is_kept(monkeypatch, tmp_path):
    state, findings = _call(monkeypatch, tmp_path, 1, {"pass": False, "findings": ["missing item"]})
    assert state is False and findings == ["missing item"]
