"""Fail-closed guidance before initial admission versus an already admitted resume."""
import json,os,sys
from pathlib import Path
import pytest
from tests.test_release_workflow_termination import engine,synthetic_admission

def refused(support):
    def admit(python,*,output,env,**kwargs):
        output.mkdir(parents=True)
        report={'status':'REFUSED','reason':'explicit synthetic unavailable prerequisite','steps':[]}
        support.atomic_json(output/'environment.json',report)
        return report
    return admit

def new_workflow(engine,tmp_path):
    source=tmp_path/'source';source.mkdir();(source/'input.txt').write_text('synthetic stable input\n')
    output=tmp_path/'workflow';plan=(engine.Stage('one',('{PYTHON}','-c','pass')),)
    return source,output,lambda:engine.Workflow(source,output,plan,sys.executable,env=dict(os.environ),min_disk=0,timeout=1)

def test_unadmitted_initial_root_names_fresh_output_and_never_retries_child(engine,tmp_path,monkeypatch):
    source,output,workflow=new_workflow(engine,tmp_path)
    monkeypatch.setattr(engine.support,'admit_environment',refused(engine.support))
    monkeypatch.setattr(engine.support,'run_watched',lambda *a,**k:pytest.fail('unadmitted stage executed'))
    with pytest.raises(ValueError,match='start a fresh workflow output'):workflow().run()
    before=(output/'workflow.json').read_bytes();record=json.loads(before)
    assert record['environment'] is None and record['stages'][0]['attempts']==[]
    assert 'state: REFUSED_ENVIRONMENT' in (output/'STATUS.md').read_text()
    monkeypatch.setattr(engine.support,'admit_environment',lambda *a,**k:pytest.fail('unadmitted root re-admitted on resume'))
    with pytest.raises(ValueError,match='initial environment was never admitted; preserve this root and start a fresh workflow output'):workflow().run(resume=True)
    assert any(p.read_bytes()==before for p in output.glob('refusals/*/workflow_before.json'))
    assert json.loads((output/'workflow.json').read_text())['status']=='REFUSED_RESUME'
    assert (source/'input.txt').read_text()=='synthetic stable input\n'

def test_prior_admission_survives_temporary_refusal_and_green_stage_is_not_repeated(engine,synthetic_admission,tmp_path,monkeypatch):
    source,output,workflow=new_workflow(engine,tmp_path);calls=[]
    def watch(argv,*,log,cwd,env,rss_limit,min_disk,timeout):
        calls.append(argv);log.write_text('explicit synthetic watch; no child executed\n')
        nice=engine.shutil.which('nice')
        return {'exit_code':0,'stop_reason':None,'argv':[nice,'-n','15',*argv] if nice else argv,
                'rss_stop_bytes':rss_limit,'minimum_free_disk_bytes':min_disk,'timeout_seconds':timeout,'peak_process_tree_rss':0}
    monkeypatch.setattr(engine.support,'run_watched',watch)
    assert workflow().run()['status']=='STAGES_COMPLETE'
    before=json.loads((output/'workflow.json').read_text());original=engine.support.admit_environment
    monkeypatch.setattr(engine.support,'admit_environment',refused(engine.support))
    with pytest.raises(ValueError,match='resume the original admitted workflow with unchanged bound inputs'):workflow().run(resume=True)
    refused_record=json.loads((output/'workflow.json').read_text())
    assert refused_record['environment']==before['environment']
    monkeypatch.setattr(engine.support,'admit_environment',original)
    after=workflow().run(resume=True)
    assert after['status']=='STAGES_COMPLETE' and len(calls)==1
    assert after['stages']==before['stages']
