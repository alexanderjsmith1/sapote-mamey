"""Actual parsers/functions with intercepted owners; no cut, suite, import audit or ZIP."""
import argparse,ast,json,os,shutil,stat,subprocess,sys,uuid,zipfile
from pathlib import Path
from types import SimpleNamespace as NS
import pytest

ROOT=Path(__file__).resolve().parents[1]

def need(ok,message):
    if not ok:raise ValueError(message)

def load_api():
    text=(ROOT/'tools/release_workflow.py').read_text();tree=ast.parse(text)
    names={'registry_options','registry_context','registry_inputs','cut_context','plan','parse_args',
           'run_partitions','verified_final','run_import_stage','verify_current_imports','artifact_stage','execute_step','command_events','workflow_environment'}
    support=NS(ValidationRefused=ValueError,sha256_file=lambda _: 'a'*64,atomic_json=lambda *a:None,resolve_interpreter=lambda p:Path(p))
    ns=dict(argparse=argparse,ast=ast,json=json,os=os,Path=Path,sys=sys,uuid=uuid,zipfile=zipfile,
        shutil=shutil,stat=stat,hashlib=__import__('hashlib'),re=__import__('re'),subprocess=subprocess,
        support=support,contract=NS(require=need),partitions=NS(),imports=NS(),
        RegistryRefused=type('RegistryRefused',(ValueError,),{}),Outcome=lambda text,code=0,stderr=False:NS(text=text,code=code,stderr=stderr),
        Stage=lambda name,argv,**kw:NS(name=name,argv=argv,**kw),preparation_outputs=lambda _:('fixture',))
    # Use the genuine declared states without importing audit/production machinery.
    readiness_tree=ast.parse((ROOT/'tools/_release_import_worker.py').read_text())
    readiness=next(n for n in readiness_tree.body if isinstance(n,ast.Assign)
                   and any(getattr(t,'id','')=='IMPORT_READY_STATES' for t in n.targets))
    readiness_ns={}
    exec(compile(ast.Module(body=[readiness],type_ignores=[]),'actual-import-ready-states','exec'),readiness_ns)
    ns['imports'].IMPORT_READY_STATES=readiness_ns['IMPORT_READY_STATES']
    for n in tree.body:
        if isinstance(n,ast.Assign) and any(getattr(t,'id','') in {'INTEGRITY_FILES','GENERATED_FILES'} for t in n.targets):exec(compile(ast.Module(body=[n],type_ignores=[]),'constants','exec'),ns)
        if isinstance(n,ast.FunctionDef) and n.name in names:exec(compile(ast.Module(body=[n],type_ignores=[]),'actual-workflow','exec'),ns)
    retry_tree=ast.parse((ROOT/'tools/release_validate.py').read_text())
    retry=next(n for n in retry_tree.body if getattr(n,'name','')=='retries')
    ns['ValidationRefused']=ValueError
    exec(compile(ast.Module(body=[retry],type_ignores=[]),'actual-retry-parser','exec'),ns)
    return ns

