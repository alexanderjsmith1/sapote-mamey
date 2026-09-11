"""Generic baseline reproduction for unowned timing-receipt evidence loss."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.validate_timing_receipt_parity import audit


def _write_valid_receipts(package: Path) -> None:
    rows = [
        {"phase": "source_scans", "status": "START", "mono_ns": 1},
        {"phase": "source_scans", "status": "END", "mono_ns": 2},
    ]
    (package / "run_phase_receipts.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
    )


def _write_valid_timing_csv(package: Path) -> None:
    with (package / "GENERIC_timing_breakdown.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=["name", "status"])
        writer.writeheader()
        writer.writerow({"name": "source_scans", "status": "COMPLETE"})


def test_red_malformed_preferred_json_must_not_be_reported_as_default_pass(tmp_path: Path) -> None:
    """A present malformed JSON artifact must be a typed error, not an empty/missing warning."""
    _write_valid_receipts(tmp_path)
    _write_valid_timing_csv(tmp_path)
    (tmp_path / "GENERIC_timing_breakdown.json").write_text("{not-json", encoding="utf-8")

    result = audit(tmp_path)

    assert result["status"] == "FAIL"
    assert any(item.get("kind") == "timing_parse_error" for item in result["errors"])
    assert result["timing_phase_count"] == 0


def test_negative_control_valid_timing_and_closed_receipts_pass(tmp_path: Path) -> None:
    _write_valid_receipts(tmp_path)
    (tmp_path / "GENERIC_timing_breakdown.json").write_text(
        json.dumps({"phases": [{"name": "source_scans", "status": "COMPLETE"}]}),
        encoding="utf-8",
    )

    result = audit(tmp_path)

    assert result["status"] == "PASS"
    assert result["errors"] == []
    assert result["timing_phase_count"] == 1


def test_negative_control_missing_receipts_remains_a_failure(tmp_path: Path) -> None:
    (tmp_path / "GENERIC_timing_breakdown.json").write_text(
        json.dumps({"phases": [{"name": "source_scans", "status": "COMPLETE"}]}),
        encoding="utf-8",
    )

    result = audit(tmp_path)

    assert result["status"] == "FAIL"
    assert any(item.get("kind") == "missing_receipts" for item in result["errors"])


import pytest
from tools import validate_timing_receipt_parity as timing_gate

@pytest.mark.parametrize('data', [[], None, {}, {'phases': 'bad'}, {'phases': [None]}])
def test_malformed_timing_shapes_are_typed_failures(tmp_path, data):
    _write_valid_receipts(tmp_path)
    (tmp_path / 'GENERIC_timing_breakdown.json').write_text(json.dumps(data))
    result = audit(tmp_path)
    assert result['status'] == 'FAIL'
    assert any(e['kind'] == 'timing_parse_error' for e in result['errors'])

@pytest.mark.parametrize('data', [[], None, {}, 'bad'])
def test_malformed_receipt_objects_are_typed_failures(tmp_path, data):
    (tmp_path / 'run_phase_receipts.jsonl').write_text(json.dumps(data)+'\n')
    result = audit(tmp_path)
    assert result['status'] == 'FAIL'
    assert any(e['kind'] == 'receipt_parse_errors' for e in result['errors'])

def test_genuinely_absent_timing_retains_warning_policy(tmp_path):
    _write_valid_receipts(tmp_path)
    result = audit(tmp_path)
    assert result['status'] == 'PASS'
    assert any(e['kind'] == 'missing_timing' for e in result['warnings'])

def test_valid_csv_timing_fallback_remains_valid(tmp_path):
    _write_valid_receipts(tmp_path)
    _write_valid_timing_csv(tmp_path)
    assert audit(tmp_path)['status'] == 'PASS'

def test_unreadable_timing_is_typed_failure(tmp_path, monkeypatch):
    _write_valid_receipts(tmp_path)
    source = tmp_path / 'GENERIC_timing_breakdown.json'
    source.write_text('{}')
    original = Path.read_text
    def read(path, *args, **kwargs):
        if path == source:
            raise PermissionError('injected read failure')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'read_text', read)
    result = audit(tmp_path)
    assert result['status'] == 'FAIL'
    assert any(e['kind'] == 'timing_parse_error' for e in result['errors'])
