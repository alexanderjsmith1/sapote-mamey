"""A RID that NCBI no longer knows is resent in the same run, once.

Six tier-lane searches stranded across a stop came back RID UNKNOWN when their lanes restarted. The
runner marked them expired and left them until the next restart. They are now requeued in-run.
"""
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tools/blastp_crawl/nr_rid_runner.py"


def _load(monkeypatch, tmp_path):
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("RID_DATABASE", "nr_cluster_seq")
    monkeypatch.setenv("RID_QUERIES", "_QUERIES_T")
    monkeypatch.setenv("RID_BASE", "_LANE_T")
    spec = importlib.util.spec_from_file_location("rid_runner_465", SCRIPT)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def test_first_unknown_requeues_the_file(monkeypatch, tmp_path):
    m = _load(monkeypatch, tmp_path)
    faa = m.QUERIES / "AS-9001" / "p0001" / "q.faa"
    led = {"AS-9001/p0001/q.faa": {"status": "submitted", "note": ""}}
    todo, seen = [], set()
    assert m.requeue_unknown(led, "AS-9001/p0001/q.faa", faa, todo, seen) is True
    assert todo == [faa]
    assert led["AS-9001/p0001/q.faa"]["status"] == "expired"
    assert led["AS-9001/p0001/q.faa"]["note"] == "RID UNKNOWN, requeued"


def test_second_unknown_in_one_run_waits_for_a_later_run(monkeypatch, tmp_path):
    m = _load(monkeypatch, tmp_path)
    faa = m.QUERIES / "q.faa"
    led = {"q.faa": {"status": "submitted", "note": ""}}
    todo, seen = [], set()
    m.requeue_unknown(led, "q.faa", faa, todo, seen)
    led["q.faa"]["status"] = "submitted"
    assert m.requeue_unknown(led, "q.faa", faa, todo, seen) is False
    assert todo == [faa]
    assert led["q.faa"]["status"] == "expired" and led["q.faa"]["note"] == "RID UNKNOWN"


def test_expired_row_is_still_picked_up_by_a_later_run(monkeypatch, tmp_path):
    m = _load(monkeypatch, tmp_path)
    src = SCRIPT.read_text()
    todo_filter = src[src.index("    todo = [f for f in files"):].split("\n\n", 1)[0]
    assert '"expired"' not in todo_filter
