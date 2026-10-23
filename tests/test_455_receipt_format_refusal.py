"""Malformed receipt format must use the verifier's normal refusal channel."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = ROOT / "tools/verify_external_validation_receipt.py"


def _helper():
    spec = importlib.util.spec_from_file_location("receipt_format", HELPER_PATH)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


def _input(tmp_path, raw):
    source = tmp_path / "source"
    source.mkdir()
    receipt = tmp_path / "receipt.json"
    receipt.write_bytes(raw)
    return source, receipt, hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize("payload", [[], None, False, 0, "text", 1.5])
def test_non_object_receipt_uses_typed_refusal(tmp_path, payload):
    helper = _helper()
    source, receipt, digest = _input(tmp_path, json.dumps(payload).encode())
    with pytest.raises(helper.ReceiptRefused, match="receipt must be a JSON object"):
        helper.verify_receipt(receipt, source, digest)


@pytest.mark.parametrize("raw", [b"[]", b"null", b"true", b'"text"', b"\xff"])
def test_malformed_receipt_cli_refuses_without_traceback(tmp_path, raw, capsys):
    helper = _helper()
    source, receipt, digest = _input(tmp_path, raw)
    result = helper.main(["--root", str(source), "--receipt", str(receipt),
                          "--expected-receipt-sha256", digest])
    assert result == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "EXTERNAL VALIDATION RECEIPT: REFUSED:" in captured.err
    assert "Traceback" not in captured.err


def test_object_still_receives_existing_schema_checks(tmp_path):
    helper = _helper()
    source, receipt, digest = _input(tmp_path, b"{}")
    with pytest.raises(helper.ReceiptRefused, match="receipt schema"):
        helper.verify_receipt(receipt, source, digest)