def shell_fixture(tmp_path,*,resume=False,phase=''):
    source=tmp_path/'source with spaces';(source/'tools').mkdir(parents=True)
    text=(ROOT/'tools/release_workflow.py').read_text();tree=ast.parse(text)
    parser=ast.get_source_segment(text,next(n for n in tree.body if getattr(n,'name','')=='parse_args'))
    capture=tmp_path/'capture.jsonl'
    stub='import argparse,json,os,sys\nfrom pathlib import Path\n'+parser+'''\na=parse_args()
with open(os.environ['CAPTURE'],'a') as out:out.write(json.dumps(dict(argv=sys.argv[1:],args=vars(a),cwd=os.getcwd(),python_env=os.environ.get('PYTHON'),resume_env=os.environ.get('RELEASE_WORKFLOW_RESUME'),retry_env=os.environ.get('RELEASE_WORKFLOW_RETRY')),default=str)+'\\n')
'''
    (source/'tools/release_workflow.py').write_text(stub)
    wrapper=tmp_path/'python shim';wrapper.write_text('#!'+sys.executable+'\nimport os,sys\nos.execv('+repr(sys.executable)+',['+repr(sys.executable)+',*sys.argv[1:]])\n');wrapper.chmod(0o755)
    output=tmp_path/'relative output'
    if resume:output.mkdir();(output/'prior').write_bytes(b'preserve')
    flags=['--synthetic-registry',str(tmp_path/'explicit.tsv'),'--synthetic-registry-sha256','1'*64,'--synthetic-guard-sha256','2'*64,'--synthetic-allowlist-sha256','3'*64]
    env=dict(os.environ,PYTHON=str(wrapper),CAPTURE=str(capture),RELEASE_PYTEST_MODE='partitioned',RELEASE_WORKFLOW_PHASE=phase,RELEASE_DATE='20261017',RELEASE_PARTITION_FILES='7',PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(tmp_path))
    env.pop('PYTEST_ADDOPTS',None)
    if resume:env.update(RELEASE_WORKFLOW_RESUME='1',RELEASE_WORKFLOW_RETRY='final=external prerequisite repaired')
    else:env.pop('RELEASE_WORKFLOW_RESUME',None);env.pop('RELEASE_WORKFLOW_RETRY',None)
    args=['9.7.452',str(source),'relative output','b',*flags]
    return source,output,wrapper,capture,flags,env,args

@pytest.mark.parametrize('resume',[False,True])
def test_outer_cut_forwards_original_locator_paths_registry_and_retry(tmp_path,resume):
    source,out,wrapper,capture,flags,env,args=shell_fixture(tmp_path,resume=resume)
    run=subprocess.run(['bash',str(ROOT/'tools/release_cut.sh'),*args],cwd=tmp_path,env=env,capture_output=True,text=True,timeout=5)
    assert run.returncode==0,run.stdout+run.stderr
    row=json.loads(capture.read_text());a=row['args']
    assert a['python']==str(wrapper) and row['python_env']==str(wrapper)
    assert a['source']==str(source) and a['out']==str(out)
    assert a['date']=='20261017' and a['letter']=='b' and a['files_per_partition']==7
    assert a['resume']==resume
    assert a['retry']==(['final=external prerequisite repaired'] if resume else [])
    assert row['resume_env'] is None and row['retry_env'] is None
    for flag,value in zip(flags[::2],flags[1::2]):assert a[flag[2:].replace('-','_')]==value
    if resume:assert (out/'prior').read_bytes()==b'preserve'
    else:assert not out.exists()

def test_shell_registry_boundary_keeps_original_locator(tmp_path):
    source,out,wrapper,capture,flags,env,args=shell_fixture(tmp_path,phase='prepare')
    text=(ROOT/'tools/release_cut.sh').read_text();prefix=text.split('\nsource "$SRC/tools/cut_preflight.sh"',1)[0]
    func='registry_preflight(){'+text.split('\nregistry_preflight(){',1)[1].split('\n}\n',1)[0]+'\n}\n'
    run=subprocess.run(['bash','-s','--',*args],input=prefix+'\n'+func+'\nregistry_preflight\n',cwd=tmp_path,env=env,capture_output=True,text=True,timeout=5)
    assert run.returncode==0,run.stderr
    assert json.loads(capture.read_text())['args']['python']==str(wrapper)

@pytest.mark.parametrize('phase,owner',[('prepare','prepare_release'),('integrity','refresh_source_integrity'),('post-gates','post_test_gates'),('package','build_tiers')])
def test_internal_phase_owner_dispatch_is_preserved(tmp_path,phase,owner):
    source,out,wrapper,capture,flags,env,args=shell_fixture(tmp_path,phase=phase)
    text=(ROOT/'tools/release_cut.sh').read_text();prefix=text.split('\nsource "$SRC/tools/cut_preflight.sh"',1)[0]
    tail=text[text.rindex('if [[ -n "$PHASE" ]]; then'):]
    stubs='\n'+''.join(f'{n}(){{ printf "OWNER={n}\\n"; }};\n' for n in ['prepare_release','refresh_source_integrity','post_test_gates','build_tiers'])
    run=subprocess.run(['bash','-s','--',*args],input=prefix+stubs+tail,cwd=tmp_path,env=env,capture_output=True,text=True,timeout=5)
    assert run.returncode==0 and ('OWNER='+owner) in run.stdout
    assert run.stdout.count('OWNER=')==1 and not capture.exists()

