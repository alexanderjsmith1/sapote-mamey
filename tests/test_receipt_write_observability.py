"""Focused regression tests for non-blocking receipt-write observability."""

import builtins
import logging
import warnings

from mamey import cli
from mamey import recovery_status
from mamey import validate as validate_mod


def test_phase_receipt_write_failure_logs_without_raising(tmp_path, monkeypatch, caplog):
    """The independent fallback channel must expose a failed phase receipt write."""
    package = tmp_path / "package"
    package.mkdir()

    def fail_open(*args, **kwargs):
        raise OSError("generic fixture refusal")

    monkeypatch.setattr(builtins, "open", fail_open)
    caplog.set_level(logging.WARNING, logger="mamey.cli")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        written = cli._phase_receipt(package, "probe", "START")

    assert written is False
    assert "phase receipt write failed for probe: OSError" in caplog.text


def test_terminal_status_receipt_failure_logs_and_remains_nonblocking(tmp_path, monkeypatch, caplog):
    """Terminal status still returns while its missing receipt becomes observable."""
    def fail_receipt(*args, **kwargs):
        raise OSError("generic fixture refusal")

    monkeypatch.setattr(recovery_status, "write_package_status_receipt", fail_receipt)
    caplog.set_level(logging.WARNING, logger="mamey.cli")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        terminal = cli._stamp_terminal_status(
            tmp_path,
            validator_status="PASS",
            issues=[],
        )

    assert terminal == "MAMEY_COMPLETE"
    assert "terminal package-status receipt write failed: OSError" in caplog.text


def test_validate_reports_status_receipt_write_failure_in_memory(tmp_path, monkeypatch):
    """The validator's returned receipt must expose its optional persistence failure."""
    package = tmp_path / "package"
    package.mkdir()

    def fail_receipt(*args, **kwargs):
        raise OSError("generic fixture refusal")

    monkeypatch.setattr(validate_mod, "write_package_status_receipt", fail_receipt)
    result = validate_mod.validate_package(package)

    assert result["package_status_receipt_write"] == {
        "state": "FAILED",
        "error_type": "OSError",
        "error": "generic fixture refusal",
    }
    assert result["status"] == "FAIL"
