"""Deterministic stage-boundary races on two tiny files, with real watched no-op children.

Only environment admission is a bound synthetic fixture. Source/output hash and
stage receipts, process monitoring and command execution remain the real engine.
"""
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys

import pytest


@pytest.fixture
def engine(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]/'tools'))
    module=importlib.import_module('_release_workflow')
    support=module.support
    def admit(python,*,output,env,**kwargs):
        output.mkdir(parents=True);steps=[]
        for i in range(3):
            log=output/f'synthetic-admission-{i}.log';log.write_text('Synthetic admission only; actual watched child remains real.\n')
            steps.append({'log':str(log),'log_sha256':support.sha256_file(log),'exit_code':0,'stop_reason':None,'started_utc':support.utc_now(),'completed_utc':support.utc_now()})
        payload={'executable_sha256':support.sha256_file(Path(python)),'identity':{'fixture':'Q4'},'test_environment_sha256':hashlib.sha256(support.canonical_json(env)).hexdigest()}
        value=dict(payload,status='READY',resolved_executable=python,steps=steps,identity_sha256=hashlib.sha256(support.canonical_json(payload)).hexdigest())
        support.atomic_json(output/'environment.json',value);return value
    monkeypatch.setattr(support,'admit_environment',admit)
    return module


def setup(engine,tmp_path,*,progress=None,mutate=False):
    source=tmp_path/'source';source.mkdir();(source/'version.txt').write_text('before\n')
    registry=tmp_path/'explicit-metadata.tsv';registry.write_text('synthetic-metadata-before\n')
    command='from pathlib import Path;Path("version.txt").write_text("declared\\n")' if mutate else 'pass'
    stage=engine.Stage('gate',('{PYTHON}','-c',command),source_changes=('version.txt',) if mutate else ())
    workflow=engine.Workflow(source,tmp_path/'workflow',(stage,),sys.executable,
        inputs=({'path':str(registry),'sha256':engine.support.sha256_file(registry)},),
        env=dict(os.environ),min_disk=0,timeout=3,progress=progress)
    return workflow,source,registry


def test_source_change_between_digest_and_snapshot_cannot_be_committed(engine,monkeypatch,tmp_path):
    armed={'value':False};workflow,source,_=setup(engine,tmp_path,progress=lambda _:armed.update(value=True))
    digest=engine.partition.source_digest
    def racing(path):
        result=digest(path)
        if armed['value']:
            armed['value']=False;(source/'version.txt').write_text('concurrent-unapproved\n')
        return result
    monkeypatch.setattr(engine.partition,'source_digest',racing)
    with pytest.raises(ValueError,match='source changed while taking stage input snapshot'):
        workflow.run()
    record=json.loads((workflow.output/'workflow.json').read_text())
    assert record['status']=='FAILED'
    assert record['stages'][0]['attempts']==[]
    assert record['committed_source_sha256']!=digest(source)


def test_external_input_change_during_final_stage_cannot_pass(engine,monkeypatch,tmp_path):
    workflow,source,registry=setup(engine,tmp_path)
    real=engine.support.run_watched
    def change_after_child(*args,**kwargs):
        value=real(*args,**kwargs);registry.write_text('changed-during-stage\n');return value
    monkeypatch.setattr(engine.support,'run_watched',change_after_child)
    with pytest.raises(ValueError,match='external workflow input changed'):
        workflow.run()
    record=json.loads((workflow.output/'workflow.json').read_text())
    assert record['status']==record['stages'][0]['status']=='FAILED'
    assert 'state: FAILED' in (workflow.output/'STATUS.md').read_text()
    attempt=record['stages'][0]['attempts'][0]['receipt']['path']
    assert json.loads((workflow.output/attempt).read_text())['status']=='FAILED'


def test_stable_external_input_and_declared_source_change_still_pass(engine,tmp_path):
    workflow,source,registry=setup(engine,tmp_path,mutate=True)
    result=workflow.run()
    assert result['status']=='STAGES_COMPLETE'
    assert (source/'version.txt').read_text()=='declared\n'
    assert registry.read_text()=='synthetic-metadata-before\n'