def test_plan_carries_locator_into_every_internal_python_consumer(tmp_path):
    api=load_api();selected=dict(registry_path='/explicit',registry_sha256='1'*64,guard_sha256='2'*64,allowlist_sha256='3'*64)
    stages=api['plan'](tmp_path,'9.7.452','20261017','b',7,selected)
    for stage in stages:
        if stage.argv[0]=='{PYTHON}':
            assert stage.argv[stage.argv.index('--python')+1]=='{PYTHON}'
        else:
            assert 'CUT_TIERS=code' in stage.argv
        assert '--synthetic-registry' in stage.argv

def test_step_parser_accepts_explicit_locator(tmp_path):
    api=load_api();a=api['parse_args'](['_step','--step','baseline','--source',str(tmp_path),'--out',str(tmp_path/'out'),'--python','/chosen'])
    assert a.python=='/chosen'

def exhaust(generator):
    while True:
        try:next(generator)
        except StopIteration as done:return done.value

@pytest.mark.parametrize('resume',[False,True])
def test_partition_consumer_and_retry_owner_preserve_locator(tmp_path,resume):
    api=load_api();calls=[];out=tmp_path/'partitions'
    if resume:
        out.mkdir();(out/'partition.json').write_text(json.dumps({'collection':{'status':'PASS'},'partitions':[{'status':'FAILED','plan':{'id':'part-1'}}]}))
    class Runner:
        def __init__(self,*a,**k):calls.append(('init',a,k))
        def run(self,**k):calls.append(('run',k));return {'status':'PASS'}
    api['partitions'].PartitionRunner=Runner
    exhaust(api['run_partitions'](tmp_path,out,7,python='/chosen',reason='explicit repair' if resume else None))
    assert calls[0][1][2]=='/chosen'
    assert calls[1][1]==dict(resume=resume,retry={'part-1':'explicit repair'} if resume else {})

def test_verifier_and_import_audit_consume_explicit_locator(tmp_path):
    api=load_api();seen=[]
    api['partitions'].verified_counts=lambda *a,**k:seen.append(('verify',k['python']))
    api['verified_final'](tmp_path,tmp_path,tmp_path/'admission',python='/chosen')
    api['workflow_environment']=lambda python,source:{'PYTHON':python}
    api['imports'].run_import_smoke=lambda source,out,python,**kw:(seen.append(('imports',python)) or {'status':'PASS','environment_identity_sha256':'i'})
    api['imports'].verify_import_receipt=lambda *a,**k:None
    exhaust(api['run_import_stage'](tmp_path,tmp_path/'imports',python='/chosen'))
    assert seen==[('verify','/chosen'),('imports','/chosen')]

@pytest.mark.parametrize('name',['imports-precheck','imports-final','baseline','final','artifact','convergence','manifest-check','prepackage'])
def test_step_transports_locator_to_child_owners(tmp_path,name):
    api=load_api();seen=[]
    def fake(*a,**k):seen.append(k.get('python'));yield NS(text='mock');return {'totals':{}}
    api.update(run_import_stage=fake,run_partitions=fake,artifact_stage=fake,registry_selection=lambda *a:{},checked=lambda argv,source:(need(argv[2:4]==['--python','/chosen'],'manifest consumer must receive explicit locator'),seen.append(argv[0]))[-1],verified_final=lambda *a,**k:(seen.append(k.get('python')) or ({'passed':1,'skipped':0},{})),verify_current_imports=lambda *a,**k:seen.append(k.get('python')))
    exhaust(api['execute_step'](NS(source=tmp_path,out=tmp_path/'output',step=name,files_per_partition=7,retry_reason=None,python='/chosen')))
    assert seen and all(p=='/chosen' for p in seen)

