"""Generic quarantine snapshot lifetime, size and failure controls; no analyses."""
import csv
import hashlib
import io
import json
from pathlib import Path
import tempfile

import pytest
from mamey import blastp_gate as gate
from tests.test_452_identity_x34_quarantine_index import _toy_package
from tests.source_change_helpers import replace_after_first_binary_read


def _bind_payload(package, quarantine, raw):
    quarantine.write_bytes(raw)
    receipt_path = package / "blastp_ingest_receipts" / "toy.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["quarantine_sha256"] = hashlib.sha256(raw).hexdigest()
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")


def _evidence(package):
    return {str(p.relative_to(package)): p.read_bytes()
            for p in package.rglob("*") if p.is_file()}


def _track_spools(monkeypatch, fault=None):
    factory = tempfile.SpooledTemporaryFile
    created = []

    def tracked(*args, **kwargs):
        if fault == "create":
            raise PermissionError("synthetic temporary storage refusal")
        spool = factory(*args, **kwargs)
        created.append(spool)
        if fault in {"write", "read1", "seek"}:
            def refuse(*args, **kwargs):
                raise OSError("synthetic snapshot " + fault + " failure")
            setattr(spool, fault, refuse)
        return spool

    monkeypatch.setattr(tempfile, "SpooledTemporaryFile", tracked)
    return created


def test_large_quarantine_rolls_to_disk_and_keeps_verified_rows(tmp_path, monkeypatch):
    quarantine, original = _toy_package(tmp_path, monkeypatch)
    header, row = original.splitlines(keepends=True)
    count = (2 * 1024 * 1024 // len(row)) + 1
    raw = header + row * count
    _bind_payload(tmp_path, quarantine, raw)
    before = _evidence(tmp_path)
    created = _track_spools(monkeypatch)
    replacement = raw.replace(b"current-old", b"current-new")
    changed = replace_after_first_binary_read(monkeypatch, quarantine, replacement,
                                             binary_only=False)
    index, _ = gate._referenced_rekey_source_index(tmp_path)
    assert changed == [True]
    result, = index[("nr", "ITEM001", "a" * 64)]
    assert result["held_current_bgcs"] == ["current-old"]
    assert result["source_hold_reasons"] == {"TOY_HOLD": count}
    assert len(created) == 1 and created[0]._rolled is True
    assert created[0].closed
    after = _evidence(tmp_path)
    before["blastp_quarantine/toy.csv"] = replacement
    assert after == before


def test_capture_reads_source_once_in_bounded_chunks(tmp_path, monkeypatch):
    quarantine, original = _toy_package(tmp_path, monkeypatch)
    native_open = Path.open
    opens, reads = [], []

    class Reader:
        def __init__(self, handle):
            self.handle = handle
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.handle.close()
        def read(self, size=-1):
            reads.append(size)
            assert 0 < size <= 1024 * 1024
            return self.handle.read(size)

    def guarded_open(path, *args, **kwargs):
        handle = native_open(path, *args, **kwargs)
        if path == quarantine:
            opens.append((args, kwargs))
            assert args and args[0] == "rb"
            return Reader(handle)
        return handle

    monkeypatch.setattr(Path, "open", guarded_open)
    index, _ = gate._referenced_rekey_source_index(tmp_path)
    assert index[("nr", "ITEM001", "a" * 64)][0]["held_current_bgcs"] == ["current-old"]
    assert len(opens) == 1 and reads


def test_utf8_crlf_and_quoted_newline_preserve_raw_hash_and_values(tmp_path, monkeypatch):
    quarantine, _ = _toy_package(tmp_path, monkeypatch)
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(["source_file", "source_file_sha256", "resolved_bgc", "reason"])
    writer.writerow(["toy-input.csv", "a" * 64, "current-old", "TOY_é_HOLD\r\nsecond line"])
    _bind_payload(tmp_path, quarantine, buffer.getvalue().encode("utf-8"))
    before = _evidence(tmp_path)
    created = _track_spools(monkeypatch)
    index, _ = gate._referenced_rekey_source_index(tmp_path)
    result, = index[("nr", "ITEM001", "a" * 64)]
    assert result["source_hold_reasons"] == {"TOY_é_HOLD\r\nsecond line": 1}
    assert len(created) == 1 and created[0].closed
    assert _evidence(tmp_path) == before


def test_hash_mismatch_never_parses_and_closes_snapshot(tmp_path, monkeypatch):
    quarantine, original = _toy_package(tmp_path, monkeypatch)
    quarantine.write_bytes(original + b"\n")
    before = _evidence(tmp_path)
    created = _track_spools(monkeypatch)
    def forbidden_parser(*args, **kwargs):
        pytest.fail("unverified quarantine reached parser")
    monkeypatch.setattr(csv, "DictReader", forbidden_parser)
    with pytest.raises(gate.BlastpDiscoveryError, match="quarantine hash disagrees"):
        gate._referenced_rekey_source_index(tmp_path)
    assert len(created) == 1 and created[0].closed
    assert _evidence(tmp_path) == before


@pytest.mark.parametrize("fault", ["create", "write", "seek", "read1"])
def test_snapshot_io_failures_hold_and_preserve_evidence(tmp_path, monkeypatch, fault):
    _toy_package(tmp_path, monkeypatch)
    before = _evidence(tmp_path)
    created = _track_spools(monkeypatch, fault)
    with pytest.raises(gate.BlastpDiscoveryError, match="BLASTP_REKEY_RECEIPT_HOLD"):
        gate._referenced_rekey_source_index(tmp_path)
    assert len(created) == (0 if fault == "create" else 1)
    assert all(spool.closed for spool in created)
    assert _evidence(tmp_path) == before


def test_csv_failure_closes_snapshot_and_preserves_evidence(tmp_path, monkeypatch):
    _toy_package(tmp_path, monkeypatch)
    before = _evidence(tmp_path)
    created = _track_spools(monkeypatch)
    def broken_parser(*args, **kwargs):
        raise csv.Error("synthetic malformed CSV failure")
    monkeypatch.setattr(csv, "DictReader", broken_parser)
    with pytest.raises(gate.BlastpDiscoveryError, match="BLASTP_REKEY_RECEIPT_HOLD"):
        gate._referenced_rekey_source_index(tmp_path)
    assert len(created) == 1 and created[0].closed
    assert _evidence(tmp_path) == before


def test_invalid_utf8_preserves_existing_exception_and_closes_snapshot(tmp_path, monkeypatch):
    quarantine, _ = _toy_package(tmp_path, monkeypatch)
    _bind_payload(tmp_path, quarantine, b"source_file\n\xff\n")
    before = _evidence(tmp_path)
    created = _track_spools(monkeypatch)
    with pytest.raises(UnicodeDecodeError):
        gate._referenced_rekey_source_index(tmp_path)
    assert len(created) == 1 and created[0].closed
    assert _evidence(tmp_path) == before
