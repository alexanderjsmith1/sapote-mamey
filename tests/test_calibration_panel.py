import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PANEL_PATH = ROOT / "mamey" / "data" / "calibration_panel.json"
BASELINE_PATH = ROOT / "mamey" / "data" / "calibration_baseline.json"
RUNNER = ROOT / "tools" / "calibration_run.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("calibration_run", RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_panel_is_complete_and_source_bound():
    panel = json.loads(PANEL_PATH.read_text())
    assert panel["schema_version"] == "mamey_calibration_panel_v1"
    assert len(panel["reference_controls"]) == 75
    assert len(panel["live_targets"]) == 13
    assert {row["scan"] for row in panel["synthetic_cases"]} == {
        "cctt", "cgad", "resistance", "tfbs", "umed", "blda_tta", "cassettes", "rggmci"
    }
    assert all(any(row["expected_positive"] for row in panel["synthetic_cases"] if row["scan"] == scan) for scan in {row["scan"] for row in panel["synthetic_cases"]})
    assert all(any(not row["expected_positive"] for row in panel["synthetic_cases"] if row["scan"] == scan) for scan in {row["scan"] for row in panel["synthetic_cases"]})
    ref = ROOT / "mamey" / "data" / "reference_bgc_library.json"
    assert hashlib.sha256(ref.read_bytes()).hexdigest() == panel["sources"]["reference_bgc_library.json"]["sha256"]


def test_every_case_and_live_target_has_complete_identity():
    panel = json.loads(PANEL_PATH.read_text())
    required = ("strain", "full_node_or_contig", "region", "bgc_alias")
    for row in panel["synthetic_cases"]:
        assert all(row["identity"].get(key) for key in required)
    for row in panel["live_targets"]:
        assert all(row.get(key) for key in required)


def test_stored_baseline_is_panel_bound():
    baseline = json.loads(BASELINE_PATH.read_text())
    assert baseline["panel_sha256"] == hashlib.sha256(PANEL_PATH.read_bytes()).hexdigest()


def test_runner_passes_and_reports_per_scan_metrics(tmp_path):
    output = tmp_path / "drift.json"
    completed = subprocess.run([sys.executable, str(RUNNER), "--out", str(output)], cwd=ROOT, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    report = json.loads(output.read_text())
    assert report["status"] == "PASS"
    assert report["flipped_calls"] == []
    assert report["recall_drops"] == []
    assert report["precision_drops"] == []
    assert report["executed_denominator"] == {
        "synthetic_executed": 18,
        "reference_controls_unexercisable": 75,
        "live_targets_unexecuted": 13,
    }
    assert set(report["per_scan"]) == {"cctt", "cgad", "resistance", "tfbs", "umed", "blda_tta", "cassettes", "rggmci"}
    assert all(row["recall"] == 1.0 and row["precision"] == 1.0 for row in report["per_scan"].values())


def test_recall_drop_is_nonzero_and_flip_has_complete_identity(monkeypatch):
    runner = _load_runner()
    monkeypatch.setitem(runner.CCTT_PATTERNS, "T43-HAL_halogenase", [r"never_matches_this_control"])
    report = runner.run(PANEL_PATH, BASELINE_PATH)
    assert report["status"] == "FAIL_CALL_FLIP"
    assert report["recall_drops"][0]["scan"] == "cctt"
    flip = next(row for row in report["flipped_calls"] if row["case_id"] == "SYN-CCTT-001")
    assert flip["identity_display"] == "CAL-SYN / synthetic_contig_01 / region001 / CAL-BGC-001"


def test_false_positive_is_nonzero_and_precision_gated(monkeypatch):
    runner = _load_runner()
    original = runner.evaluate_case

    def force_one_negative_positive(case):
        if case["case_id"] == "NEG-CCTT-001":
            return False
        return original(case)

    monkeypatch.setattr(runner, "evaluate_case", force_one_negative_positive)
    report = runner.run(PANEL_PATH, BASELINE_PATH)
    assert report["status"] == "FAIL_CALL_FLIP"
    assert report["recall_drops"] == []
    assert report["precision_drops"] == [{
        "scan": "cctt", "baseline_precision": 1.0, "current_precision": 0.5,
    }]
    flip = next(row for row in report["flipped_calls"] if row["case_id"] == "NEG-CCTT-001")
    assert flip["identity_display"] == "CAL-SYN / synthetic_contig_11 / region001 / CAL-BGC-011"


def test_live_panel_missing_inputs_is_explicit_skip(tmp_path):
    runner = _load_runner()
    report = runner.run(PANEL_PATH, BASELINE_PATH, tmp_path)
    assert report["live_panel"]["status"] == "LIVE_INPUTS_ABSENT_SKIP"
    assert report["live_panel"]["verified"] == 0
    assert len(report["live_panel"]["missing"]) == 13


@pytest.mark.skipif(not os.environ.get("MAMEY_CALIBRATION_INPUT_ROOT"), reason="external antiSMASH calibration inputs not supplied")
def test_live_panel_hashes_when_inputs_are_supplied():
    runner = _load_runner()
    report = runner.run(PANEL_PATH, BASELINE_PATH, Path(os.environ["MAMEY_CALIBRATION_INPUT_ROOT"]))
    assert report["live_panel"]["status"] == "LIVE_INPUTS_HASH_VERIFIED"
    assert report["live_panel"]["verified"] == 13
