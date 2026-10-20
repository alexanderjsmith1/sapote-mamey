"""v9.7.454: a DONE strain is skipped only while its package bytes, delivered outputs and run context match.

Before, the queue skipped on a hash of the source-argument strings alone, so new input bytes at the same path,
a deleted output or a different activity table still looked done.
"""
import json
from pathlib import Path

import pytest

from mamey import deliverable_queue as queue


@pytest.fixture
def setup(tmp_path, monkeypatch):
    runs, out = tmp_path / "runs", tmp_path / "out"
    pkg = runs / "SID001" / "package"; pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text('{"strain_id": "SID001"}')
    activity = tmp_path / "activity.csv"; activity.write_text("strain,activity\nSID001,+\n")
    calls = []

    def fake_process(strain, runs_dir, out_root, activity_csv=None, sources=None):
        calls.append(strain)
        d = Path(out_root) / strain / "sapote"; d.mkdir(parents=True, exist_ok=True)
        (d / f"{strain}_compiled_report.md").write_text(f"report {len(calls)}\n")
        return {"strain": strain, "status": "DETERMINISTIC_DONE"}

    monkeypatch.setattr(queue, "process_strain", fake_process)
    run = lambda: queue.run_queue(["SID001"], str(runs), str(out), activity_csv=str(activity))
    return run, calls, pkg, out, activity


def test_unchanged_strain_is_skipped(setup):
    run, calls, *_ = setup
    run(); run()
    assert calls == ["SID001"]


def test_changed_package_bytes_at_the_same_path_rerun(setup):
    run, calls, pkg, *_ = setup
    run(); (pkg / "manifest.json").write_text('{"strain_id": "SID001", "rerun": true}'); run()
    assert calls == ["SID001", "SID001"]


def test_deleted_output_reruns(setup):
    run, calls, pkg, out, _ = setup
    run(); (out / "SID001" / "sapote" / "SID001_compiled_report.md").unlink(); run()
    assert calls == ["SID001", "SID001"]


def test_changed_activity_table_reruns(setup):
    run, calls, pkg, out, activity = setup
    run(); activity.write_text("strain,activity\nSID001,-\n"); run()
    assert calls == ["SID001", "SID001"]


def test_legacy_done_record_without_bindings_reruns(setup):
    run, calls, pkg, out, _ = setup
    run()
    ledger_path = out / "DELIVERABLE_QUEUE_LEDGER.json"
    ledger = json.loads(ledger_path.read_text())
    for key in ("package_sha256", "outputs_sha256", "context_sha256"):
        ledger["SID001"].pop(key)
    ledger_path.write_text(json.dumps(ledger))
    run()
    assert calls == ["SID001", "SID001"]