def verified_import_summary_fixture(api,status):
    """Declared two-module intercepted result, not measured import-run evidence."""
    need(status in api['imports'].IMPORT_READY_STATES,'intercepted import verifier refused '+status)
    return {'status':status,'scope_counts':{'PRODUCTION':2,'TEST_OR_FIXTURE':0},
        'rss_sampling':{'zero_peak_records':0,'meaning':'Self-authored intercepted verifier fixture; no measured import audit.'},
        'orders':[{'mode':'general','order':order,'modules':2,'held':0,
                   'optional_unavailable':int(status=='READY_WITH_OPTIONAL_UNAVAILABLE'),'status':status}
                  for order in ['forward','reverse']]}

def test_artifact_consumers_keep_locator_without_opening_zip(tmp_path,monkeypatch):
    api=load_api();out=tmp_path/'output';art=out/'artifact';(art/'source').mkdir(parents=True);(art/'imports').mkdir()
    (art/'artifact.json').write_text(json.dumps({'archive_sha256':'a'*64,'extracted_source_sha256':'digest'}))
    import_status=getattr(api['imports'],'fixture_status','PASS')
    current_status=import_status if import_status in api['imports'].IMPORT_READY_STATES else 'PASS'
    (art/'imports/current.json').write_text(json.dumps({'status':current_status}))
    sentinel=tmp_path/'archive.sentinel';sentinel.write_text('mock only, not an archive')
    monkeypatch.setattr(api['zipfile'],'ZipFile',lambda *a,**k:pytest.fail('existing artifact must not open any ZIP'))
    writes={}
    api['support'].atomic_json=lambda path,value:writes.update({path:json.loads(json.dumps(value))})
    original=Path.glob
    monkeypatch.setattr(Path,'glob',lambda self,pattern:iter([sentinel]) if self==out/'packages/code' else original(self,pattern))
    seen=[];api['partitions'].source_digest=lambda _: 'digest'
    api['require_registry_preflight']=lambda source,selected,python:seen.append(python)
    api['checked']=lambda argv,source:seen.append(argv[0])
    api['verify_current_imports']=lambda *a,**k:(seen.append(k.get('python')) or verified_import_summary_fixture(api,import_status))
    def partitions(*a,**k):seen.append(k.get('python'));yield NS(text='mock');return {'totals':{}}
    api['run_partitions']=partitions
    exhaust(api['artifact_stage'](tmp_path,out,7,None,{},python='/chosen'))
    assert import_status in api['imports'].IMPORT_READY_STATES,'held verification must not advance the artifact stage'
    assert len(seen)==5 and all(p=='/chosen' for p in seen)
    assert writes[art/'artifact.json']['import_safety']['status']==import_status
    assert writes[art/'artifact.json']['import_safety']['summary']==verified_import_summary_fixture(api,import_status)
    assert sentinel.read_text()=='mock only, not an archive'

def test_partition_retry_still_requires_explicit_disposition(tmp_path):
    api=load_api();out=tmp_path/'occupied';out.mkdir()
    with pytest.raises(ValueError,match='explicit retry disposition'):
        exhaust(api['run_partitions'](tmp_path,out,7))

@pytest.mark.parametrize('phase,mode',[('package','partitioned'),('','monolithic')])
def test_occupied_targets_remain_with_their_refusal_owner(tmp_path,phase,mode):
    source,out,wrapper,capture,flags,env,args=shell_fixture(tmp_path,resume=True,phase=phase);env['RELEASE_PYTEST_MODE']=mode
    text=(ROOT/'tools/release_cut.sh').read_text();prefix=text.split('\nsource "$SRC/tools/cut_preflight.sh"',1)[0]
    tail=text[text.rindex('if [[ -n "$PHASE" ]]; then'):]
    run=subprocess.run(['bash','-s','--',*args],input=prefix+'\nbuild_tiers(){ echo BAD_BUILD; };\n'+tail,cwd=tmp_path,env=env,capture_output=True,text=True,timeout=5)
    assert run.returncode!=0 and 'BAD_BUILD' not in run.stdout and not capture.exists()
    assert ('package target is occupied' if phase else 'RELEASE-PATH-003') in run.stderr
    assert (out/'prior').read_bytes()==b'preserve'

