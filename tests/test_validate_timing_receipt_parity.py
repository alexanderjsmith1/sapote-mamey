import json
from pathlib import Path

from tools.validate_timing_receipt_parity import audit


def _write_receipts(pkg: Path, rows):
    (pkg / "run_phase_receipts.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def _write_timing(pkg: Path, phases):
    (pkg / "S_timing_breakdown.json").write_text(json.dumps({"phases": phases}))


def test_required_phase_start_without_end_fails(tmp_path):
    _write_receipts(tmp_path, [
        {"phase": "source_scans", "status": "START", "mono_ns": 1},
    ])
    _write_timing(tmp_path, [{"name": "source_scans", "status": "COMPLETE"}])
    result = audit(tmp_path)
    assert result["status"] == "FAIL"
    assert any(e["phase"] == "source_scans" for e in result["errors"])


def test_required_phase_with_end_passes(tmp_path):
    _write_receipts(tmp_path, [
        {"phase": "source_scans", "status": "START", "mono_ns": 1},
        {"phase": "source_scans", "status": "END", "mono_ns": 2},
    ])
    _write_timing(tmp_path, [{"name": "source_scans", "status": "COMPLETE"}])
    result = audit(tmp_path)
    assert result["status"] == "PASS"
    assert result["errors"] == []


def test_optional_lonely_start_warns_not_fails(tmp_path):
    _write_receipts(tmp_path, [
        {"phase": "brief_render", "status": "START", "mono_ns": 1},
    ])
    _write_timing(tmp_path, [{"name": "brief_render", "status": "COMPLETE"}])
    result = audit(tmp_path)
    assert result["status"] == "PASS"
    assert result["warnings"]
