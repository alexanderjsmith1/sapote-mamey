"""UNEXECUTED I715 public audit/CLI and G45 producer-consumer controls.

Use the exact C21 and guards G45 payloads together only after clearance.
No log timestamps or phase labels are treated as run/attempt identities.
"""
import json

import pytest

from tools.validate_timing_receipt_parity import audit, main
from mamey.timing import TimingRecorder


def _write(package, statuses, *, phase="source_scans", timing="COMPLETE"):
    rows = [{"phase": phase, "status": status, "mono_ns": i + 1}
            for i, status in enumerate(statuses)]
    (package / "run_phase_receipts.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n")
    (package / "S_timing_breakdown.json").write_text(
        json.dumps({"phases": [{"name": phase, "status": timing}]}))


@pytest.mark.parametrize("statuses", [
    ["END", "START"], ["START", "END", "START"],
    ["START", "END", "START", "END"], ["END", "START", "END"],
])
def test_old_terminal_or_repeated_starts_do_not_bind_an_attempt(tmp_path, statuses):
    _write(tmp_path, statuses)
    result = audit(tmp_path)
    assert result["status"] == "FAIL"
    assert any(row["kind"] == "phase_attempt_identity_unverified" for row in result["errors"])
    if statuses[-1] == "START":
        assert any(row["kind"] == "started_without_terminal_receipt" for row in result["errors"])


@pytest.mark.parametrize("terminal", ["ERROR", "TIMEOUT", "SKIP", "SKIPPED"])
def test_complete_cannot_agree_with_unsuccessful_terminal(tmp_path, terminal):
    _write(tmp_path, ["START", terminal])
    result = audit(tmp_path)
    assert result["status"] == "FAIL"
    assert any(row["kind"] == "complete_timing_phase_without_successful_terminal_receipt"
               for row in result["errors"])


@pytest.mark.parametrize("statuses", [["END", "START"], ["START", "ERROR"]])
def test_optional_policy_stays_warning_until_strict(tmp_path, statuses):
    _write(tmp_path, statuses, phase="brief_render")
    result = audit(tmp_path)
    assert result["status"] == "PASS" and result["warnings"] and not result["errors"]
    strict = audit(tmp_path, strict=True)
    assert strict["status"] == "FAIL" and strict["errors"] and not strict["warnings"]


@pytest.mark.parametrize("statuses,timing", [(["END"], "COMPLETE"),
    (["START", "END"], "COMPLETE"), (["START", "ERROR"], "ERROR")])
def test_unambiguous_legacy_success_and_observed_failure_parity(tmp_path, statuses, timing):
    _write(tmp_path, statuses, timing=timing)
    assert audit(tmp_path)["status"] == "PASS"  # parity agreement, not run success


def test_file_order_is_not_replaced_by_clock_sorting(tmp_path):
    _write(tmp_path, ["END", "START"])
    path = tmp_path / "run_phase_receipts.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[0]["mono_ns"], rows[1]["mono_ns"] = 99, 1
    path.write_text("\n".join(map(json.dumps, rows)) + "\n")
    assert audit(tmp_path)["status"] == "FAIL"


def test_custom_required_phase_preserves_existing_selection_policy(tmp_path):
    _write(tmp_path, ["START", "ERROR"], phase="brief_render")
    assert audit(tmp_path, required_closure={"brief_render"})["status"] == "FAIL"


@pytest.mark.parametrize("strict,code", [(False, 0), (True, 1)])
def test_public_cli_keeps_optional_strict_exit_policy(tmp_path, capsys, strict, code):
    _write(tmp_path, ["START", "TIMEOUT"], phase="brief_render")
    assert main([str(tmp_path), "--json"] + (["--strict"] if strict else [])) == code
    assert json.loads(capsys.readouterr().out)["status"] == ("FAIL" if strict else "PASS")


@pytest.mark.parametrize("terminal", ["ERROR", "TIMEOUT", "SKIP", "SKIPPED"])
def test_g45_exported_failure_has_honest_parity(tmp_path, terminal):
    _write(tmp_path, ["START", terminal])
    recorder = TimingRecorder("S", "test", "x")
    result = recorder.write(tmp_path)
    assert result["phases"][0]["status"] == terminal
    assert audit(tmp_path)["status"] == "PASS"  # failure telemetry agrees


def test_g45_ambiguous_export_remains_unverified_by_parity(tmp_path):
    _write(tmp_path, ["START", "END", "START", "END"])
    result = TimingRecorder("S", "test", "x").write(tmp_path)
    assert result["phases"][0]["status"] == "ATTEMPT_ROSTER_UNVERIFIED"
    assert audit(tmp_path)["status"] == "FAIL"