def test_exporter_receives_exact_bound_arguments_and_refusal_propagates(tmp_path):
    source,out,wrapper,capture,flags,env,args=shell_fixture(tmp_path,phase='package')
    builder=tmp_path/'builder.json';env['BUILDER_CAPTURE']=str(builder)
    text=(ROOT/'tools/release_cut.sh').read_text();prefix=text.split('\nsource "$SRC/tools/cut_preflight.sh"',1)[0]
    registry='registry_preflight(){'+text.split('\nregistry_preflight(){',1)[1].split('\n}\n',1)[0]+'\n}\n'
    build='build_tiers(){'+text.split('\nbuild_tiers(){',1)[1].split('\n}\n',1)[0]+'\n}\n'
    spy='''
bash(){
 "$PYTHON" - "$@" <<'PY'
import json,os,sys
from pathlib import Path
Path(os.environ['BUILDER_CAPTURE']).write_text(json.dumps(dict(argv=sys.argv[1:],python=os.environ['PYTHON'],skip=os.environ.get('SKIP_INTIER_PYTEST'))))
PY
 return 7
}
rm(){ :; } # Retain the producer's newly created local cutlog fixture.
'''
    run=subprocess.run(['bash','-s','--',*args],input=prefix+'\n'+registry+build+spy+'\nbuild_tiers\n',cwd=tmp_path,env=env,capture_output=True,text=True,timeout=5)
    assert run.returncode!=0 and 'tier code cut failed' in run.stderr
    record=json.loads(builder.read_text())
    assert record['argv']==['tools/make_public_tier.sh','code',str(source),str(out/'code'),*flags]
    assert record['python']==str(wrapper) and record['skip']=='1'
    assert json.loads(capture.read_text())['args']['python']==str(wrapper)
    assert not list(out.rglob('*.zip'))

@pytest.mark.parametrize('retry,valid',[('final=external prerequisite repaired',True),('final=',False)])
def test_cut_dispatch_keeps_resume_retry_with_workflow_owner(tmp_path,retry,valid):
    api=load_api();source=tmp_path/'source';source.mkdir();out=tmp_path/'existing output';out.mkdir();marker=out/'prior';marker.write_bytes(b'preserve')
    selected=dict(registry_path='/explicit',registry_sha256='1'*64,guard_sha256='2'*64,allowlist_sha256='3'*64)
    calls=[]
    class Workflow:
        def __init__(self,*a,**k):calls.append(('init',a,k))
        def iter_run(self,**k):calls.append(('run',k));yield NS(text='mock execution',code=0,stderr=False);return {'status':'STAGES_COMPLETE'}
    api.update(Workflow=Workflow,registry_selection=lambda *a:selected,require_registry_preflight=lambda *a:None)
    args=api['parse_args'](['cut','--version','9.7.452','--date','20261017','--source',str(source),'--out',str(out),'--python','/chosen','--resume','--retry',retry])
    events=list(api['command_events'](args))
    assert calls[0][1][3]=='/chosen' and calls[0][2]['env']['PYTHON']=='/chosen'
    if valid:assert calls[1]==('run',dict(resume=True,retry={'final':'external prerequisite repaired'}))
    else:assert len(calls)==1 and events[-1].code==2
    assert marker.read_bytes()==b'preserve'


