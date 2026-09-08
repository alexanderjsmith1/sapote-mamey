"""Exact-run transaction gate for the BiG-SCAPE pipeline driver."""
from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _load_pipeline():
    name = "bigscape_pipeline_run_id_under_test"
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / "bigscape_pipeline.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _write_runs(db: Path, run_ids) -> None:
    db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db) as connection:
        connection.execute("create table run (id integer primary key)")
        connection.executemany("insert into run (id) values (?)", [(value,) for value in run_ids])


def _argv(workdir: Path, *extra: str) -> list[str]:
    return [
        "--inputs", "synthetic.zip", "--pfam", "synthetic.hmm",
        "--workdir", str(workdir), "--skip-prep", *extra,
    ]


def _reader_calls(recorded):
    owners = (
        "bigscape_known_novel.py",
        "bigscape_cross_strain.py",
        "bigscape_ingest_to_mamey.py",
    )
    return [
        call for call in recorded
        if any(any(token.endswith(owner) for token in call) for owner in owners)
    ]


def _run_value(call):
    index = call.index("--run-id")
    return call[index + 1]


def test_all_three_downstream_calls_receive_one_identical_exact_run_id(tmp_path, monkeypatch):
    module = _load_pipeline()
    workdir = tmp_path / "run"
    _write_runs(workdir / "bigscape.db", [42])
    recorded = []
    monkeypatch.setattr(module, "run", lambda cmd, **kwargs: recorded.append([str(v) for v in cmd]))
    module.main(_argv(workdir, "--skip-cluster", "--run-id", "42", "--ingest-package", "pkg"))
    calls = _reader_calls(recorded)
    assert len(calls) == 3
    assert {_run_value(call) for call in calls} == {"42"}


def test_explicit_run_id_is_preserved_in_a_shared_multi_run_database(tmp_path, monkeypatch):
    module = _load_pipeline()
    workdir = tmp_path / "shared"
    _write_runs(workdir / "bigscape.db", [7, 42, 99])
    recorded = []
    monkeypatch.setattr(module, "run", lambda cmd, **kwargs: recorded.append([str(v) for v in cmd]))
    module.main(_argv(workdir, "--skip-cluster", "--run-id", "42"))
    calls = _reader_calls(recorded)
    assert len(calls) == 2
    assert {_run_value(call) for call in calls} == {"42"}


def test_skip_cluster_without_explicit_run_id_refuses_before_mutation(tmp_path):
    module = _load_pipeline()
    workdir = tmp_path / "must_not_exist"
    with pytest.raises(module.PipelineRunError) as caught:
        module.main(_argv(workdir, "--skip-cluster"))
    assert caught.value.code == "RUN_ID_REQUIRED_SKIP"
    assert not workdir.exists()


def test_preexisting_shared_or_chunked_database_without_explicit_run_id_refuses(tmp_path):
    module = _load_pipeline()
    workdir = tmp_path / "shared"
    db = workdir / "bigscape.db"
    _write_runs(db, [7, 42])
    before = db.read_bytes()
    with pytest.raises(module.PipelineRunError) as caught:
        module.main(_argv(workdir))
    assert caught.value.code == "RUN_ID_REQUIRED_PREEXISTING"
    assert db.read_bytes() == before
    assert not (workdir / "known_vs_novel.tsv").exists()
    assert not (workdir / "cross_strain_GCFs.tsv").exists()

    chunked = tmp_path / "chunked_must_not_exist"
    with pytest.raises(module.PipelineRunError) as second:
        module.main(_argv(chunked, "--chunk-mibig", "3", "--mibig-dir", "references"))
    assert second.value.code == "RUN_ID_REQUIRED_MULTICALL"
    assert not chunked.exists()


def test_one_proven_new_run_is_captured_and_propagated(tmp_path, monkeypatch):
    module = _load_pipeline()
    workdir = tmp_path / "fresh"
    recorded = []

    def fake_run(cmd, **kwargs):
        call = [str(value) for value in cmd]
        recorded.append(call)
        if "cluster" in call:
            _write_runs(workdir / "bigscape.db", [17])

    monkeypatch.setattr(module, "run", fake_run)
    module.main(_argv(workdir, "--ingest-package", "pkg"))
    calls = _reader_calls(recorded)
    assert len(calls) == 3
    assert {_run_value(call) for call in calls} == {"17"}


def test_zero_or_multiple_new_runs_refuse_before_downstream_outputs(tmp_path, monkeypatch):
    for label, created in (("zero", []), ("multiple", [3, 4])):
        module = _load_pipeline()
        workdir = tmp_path / label
        recorded = []

        def fake_run(cmd, **kwargs):
            call = [str(value) for value in cmd]
            recorded.append(call)
            if "cluster" in call:
                _write_runs(workdir / "bigscape.db", created)

        monkeypatch.setattr(module, "run", fake_run)
        with pytest.raises(module.PipelineRunError) as caught:
            module.main(_argv(workdir))
        assert caught.value.code == "RUN_DELTA_AMBIGUOUS"
        assert _reader_calls(recorded) == []
        assert not (workdir / "known_vs_novel.tsv").exists()
        assert not (workdir / "cross_strain_GCFs.tsv").exists()


def test_driver_has_no_order_based_or_workdir_based_run_inference():
    source = (ROOT / "tools" / "bigscape_pipeline.py").read_text(encoding="utf-8").lower()
    for forbidden in ("select max", "max(id)", "latest", "newest", "st_mtime", "order by"):
        assert forbidden not in source
    assert "created = after - before" in source


def test_malformed_resolution_is_typed_redacted_resource_clean_and_noncreating(
    tmp_path, monkeypatch, capsys
):
    module = _load_pipeline()
    workdir = tmp_path / "private-user-root" / "run"
    db = workdir / "bigscape.db"
    db.parent.mkdir(parents=True)
    db.write_text("not sqlite", encoding="utf-8")
    with pytest.raises(module.PipelineRunError) as caught:
        module.main(_argv(workdir, "--skip-cluster", "--run-id", "8"))
    assert caught.value.code == "RUN_DATABASE_INVALID"
    assert str(workdir) not in str(caught.value)
    assert not (workdir / "known_vs_novel.tsv").exists()

    assert module.cli(_argv(workdir, "--skip-cluster", "--run-id", "8")) == 2
    captured = capsys.readouterr()
    assert str(workdir) not in captured.out + captured.err

    valid_workdir = tmp_path / "valid_but_wrong_run"
    _write_runs(valid_workdir / "bigscape.db", [7])
    with pytest.raises(module.PipelineRunError) as absent:
        module.main(_argv(valid_workdir, "--skip-cluster", "--run-id", "8"))
    assert absent.value.code == "RUN_ID_NOT_PRESENT"
    assert not (valid_workdir / "known_vs_novel.tsv").exists()

    closed = {"value": False}

    class BrokenConnection:
        def execute(self, statement):
            raise sqlite3.DatabaseError("local secret must not escape")

        def close(self):
            closed["value"] = True

    monkeypatch.setattr(module.sqlite3, "connect", lambda *args, **kwargs: BrokenConnection())
    with pytest.raises(module.PipelineRunError) as second:
        module._snapshot_run_ids(db)
    assert second.value.code == "RUN_DATABASE_INVALID"
    assert "local secret" not in str(second.value)
    assert closed["value"] is True
