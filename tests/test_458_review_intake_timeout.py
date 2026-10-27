from pathlib import Path
from types import SimpleNamespace
import csv,importlib.util,json,subprocess,sys
import pytest
ROOT=Path(__file__).resolve().parents[1]

def load():
    spec=importlib.util.spec_from_file_location('timeout_harness',ROOT/'tools/intake_harness.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def command(tmp_path,extra=()):
    inputs=[]
    for name in ['first','second']:
        p=tmp_path/(name+'.zip');p.write_bytes(b'synthetic archive binding only');inputs.append(str(p))
    out=tmp_path/'out'
    return ['intake_harness','--inputs',*inputs,'--outdir',str(out),
            '--registry',str(out/'registry.csv'),'--metrics',str(out/'metrics.csv'),*extra]

@pytest.mark.parametrize('timeout',[None,12.5])
def test_optional_timeout_forwards_and_failed_input_does_not_end_batch(tmp_path,monkeypatch,capsys,timeout):
    m=load();extra=[] if timeout is None else ['--per-input-timeout',str(timeout)]
    monkeypatch.setattr(sys,'argv',command(tmp_path,extra))
    monkeypatch.setattr(m,'_engine_binding',lambda:{'code':'synthetic'})
    monkeypatch.setattr(m,'detect_and_stage',lambda zp,*a:('ANTISMASH',str(zp),None,'synthetic taxonomy'))
    calls=[]
    def monitor(cmd,**kwargs):
        calls.append(kwargs)
        if timeout is not None and len(calls)==1:
            raise subprocess.TimeoutExpired(cmd,timeout,output='saved synthetic child diagnostics')
        return 1,0.1,0,'synthetic controlled failure'
    monkeypatch.setattr(m,'run_monitored',monitor)
    assert m.main()==1
    assert len(calls)==2
    if timeout is None:assert all('timeout' not in c for c in calls)
    else:
        assert all(c['timeout']==timeout for c in calls)
        assert 'INPUT_TIMEOUT' in capsys.readouterr().err
    with (tmp_path/'out/metrics.csv').open() as stream:rows=list(csv.DictReader(stream))
    assert [r['status'] for r in rows]==['RUN_FAILED','RUN_FAILED']
    if timeout is not None:assert rows[0]['engine_peak_mb']==''
    assert not list((tmp_path/'out').rglob('intake_completion_receipt.json'))

@pytest.mark.parametrize('value',['0','-1','nan','inf'])
def test_invalid_timeout_refuses_before_output(tmp_path,monkeypatch,value):
    m=load();monkeypatch.setattr(sys,'argv',command(tmp_path,['--per-input-timeout',value]))
    with pytest.raises(SystemExit) as e:m.main()
    assert e.value.code==2 and not (tmp_path/'out').exists()

def test_captured_policy_cannot_silently_ignore_staged_timeout(tmp_path,monkeypatch,capsys):
    m=load();monkeypatch.setattr(sys,'argv',command(tmp_path,['--per-input-timeout','1','--capture-policy','synthetic.json']))
    with pytest.raises(SystemExit) as e:m.main()
    assert e.value.code==2 and not (tmp_path/'out').exists()
    assert 'staged intake' in capsys.readouterr().err

def binding_fixture(tmp_path,timeout):
    m=load();source=tmp_path/'input.zip';source.write_bytes(b'synthetic')
    args=SimpleNamespace(mode='gold',source='synthetic',release='PRIVATE',taxonomy_map=None,
                         outdir=str(tmp_path/'out'),per_input_timeout=timeout)
    return m,source,args

def test_changed_explicit_timeout_invalidates_resume(tmp_path):
    m,source,args=binding_fixture(tmp_path,9.0);binding=m._run_binding(source,'SYNTHETIC',args,{'code':'synthetic'})
    package=tmp_path/'package';package.mkdir();receipt=tmp_path/'receipt.json'
    receipt.write_text(json.dumps({'schema':1,'status':'OK','run':binding,'output':m._tree_binding(package)}))
    assert m._resume_verified(receipt,binding,package)
    args.per_input_timeout=10.0
    assert not m._resume_verified(receipt,m._run_binding(source,'SYNTHETIC',args,{'code':'synthetic'}),package)

def test_default_binding_preserves_prior_option_shape(tmp_path):
    m,source,args=binding_fixture(tmp_path,None)
    assert set(m._run_binding(source,'SYNTHETIC',args,{})['options'])=={'mode','source','release','taxonomy_map','brief','json_evidence'}