@pytest.mark.parametrize('status',['READY_WITH_OPTIONAL_UNAVAILABLE','HOLD'])
def test_real_import_stage_preserves_readiness_and_locator_or_refuses_hold(tmp_path,status):
    api=load_api();seen=[];writes={}
    api['workflow_environment']=lambda python,source:{'PYTHON':python}
    def importing(source,out,python,**kw):
        seen.append(('imports',python,kw['env']['PYTHON']))
        return {'status':status,'environment_identity_sha256':'fixture-environment'}
    def verifying(*a,**kw):
        seen.append(('verify',kw['env']['PYTHON']))
        return verified_import_summary_fixture(api,status)
    api['imports'].run_import_smoke=importing;api['imports'].verify_import_receipt=verifying
    api['support'].atomic_json=lambda path,value:writes.update({path:value})
    out=tmp_path/'imports'
    if status=='HOLD':
        with pytest.raises(ValueError,match='complete import roster is HOLD'):
            list(api['run_import_stage'](tmp_path,out,python='/chosen'))
        assert seen==[('imports','/chosen','/chosen')]
    else:
        events=list(api['run_import_stage'](tmp_path,out,python='/chosen'))
        assert seen==[('imports','/chosen','/chosen'),('verify','/chosen')]
        assert status in events[0].text
    assert writes[out/'current.json']['status']==status


def current_import_fixture(tmp_path,current_status,verified_status=None):
    api=load_api();out=tmp_path/'imports';out.mkdir();seen=[];writes={}
    (out/'current.json').write_text(json.dumps({'schema':'sapote-mamey.workflow-import-stage.v1','status':current_status,
        'receipt':{'path':'fixture.json','sha256':'a'*64}}))
    api['workflow_environment']=lambda python,source:{'PYTHON':python}
    api['partitions'].read_artifact=lambda directory,reference:(directory/'fixture.json',None)
    api['partitions'].test_environment=lambda source,env:dict(env)
    def admitting(python,**kw):
        seen.append(('admit',python,kw['env']['PYTHON']))
        return {'status':'READY','identity_sha256':'fixture-environment'}
    def verifying(*a,**kw):
        seen.append(('verify',kw['env']['PYTHON']))
        return verified_import_summary_fixture(api,verified_status or current_status)
    api['support'].admit_environment=admitting;api['imports'].verify_import_receipt=verifying
    api['support'].atomic_json=lambda path,value:writes.update({path:value})
    return api,out,seen,writes


@pytest.mark.parametrize('status',['READY_WITH_OPTIONAL_UNAVAILABLE','HOLD'])
def test_real_current_import_consumer_preserves_status_and_locator_or_refuses_hold(tmp_path,status):
    api,out,seen,writes=current_import_fixture(tmp_path,status)
    admission=tmp_path/'admission'
    if status=='HOLD':
        with pytest.raises(ValueError,match='current complete import stage is not PASS'):
            api['verify_current_imports'](tmp_path,out,admission,python='/chosen')
        assert seen==[] and writes=={}
    else:
        summary=api['verify_current_imports'](tmp_path,out,admission,python='/chosen')
        assert summary['status']==status
        assert seen==[('admit','/chosen','/chosen'),('verify','/chosen')]
        assert writes[admission/'import-verification.json']['summary']==summary


def test_real_current_import_consumer_refuses_status_substitution(tmp_path):
    api,out,seen,writes=current_import_fixture(tmp_path,'READY_WITH_OPTIONAL_UNAVAILABLE','PASS')
    with pytest.raises(ValueError,match='current import status differs from verified receipt'):
        api['verify_current_imports'](tmp_path,out,tmp_path/'admission',python='/chosen')
    assert seen==[('admit','/chosen','/chosen'),('verify','/chosen')] and writes=={}


def test_artifact_optional_ready_preserves_status_locator_and_zip_sentinel(tmp_path,monkeypatch):
    original_load=load_api
    def loading():
        api=original_load();api['imports'].fixture_status='READY_WITH_OPTIONAL_UNAVAILABLE';return api
    monkeypatch.setattr(sys.modules[__name__],'load_api',loading)
    test_artifact_consumers_keep_locator_without_opening_zip(tmp_path,monkeypatch)


def test_artifact_refuses_held_verifier_without_opening_zip(tmp_path,monkeypatch):
    original_load=load_api
    def loading():
        api=original_load();api['imports'].fixture_status='HOLD';return api
    monkeypatch.setattr(sys.modules[__name__],'load_api',loading)
    with pytest.raises(ValueError,match='intercepted import verifier refused HOLD'):
        test_artifact_consumers_keep_locator_without_opening_zip(tmp_path,monkeypatch)
