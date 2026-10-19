"""Synthetic pre-commit interruption and recovery-containment regressions."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from mamey import bank_transaction as bank
from mamey import output_transaction as output


@pytest.mark.parametrize("fault_type", [KeyboardInterrupt, SystemExit])
def test_fresh_set_interrupt_rolls_back_and_can_retry(tmp_path, monkeypatch, fault_type):
    root = tmp_path / "outputs"
    original = output.os.link
    fault = fault_type("synthetic interruption")

    def interrupted(source, target):
        if Path(target).name == "second.txt":
            raise fault
        return original(source, target)

    with monkeypatch.context() as patch:
        patch.setattr(output.os, "link", interrupted)
        with pytest.raises(fault_type) as caught:
            with output.fresh_output_set(root, ["nested/first.txt", "nested/second.txt"]) as stage:
                (stage / "nested").mkdir()
                (stage / "nested/first.txt").write_bytes(b"first")
                (stage / "nested/second.txt").write_bytes(b"second")
    assert caught.value is fault
    assert not root.exists()
    assert not list(tmp_path.glob(".mamey-output-*"))
    with output.fresh_output_set(root, ["nested/first.txt", "nested/second.txt"]) as stage:
        (stage / "nested").mkdir()
        (stage / "nested/first.txt").write_bytes(b"first")
        (stage / "nested/second.txt").write_bytes(b"second")
    assert (root / "nested/second.txt").read_bytes() == b"second"


@pytest.mark.parametrize("fault_type", [KeyboardInterrupt, SystemExit])
@pytest.mark.parametrize("existing_report", [False, True])
def test_payload_interrupt_preserves_old_report_and_allows_retry(
    tmp_path, monkeypatch, fault_type, existing_report
):
    first, second, report = (tmp_path / name for name in ("first", "second", "report"))
    if existing_report:
        report.write_bytes(b"previous report")
    original = output.os.fsync
    calls = 0
    fault = fault_type("synthetic flush interruption")

    def interrupted(fd):
        nonlocal calls
        calls += 1
        # Existing replacement is staged first; interrupt the second fresh payload.
        if calls == (3 if existing_report else 2):
            raise fault
        return original(fd)

    with monkeypatch.context() as patch:
        patch.setattr(output.os, "fsync", interrupted)
        with pytest.raises(fault_type) as caught:
            output.publish_payloads({first: b"first", second: b"second"}, replacement=(report, b"new"))
    assert caught.value is fault
    assert not first.exists() and not second.exists()
    assert not list(tmp_path.glob(".mamey-report-*"))
    assert report.read_bytes() == b"previous report" if existing_report else not report.exists()
    output.publish_payloads({first: b"first", second: b"second"}, replacement=(report, b"new"))
    assert report.read_bytes() == b"new"


def _snapshot(root):
    return {name: (root / name).read_bytes() if (root / name).is_file() else None
            for name in bank.STORES + (bank.STATE,)}


def _interrupted_bank(tmp_path, monkeypatch):
    root = tmp_path / "bank"
    def build(label):
        def stage(directory):
            (directory / "bgc_data.json").write_text(json.dumps({"strains": {label: {}}, "bgcs": []}))
            (directory / "gene_data.json").write_text(json.dumps({"scan_agg": {}, "tfbs": {label: {}}}))
        return stage
    with bank.lock(root, writer=True):
        bank.prepare(root, build("before"))
    before = _snapshot(root)
    def fault(boundary):
        if boundary == "published:bgc_data.json":
            raise KeyboardInterrupt("synthetic pending transaction")
    with monkeypatch.context() as patch:
        patch.setattr(bank, "_boundary", fault)
        with bank.lock(root, writer=True), pytest.raises(KeyboardInterrupt):
            bank.prepare(root, build("after"))
    return root, before


@pytest.mark.parametrize("mode", ["finish", "rollback"])
def test_recovery_preflights_state_destination_before_any_store_write(tmp_path, monkeypatch, mode):
    root, before = _interrupted_bank(tmp_path, monkeypatch)
    (root / bank.STATE).unlink()
    (root / bank.STATE).mkdir()
    pending = (root / bank.PENDING).read_bytes()
    snapshot = _snapshot(root)
    with pytest.raises(bank.BankError, match="DESTINATION_NOT_REGULAR"):
        bank.recover(root, mode)
    assert _snapshot(root) == snapshot
    assert (root / bank.PENDING).read_bytes() == pending
    # Repair only the injected damage, then recover using the preserved journal.
    (root / bank.STATE).rmdir()
    (root / bank.STATE).write_bytes(before[bank.STATE])
    bank.recover(root, mode)
    bank.coherent(root)
    if mode == "rollback":
        assert _snapshot(root) == before


@pytest.mark.parametrize("mode", ["rollback", "finish"])
def test_abrupt_process_exit_leaves_reader_hold_and_recoverable_journal(tmp_path, mode):
    """Exit without finally blocks, then recover from the persistent before/after images."""
    root = tmp_path / "abrupt-bank"
    script = r'''
import importlib.util, json, os, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location("crash_bank", sys.argv[1])
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
root = Path(sys.argv[2])
def builder(label):
    def build(stage):
        (stage / "bgc_data.json").write_text(json.dumps({"strains": {label: {}}, "bgcs": []}))
        (stage / "gene_data.json").write_text(json.dumps({"scan_agg": {}, "tfbs": {label: {}}}))
    return build
with b.lock(root, writer=True):
    b.prepare(root, builder("before"))
    def crash(boundary):
        if boundary == "published:bgc_data.json": os._exit(73)
    b._boundary = crash
    b.prepare(root, builder("after"))
'''
    result = subprocess.run(
        [sys.executable, "-B", "-c", script, str(Path(bank.__file__).resolve()), str(root)],
        capture_output=True, text=True, timeout=10,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    assert result.returncode == 73, result.stderr
    with pytest.raises(bank.BankError, match="RECOVERY_REQUIRED"):
        with bank.reader(root):
            pass
    bank.recover(root, mode)
    bank.coherent(root)
    expected = "before" if mode == "rollback" else "after"
    assert set(json.loads((root / "bgc_data.json").read_text())["strains"]) == {expected}


@pytest.mark.parametrize("mode,phase", [("rollback", "before"), ("finish", "after")])
def test_recovery_refuses_symlinked_image_directory_without_writes(tmp_path, monkeypatch, mode, phase):
    root, _ = _interrupted_bank(tmp_path, monkeypatch)
    journal = json.loads((root / bank.PENDING).read_text())
    tx = root / ".ingest_transactions" / journal["transaction"]
    displaced = tmp_path / "displaced-image"
    (tx / phase).rename(displaced)
    (tx / phase).symlink_to(displaced, target_is_directory=True)
    snapshot = _snapshot(root)
    with pytest.raises(bank.BankError, match="RECOVERY_PATH_INVALID"):
        bank.recover(root, mode)
    assert _snapshot(root) == snapshot
    assert (root / bank.PENDING).is_file()
    (tx / phase).unlink()
    displaced.rename(tx / phase)
    bank.recover(root, mode)
    bank.coherent(root)
