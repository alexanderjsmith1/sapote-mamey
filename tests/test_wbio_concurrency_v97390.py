"""v9.7.390 regression coverage for collision-safe atomic output transactions."""
from __future__ import annotations

import pathlib
import sys
import threading

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
import _wbio


def _temps(directory: pathlib.Path) -> list[pathlib.Path]:
    return sorted(directory.glob(".*.tmp"))


def test_atomic_save_uses_a_unique_sibling_temp(tmp_path):
    target = tmp_path / "deliverable.xlsx"
    destinations = []

    class FakeWorkbook:
        def save(self, destination):
            destination = pathlib.Path(destination)
            destinations.append(destination)
            destination.write_bytes(b"complete")

    _wbio.atomic_save(FakeWorkbook(), target)

    assert target.read_bytes() == b"complete"
    assert destinations[0].parent == target.parent
    assert destinations[0] != pathlib.Path(str(target) + ".tmp")
    assert destinations[0].name.startswith(f".{target.name}.")
    assert not _temps(tmp_path)


def test_concurrent_text_writers_never_share_or_publish_partial_bytes(tmp_path):
    target = tmp_path / "cohort.tsv"
    payloads = [(f"writer-{i}\n" * 2000) for i in range(8)]
    barrier = threading.Barrier(len(payloads))
    errors = []

    def write(payload):
        try:
            barrier.wait(timeout=5)
            _wbio.atomic_write_text(target, payload)
        except BaseException as exc:  # captured so the main test can report it
            errors.append(exc)

    threads = [threading.Thread(target=write, args=(payload,)) for payload in payloads]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert not errors
    assert target.read_text() in payloads
    assert not _temps(tmp_path)


def test_failed_backup_refresh_keeps_the_previous_backup(tmp_path, monkeypatch):
    target = tmp_path / "private.xlsx"
    backup = tmp_path / "private.xlsx.bak"
    target.write_bytes(b"old-current")
    backup.write_bytes(b"older-known-good")

    class FakeWorkbook:
        def save(self, destination):
            pathlib.Path(destination).write_bytes(b"new-current")

    def fail_after_partial_copy(_source, destination):
        pathlib.Path(destination).write_bytes(b"partial-backup")
        raise OSError("simulated backup interruption")

    monkeypatch.setattr(_wbio.shutil, "copy2", fail_after_partial_copy)
    with pytest.warns(UserWarning, match="could not create .bak"):
        _wbio.atomic_save(FakeWorkbook(), target, keep_bak=True)

    assert target.read_bytes() == b"new-current"
    assert backup.read_bytes() == b"older-known-good"
    assert not _temps(tmp_path)


def test_failed_commit_discards_private_temp_and_preserves_original(tmp_path, monkeypatch):
    target = tmp_path / "result.md"
    target.write_text("original")

    def fail_replace(_source, _destination):
        raise OSError("simulated rename failure")

    monkeypatch.setattr(_wbio.os, "replace", fail_replace)
    with pytest.raises(OSError, match="rename failure"):
        _wbio.atomic_write_text(target, "replacement")

    assert target.read_text() == "original"
    assert not _temps(tmp_path)
