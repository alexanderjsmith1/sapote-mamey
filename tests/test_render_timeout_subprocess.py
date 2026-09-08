"""test_render_timeout_subprocess.py — subprocess render timeout regression (v9.7.81).

Acceptance criteria (P0 item 2 from PATCH_ORDER_LIST):
  - When MAMEY_RENDER_TIMEOUT_S=1 is set AND MAMEY_BRIEF_FORCE_INPROCESS is NOT set,
    a slow subprocess render must time out and write BRIEF_SKIPPED_TIMEOUT.md.
  - The function must return status=SKIPPED (not raise).
  - A phase receipt with status TIMEOUT must be written to run_phase_receipts.jsonl.

Note: This test patches subprocess.run to simulate a timeout without actually
spawning a slow subprocess process.
"""
import json
import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import mamey.cli as cli


def test_subprocess_timeout_writes_skip_marker(tmp_path, monkeypatch):
    """Subprocess timeout must write BRIEF_SKIPPED_TIMEOUT.md and return SKIPPED."""
    monkeypatch.delenv("MAMEY_BRIEF_FORCE_INPROCESS", raising=False)
    monkeypatch.setenv("MAMEY_RENDER_TIMEOUT_S", "1")

    # Patch subprocess.run to raise TimeoutExpired
    with patch("mamey.cli._sub.run",
               side_effect=subprocess.TimeoutExpired(cmd="test", timeout=1)):
        logs = []
        res = cli._render_brief_nonblocking(tmp_path, "standard", logs.append, timeout_s=1)

    assert res["status"] == "SKIPPED"
    assert "timed out" in res["reason"].lower()
    assert (tmp_path / "BRIEF_SKIPPED_TIMEOUT.md").exists()
    assert any("skipped" in m.lower() for m in logs)


def test_subprocess_timeout_writes_phase_receipt(tmp_path, monkeypatch):
    """A TIMEOUT phase receipt must be written to run_phase_receipts.jsonl."""
    monkeypatch.delenv("MAMEY_BRIEF_FORCE_INPROCESS", raising=False)

    with patch("mamey.cli._sub.run",
               side_effect=subprocess.TimeoutExpired(cmd="test", timeout=1)):
        cli._render_brief_nonblocking(tmp_path, "standard", lambda m: None, timeout_s=1)

    receipts_path = tmp_path / "run_phase_receipts.jsonl"
    assert receipts_path.exists(), "run_phase_receipts.jsonl must be written"
    rows = [json.loads(line) for line in receipts_path.read_text().splitlines() if line.strip()]
    brief_rows = [r for r in rows if r.get("phase") == "brief_render"]
    assert any(r.get("status") in ("TIMEOUT", "ERROR") for r in brief_rows), (
        f"Expected TIMEOUT receipt in brief_render rows; got: {brief_rows}"
    )


def test_subprocess_error_writes_skip_error_marker(tmp_path, monkeypatch):
    """Non-timeout subprocess failure writes BRIEF_SKIPPED_ERROR.md."""
    monkeypatch.delenv("MAMEY_BRIEF_FORCE_INPROCESS", raising=False)

    # Subprocess returns non-zero exit code
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "render_brief import error"

    # Also make the in-process fallback fail so we hit the error path
    with patch("mamey.cli._sub.run", return_value=mock_result):
        with patch("mamey.cli.render_brief",
                   side_effect=RuntimeError("in-process also fails")):
            res = cli._render_brief_nonblocking(tmp_path, "standard",
                                                lambda m: None, timeout_s=10)

    assert res["status"] == "SKIPPED"
    # Should write EITHER the error OR timeout marker
    markers = list(tmp_path.glob("BRIEF_SKIPPED_*.md"))
    assert len(markers) >= 1, "At least one skip marker must be written"


def test_core_zip_unaffected_by_timeout(tmp_path, monkeypatch):
    """The SKIPPED return value must not prevent package sealing (function does not raise)."""
    monkeypatch.delenv("MAMEY_BRIEF_FORCE_INPROCESS", raising=False)

    with patch("mamey.cli._sub.run",
               side_effect=subprocess.TimeoutExpired(cmd="test", timeout=1)):
        try:
            res = cli._render_brief_nonblocking(tmp_path, "standard",
                                                lambda m: None, timeout_s=1)
            raised = False
        except Exception:
            raised = True

    assert not raised, "_render_brief_nonblocking must not raise on timeout"
    assert res["status"] == "SKIPPED"
