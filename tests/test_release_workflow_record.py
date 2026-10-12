"""Serial source-transform lineage, immutable outputs and generated status fixtures."""
from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
import shutil
import sys

import pytest


@pytest.fixture
def engine(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root / "tools"))
    return importlib.import_module("_release_workflow")


def setup(tmp_path):
    source = tmp_path / "source"; source.mkdir()
    (source / "version.txt").write_text("old\n")
    return source, tmp_path / "workflow", dict(os.environ)


def stages(engine):
    return (
        engine.Stage("prepare", ("{PYTHON}", "-c", '''from pathlib import Path
Path("version.txt").write_text("new\\n")
out=Path(r"{OUT}")/"prepare.txt"
out.write_text("one execution\\n")
'''), source_changes=("version.txt",), outputs=("prepare.txt",)),
        engine.Stage("gate", ("{PYTHON}", "-c", '''import os
from pathlib import Path
assert Path(os.environ["FIXTURE_READY"]).exists(), "fixture gate not ready"
out=Path(r"{OUT}")/"gate-output"
out.mkdir()
(out/"evidence.txt").write_text("gate passed\\n")
'''), output_trees=("gate-output",)),
    )


def workflow(engine, source, output, plan, env, **kwargs):
    return engine.Workflow(source, output, plan, str(Path(sys.executable).absolute()), env=env, **kwargs)


def test_transformed_source_resumes_at_failed_gate_without_repeating_prior_stage(engine, tmp_path):
    source, output, env = setup(tmp_path); marker = tmp_path / "ready"
    env["FIXTURE_READY"] = str(marker); plan = stages(engine)
    with pytest.raises(ValueError, match="stage failed"):
        workflow(engine, source, output, plan, env).run()
    original = json.loads((output / "workflow.json").read_text())
    assert original["status"] == "FAILED"
    assert original["stages"][0]["status"] == "PASS"
    assert (source / "version.txt").read_text() == "new\n"
    first = original["stages"][0]["active"]
    failed = original["stages"][1]["attempts"][0]["receipt"]
    failed_bytes = (output / failed["path"]).read_bytes()
    marker.write_text("ready")
    with pytest.raises(ValueError, match="requires a retry reason"):
        workflow(engine, source, output, plan, env).run(resume=True)
    result = workflow(engine, source, output, plan, env).run(resume=True,
        retry={"gate": "Synthetic fixture setup completed; retained failed gate evidence"})
    assert result["status"] == "STAGES_COMPLETE"
    assert result["stages"][0]["active"] == first
    assert len(result["stages"][0]["attempts"]) == 1
    assert len(result["stages"][1]["attempts"]) == 2
    assert (output / failed["path"]).read_bytes() == failed_bytes
    for name in ("STATUS.md", "00_START_HERE.md", "HANDOFF.md"):
        assert "state: STAGES_COMPLETE" in (output / name).read_text()
    moved = tmp_path / "moved workflow"; shutil.move(output, moved)
    again = workflow(engine, source, moved, plan, env).run(resume=True)
    assert again["status"] == "STAGES_COMPLETE"
    assert all(len(stage["attempts"]) == len(old["attempts"]) for stage, old in zip(again["stages"], result["stages"]))


def test_changed_output_or_child_log_refuses_reuse(engine, tmp_path):
    source, output, env = setup(tmp_path)
    plan = (engine.Stage("output", ("{PYTHON}", "-c", 'from pathlib import Path; p=Path(r"{OUT}")/"tree";p.mkdir();(p/"log").write_text("original")'), output_trees=("tree",)),)
    workflow(engine, source, output, plan, env).run()
    (output / "tree/log").write_text("tampered")
    with pytest.raises(ValueError, match="output inventory changed"):
        workflow(engine, source, output, plan, env).run(resume=True)
    data = json.loads((output / "workflow.json").read_text())
    assert data["status"] == "REFUSED_RESUME"
    assert data["resume_refusals"]
    assert "state: REFUSED_RESUME" in (output / "STATUS.md").read_text()
    assert list((output / "refusals").glob("*/workflow_before.json"))


def test_undeclared_source_mutation_fails_and_blocks_resume(engine, tmp_path):
    source, output, env = setup(tmp_path)
    plan = (engine.Stage("read-only", ("{PYTHON}", "-c", 'from pathlib import Path;Path("version.txt").write_text("unapproved")')),)
    with pytest.raises(ValueError, match="undeclared source mutation"):
        workflow(engine, source, output, plan, env).run()
    data = json.loads((output / "workflow.json").read_text())
    assert data["status"] == data["stages"][0]["status"] == "FAILED"
    with pytest.raises(ValueError, match="source differs"):
        workflow(engine, source, output, plan, env).run(resume=True, retry={"read-only": "cannot override source drift"})


def test_changed_plan_or_resource_policy_refuses_before_execution(engine, tmp_path):
    source, output, env = setup(tmp_path)
    plan = (engine.Stage("gate", ("{PYTHON}", "-c", "pass")),)
    workflow(engine, source, output, plan, env).run()
    with pytest.raises(ValueError, match="definition or schema changed"):
        workflow(engine, source, output, plan, env, timeout=30).run(resume=True)
    changed = (engine.Stage("gate", ("{PYTHON}", "-c", "raise AssertionError('must not execute')")),)
    with pytest.raises(ValueError, match="definition or schema changed"):
        workflow(engine, source, output, changed, env).run(resume=True)


