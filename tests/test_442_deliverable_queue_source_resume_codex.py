"""A queue run must not certify failed steps or skip changed template sources."""

import json
from types import SimpleNamespace

from mamey import deliverable_queue as queue


def test_failed_cards_step_does_not_mark_strain_done(tmp_path, monkeypatch):
    runs = tmp_path / "runs"
    (runs / "SID001" / "package").mkdir(parents=True)
    monkeypatch.setattr(queue, "_auto_ingest", lambda *_: {})
    monkeypatch.setattr(queue._g, "gate", lambda *_: {"blocked": False, "missing": []})
    monkeypatch.setattr(queue, "_run", lambda argv, env=None:
                        (7, "fixture failure") if argv[0] == "emit-modeb-template" else (0, ""))

    rec = queue.process_strain("SID001", str(runs), str(tmp_path / "out"),
                               sources={"cohort_dir": str(tmp_path / "cohort")})

    assert rec["steps"]["cards"].startswith("rc7:")
    assert rec["status"] == "DETERMINISTIC_INCOMPLETE"
    assert rec["failed_steps"] == ["cards"]


def test_changed_source_flags_reprocess_completed_queue_record(tmp_path, monkeypatch):
    calls = []

    def fake_process(strain, runs_dir, out_root, activity_csv=None, sources=None):
        calls.append(dict(sources or {}))
        return {"strain": strain, "status": "DETERMINISTIC_DONE"}

    monkeypatch.setattr(queue, "process_strain", fake_process)
    out = tmp_path / "out"
    args = (["SID001"], str(tmp_path / "runs"), str(out))
    queue.run_queue(*args, sources={"cohort_dir": "first"})
    queue.run_queue(*args, sources={"cohort_dir": "first"})
    queue.run_queue(*args, sources={"cohort_dir": "second"})

    assert calls == [{"cohort_dir": "first"}, {"cohort_dir": "second"}]
    ledger = json.loads((out / "DELIVERABLE_QUEUE_LEDGER.json").read_text())
    assert ledger["SID001"]["status"] == "DETERMINISTIC_DONE"
    assert ledger["SID001"]["source_args_sha256"]


def test_cli_reports_incomplete_deterministic_steps(tmp_path, monkeypatch):
    monkeypatch.setattr(queue, "run_queue", lambda *a, **k: {"incomplete": 1})
    args = SimpleNamespace(strains=["SID001"], runs_dir=str(tmp_path / "runs"),
                           out_root=str(tmp_path / "out"))
    assert queue.deliverable_queue_command(args) == 1


def test_legacy_done_record_without_source_binding_reprocesses(tmp_path, monkeypatch):
    out = tmp_path / "out"
    out.mkdir()
    (out / "DELIVERABLE_QUEUE_LEDGER.json").write_text(
        json.dumps({"SID001": {"status": "DETERMINISTIC_DONE"}}))
    calls = []
    monkeypatch.setattr(queue, "process_strain", lambda *a, **k:
                        (calls.append(k["sources"]),
                         {"strain": "SID001", "status": "DETERMINISTIC_DONE"})[1])

    queue.run_queue(["SID001"], str(tmp_path / "runs"), str(out),
                    sources={"cohort_dir": "new-source"})

    assert calls == [{"cohort_dir": "new-source"}]


def test_summary_and_cli_ignore_unrequested_old_incomplete_record(tmp_path, monkeypatch):
    out = tmp_path / "out"
    out.mkdir()
    (out / "DELIVERABLE_QUEUE_LEDGER.json").write_text(json.dumps({
        "SID_OLD": {"status": "DETERMINISTIC_INCOMPLETE"}}))
    monkeypatch.setattr(queue, "process_strain", lambda *a, **k:
                        {"strain": "SID001", "status": "DETERMINISTIC_DONE"})

    summary = queue.run_queue(["SID001"], str(tmp_path / "runs"), str(out))

    assert summary["total"] == 1
    assert summary["deterministic_done"] == 1
    assert summary["incomplete"] == 0
