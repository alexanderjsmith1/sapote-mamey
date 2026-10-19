"""Quarantine snapshot resource/error controls using generic temporary files.

Native tempfile rollover is retained except for precisely injected creation/copy
failures. Quarantine source failures retain the receipt-hold diagnostic prefix."""
import csv
import errno
import io
from pathlib import Path
import tempfile

import pytest
from mamey import blastp_gate as gate
from tests.test_452_identity_x34_quarantine_index import _toy_package
from tests.test_452_identity_x34_snapshot_resources import _bind_payload, _evidence, _track_spools


CHUNK = 1024 * 1024


def _large_payload(original):
    header, row = original.splitlines(keepends=True)
    return header + row * ((2 * CHUNK // len(row)) + 2)


@pytest.mark.parametrize("fault", ["create", "copy"])
def test_native_rollover_failure_holds_and_closes_owned_storage(tmp_path, monkeypatch, fault):
    quarantine, original = _toy_package(tmp_path, monkeypatch)
    _bind_payload(tmp_path, quarantine, _large_payload(original))
    before = _evidence(tmp_path)
    spools = _track_spools(monkeypatch)
    native_factory = tempfile.TemporaryFile
    reached, native_files = [], []

    class CopyFailure:
        def __init__(self, inner):
            self.inner = inner
        def __getattr__(self, name):
            return getattr(self.inner, name)
        def write(self, data):
            reached.append("copy")
            raise OSError(errno.ENOSPC, "synthetic rollover copy refusal")

    def failing_factory(*args, **kwargs):
        reached.append("create")
        if fault == "create":
            raise OSError(errno.ENOSPC, "synthetic rollover storage refusal")
        inner = native_factory(*args, **kwargs)
        native_files.append(inner)
        return CopyFailure(inner)

    monkeypatch.setattr(tempfile, "TemporaryFile", failing_factory)
    with pytest.raises(gate.BlastpDiscoveryError, match="BLASTP_REKEY_RECEIPT_HOLD"):
        gate._referenced_rekey_source_index(tmp_path)
    assert reached == (["create"] if fault == "create" else ["create", "copy"])
    assert len(spools) == 1 and spools[0].closed
    assert all(handle.closed for handle in native_files)
    assert _evidence(tmp_path) == before


@pytest.mark.parametrize("fault", ["open", "late_read"])
def test_source_io_failure_keeps_a_typed_hold_and_closes_partial_snapshot(tmp_path, monkeypatch, fault):
    quarantine, original = _toy_package(tmp_path, monkeypatch)
    _bind_payload(tmp_path, quarantine, _large_payload(original))
    before = _evidence(tmp_path)
    spools = _track_spools(monkeypatch)
    native_open = Path.open
    reads, opened = [], []

    class FailingReader:
        def __init__(self, handle):
            self.handle = handle
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.handle.close()
        def read(self, size=-1):
            reads.append(size)
            if len(reads) == 3:
                raise OSError(errno.EIO, "synthetic source read refusal after capture")
            return self.handle.read(size)

    def opening(path, *args, **kwargs):
        if path == quarantine:
            assert args and args[0] == "rb"
            if fault == "open":
                raise PermissionError("synthetic quarantine source refusal")
            handle = native_open(path, *args, **kwargs)
            opened.append(handle)
            return FailingReader(handle)
        return native_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", opening)
    with pytest.raises(gate.BlastpDiscoveryError) as raised:
        gate._referenced_rekey_source_index(tmp_path)
    assert str(raised.value).startswith("BLASTP_REKEY_RECEIPT_HOLD:")
    assert reads == ([] if fault == "open" else [CHUNK, CHUNK, CHUNK])
    assert len(spools) == 1 and spools[0].closed
    assert all(handle.closed for handle in opened)
    # Restore interception before reading original evidence; this is test-only state.
    monkeypatch.setattr(Path, "open", native_open)
    assert _evidence(tmp_path) == before


def _csv_row(values):
    buffer = io.StringIO(newline="")
    csv.writer(buffer, lineterminator="\r\n").writerow(values)
    return buffer.getvalue().encode("utf-8")


def test_multibyte_and_quoted_crlf_cross_capture_boundary_without_value_drift(tmp_path, monkeypatch):
    quarantine, _ = _toy_package(tmp_path, monkeypatch)
    header = _csv_row(["source_file", "source_file_sha256", "resolved_bgc", "reason", "padding"])
    normal = _csv_row(["toy-input.csv", "a" * 64, "current-old", "PAD", ""])
    reason = "TOY_é_HOLD\r\nsecond line"
    boundary = _csv_row(["toy-input.csv", "a" * 64, "current-old", reason, ""])
    count = (CHUNK // len(normal)) - 3
    prefix = header + normal * count
    padding = CHUNK - 1 - (len(prefix) + len(normal) + boundary.index("é".encode("utf-8")))
    assert 0 <= padding < 1024
    padded = _csv_row(["toy-input.csv", "a" * 64, "current-old", "PAD", "p" * padding])
    raw = prefix + padded + boundary
    assert raw[CHUNK - 1:CHUNK + 1] == "é".encode("utf-8")
    _bind_payload(tmp_path, quarantine, raw)
    before = _evidence(tmp_path)
    spools = _track_spools(monkeypatch)
    index, _ = gate._referenced_rekey_source_index(tmp_path)
    result, = index[("nr", "ITEM001", "a" * 64)]
    assert result["held_current_bgcs"] == ["current-old"]
    assert result["source_hold_reasons"] == {"PAD": count + 1, reason: 1}
    assert len(spools) == 1 and spools[0]._rolled is True and spools[0].closed
    assert _evidence(tmp_path) == before