def test_omitted_stage_cannot_be_reported_complete(engine, tmp_path):
    source, output, env = setup(tmp_path)
    plan = (engine.Stage("gate", ("{PYTHON}", "-c", "pass")),)
    workflow(engine, source, output, plan, env).run()
    path = output / "workflow.json"; data = json.loads(path.read_text()); data["stages"] = []
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="stage list is incomplete"):
        workflow(engine, source, output, plan, env).run(resume=True)


def test_changed_environment_cannot_reuse_green_stages(engine, tmp_path):
    source, output, env = setup(tmp_path)
    plan = (engine.Stage("gate", ("{PYTHON}", "-c", "pass")),)
    workflow(engine, source, output, plan, env).run()
    env["A_CHANGED_FIXTURE_VARIABLE"] = "new binding"
    with pytest.raises(ValueError, match="environment changed"):
        workflow(engine, source, output, plan, env).run(resume=True)


@pytest.mark.parametrize("relative", ["../escape", "/absolute", "workflow.json", "attempts/collision"])
def test_unsafe_or_reserved_output_paths_refuse(engine, tmp_path, relative):
    source, output, env = setup(tmp_path)
    with pytest.raises(ValueError):
        workflow(engine, source, output, (engine.Stage("bad", ("{PYTHON}", "-c", "pass"), outputs=(relative,)),), env)


def test_environment_refusal_has_an_authoritative_non_green_root(engine, tmp_path):
    source, output, env = setup(tmp_path)
    env['PYTEST_ADDOPTS'] = '-k easy_only'
    plan = (engine.Stage('never-run', ('{PYTHON}', '-c', 'raise AssertionError("must not execute")')),)
    with pytest.raises(ValueError, match='environment refused'):
        workflow(engine, source, output, plan, env, context={'owner_gate':'PENDING'}).run()
    data = json.loads((output/'workflow.json').read_text())
    assert data['status'] == 'REFUSED_ENVIRONMENT'
    assert data['stages'][0]['attempts'] == []
    assert data['context']['owner_gate'] == 'PENDING'
    assert 'state: REFUSED_ENVIRONMENT' in (output/'STATUS.md').read_text()


def test_independent_root_verification_is_read_only_and_keeps_owner_hold(engine, tmp_path):
    source, output, env = setup(tmp_path)
    plan = (engine.Stage('one', ('{PYTHON}', '-c', 'pass')),)
    instance = workflow(engine, source, output, plan, env, context={'owner_gate':'PENDING'})
    instance.run()
    before = (output/'workflow.json').read_bytes()
    result = workflow(engine, source, output, plan, env, context={'owner_gate':'PENDING'}).verify(
        engine.support.sha256_file(output/'workflow.json'), tmp_path/'verification')
    assert result['status'] == 'VERIFIED_STAGES' and result['owner_adoption'] == 'NOT_AUTHORIZED'
    assert (output/'workflow.json').read_bytes() == before
    assert (tmp_path/'verification/workflow-verification.json').is_file()
    with pytest.raises(ValueError, match='root SHA-256 mismatch'):
        workflow(engine, source, output, plan, env, context={'owner_gate':'PENDING'}).verify('0'*64, tmp_path/'bad-verification')
    assert not (tmp_path/'bad-verification').exists()


def test_context_drift_is_refused_and_visible(engine, tmp_path):
    source, output, env = setup(tmp_path)
    plan = (engine.Stage('one', ('{PYTHON}', '-c', 'pass')),)
    instance = workflow(engine, source, output, plan, env, context={'owner_gate':'PENDING'})
    instance.run()
    record = json.loads((output/'workflow.json').read_text())
    record['context']['owner_gate'] = 'IMPLIED_APPROVAL'
    engine.support.atomic_json(output/'workflow.json', record)
    with pytest.raises(ValueError, match='context changed'):
        workflow(engine, source, output, plan, env, context={'owner_gate':'PENDING'}).run(resume=True)
    assert json.loads((output/'workflow.json').read_text())['status'] == 'REFUSED_RESUME'


def test_stage_events_precede_execution_and_return_the_bound_record(engine, tmp_path):
    source, output, env = setup(tmp_path)
    plan = tuple(engine.Stage(name, ('{PYTHON}', '-c',
        f'from pathlib import Path;Path(r"{{OUT}}/{name}").write_text("done")'), outputs=(name,))
        for name in ('one','two'))
    events = workflow(engine,source,output,plan,env).iter_run()
    assert next(events) == 'Release stage: one'
    assert not (output/'one').exists()
    assert next(events) == 'Release stage: two'
    assert (output/'one').read_text() == 'done' and not (output/'two').exists()
    with pytest.raises(StopIteration) as completed:
        next(events)
    assert completed.value.value['status'] == 'STAGES_COMPLETE'
    assert (output/'two').read_text() == 'done'
    assert json.loads((output/'workflow.json').read_text())['status'] == 'STAGES_COMPLETE'


def test_closing_stage_events_records_failure_and_releases_lock(engine, tmp_path):
    source, output, env = setup(tmp_path)
    plan = (engine.Stage('never-executed', ('{PYTHON}', '-c', 'raise AssertionError("must not run")')),)
    events = workflow(engine,source,output,plan,env).iter_run()
    assert next(events) == 'Release stage: never-executed'
    events.close()
    record = json.loads((output/'workflow.json').read_text())
    assert record['status'] == 'FAILED' and record['stages'][0]['attempts'] == []
    with engine.partition.exclusive(output):
        assert record['committed_source_sha256'] == engine.partition.source_digest(source)
