"""Portable owner-consumer wiring/refusal tests; no real sealer or cohort pipeline."""
from pathlib import Path
import hashlib
import importlib.util
import json
from types import SimpleNamespace

import pytest


ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture
def adapter():
    spec=importlib.util.spec_from_file_location('isolated_owner_consumer',ROOT/'tools/release_owner_consumer.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,sort_keys=True))


@pytest.fixture
def admitted(adapter,tmp_path,monkeypatch):
    source=tmp_path/'source';source.mkdir();(source/'marker').write_text('source')
    output=tmp_path/'workflow';output.mkdir()
    extracted=output/'artifact/source';extracted.mkdir(parents=True);(extracted/'marker').write_text('artifact')
    consumer=tmp_path/'owner-consumer';consumer.write_text('# synthetic executable, never run\n');consumer.chmod(0o700)
    digest=lambda path:hashlib.sha256((path/'marker').read_bytes()).hexdigest()
    totals={'main_counts':{'passed':3},'main_nodes':3,'collection_skips':0,'subtest_counts':{}}
    context={'profile':'configured-full-suite-partitioned-cut','bundle_version':'8.8.8','date':'20990101',
             'letter':'a','files_per_partition':2,'build_stamp':'20990101v888a','seal_status':'NOT_RUN',
             'linux_py312_ci':'NOT_RUN_LOCALLY','import_safety':'REQUIRED_COMPLETE_SOURCE_AND_ARTIFACT'}
    final=output/'final/partition.json'
    artifact_final=output/'artifact/validation/partition.json'
    for path,current in [(final,source),(artifact_final,extracted)]:
        dump(path,{'schema':'synthetic-final','status':'PASS','source_sha256':digest(current),'totals':totals})
    archive=output/'packages/code/synthetic.zip';archive.parent.mkdir(parents=True);archive.write_bytes(b'fake archive, not extracted')
    current_imports=output/'artifact/imports/current.json';dump(current_imports,{'status':'PASS'})
    source_current_imports=output/'imports-final/current.json';dump(source_current_imports,{'status':'PASS'})
    artifact=output/'artifact/artifact.json'
    dump(artifact,{'status':'EXTRACTED_SUITE_PASS','archive_sha256':adapter.file_pin(archive)['sha256'],
        'extracted_source_sha256':digest(extracted),'partition_receipt':{
            'path':'validation/partition.json','sha256':adapter.file_pin(artifact_final)['sha256']},
        'summary':totals,'import_safety':{'status':'PASS','current_sha256':adapter.file_pin(current_imports)['sha256']}})
    root_record={'status':'STAGES_COMPLETE','committed_source_sha256':digest(source),'context':context,'stages':[]}
    args=dict(source=source,workflow=output/'workflow.json',workflow_sha256='',evidence=tmp_path/'owner evidence',
              target=tmp_path/'owner target',consumer=consumer,consumer_sha256=adapter.file_pin(consumer)['sha256'],
              owner_authorized=True,python='synthetic-python')
    def refresh():
        root_record['stages']=[]
        for name,files in [('final',[final]),('imports-final',[source_current_imports]),
                           ('package',[archive]),('artifact',[artifact,artifact_final,current_imports])]:
            rows=[]
            for path in files:
                if path.is_file():
                    pin=adapter.file_pin(path);rows.append(dict(pin,path=path.relative_to(output).as_posix()))
            attempt=output/'attempts'/name/'attempt.json';dump(attempt,{'outputs':rows})
            root_record['stages'].append({'name':name,'status':'PASS',
                'active':{'path':attempt.relative_to(output).as_posix(),'sha256':adapter.file_pin(attempt)['sha256']}})
        dump(args['workflow'],root_record);args['workflow_sha256']=adapter.file_pin(args['workflow'])['sha256']
    refresh()
    calls=[];faults={};after_import=[None];during_consumer=[None];partition_admissions=[];import_admissions=[]
    def visit(name):
        calls.append(name)
        if name in faults:raise ValueError('injected refusal '+name)
    def atomic(path,value):dump(path,value)
    class Engine:
        def __init__(self,*pos,**kw):
            assert pos==(source,output,('synthetic owned plan',),'synthetic-python')
            assert kw['context']==context
            self.env=dict(kw['env'])
        def verify(self,expected,admission):
            visit('workflow')
            measured=adapter.read_json(args['workflow'],expected)
            if measured['status']!='STAGES_COMPLETE' or measured['committed_source_sha256']!=digest(source):
                raise ValueError('root incomplete or source changed')
            return {'status':'VERIFIED_STAGES','root_sha256':expected,'owner_adoption':'NOT_AUTHORIZED'}
        def check_history(self):
            visit('history')
            for stage in root_record['stages']:
                reference=stage['active']
                attempt=adapter.read_json(output/reference['path'],reference['sha256'])
                for row in attempt['outputs']:
                    adapter.file_pin(output/row['path'],row['sha256'])
    def admit(python,*,output,env):
        assert python=='synthetic-python' and env=={'bound':'synthetic','PWD':str(source)}
        partition_admissions.append({'output':output,'env':dict(env)})
        output.mkdir(parents=True);value={'status':'READY','identity_sha256':'environment'}
        dump(output/'environment.json',value);return value
    def verify_partition(receipt,current,expected,environment):
        name='partition-source' if current==source else 'partition-artifact';visit(name)
        assert environment=='environment'
        value=adapter.read_json(receipt,expected)
        if value['status']!='PASS' or value['schema']!='synthetic-final' or value['source_sha256']!=digest(current):
            raise ValueError('partition not complete final PASS')
        return value['totals']
    def imports(current,directory,admission,*,python):
        import_admissions.append({'source':current,'python':python})
        name='imports-source' if current==source else 'imports-artifact';visit(name)
        if name=='imports-artifact' and after_import[0]:after_import[0]()
        if faults.get('held-'+name):return {'status':'HOLD'}
        return {'status':json.loads((directory/'current.json').read_text())['status'],'scope_counts':{'PRODUCTION':2}}
    def watched(command,*,cwd,log,env,timeout):
        visit('consumer')
        assert cwd==consumer.parent and command[0]==str(consumer)
        assert command[1]=='--verified-release-record' and command[3]=='--verified-release-record-sha256'
        pin=adapter.file_pin(Path(command[2]),command[4]);assert pin['mode']==0o444
        payload=adapter.read_json(Path(command[2]),command[4])
        assert payload['archive']['sha256']==adapter.file_pin(archive)['sha256']
        assert payload['root']['sha256']==args['workflow_sha256']
        assert command[5:]==['--seal-target',str(args['target'])]
        assert payload['source_partition']['verified_totals']==totals
        assert payload['artifact_partition']['verified_totals']==totals
        assert payload['source_complete_imports']['status']==json.loads((output/'imports-final/current.json').read_text())['status']
        assert payload['artifact_complete_imports']['status']==json.loads(current_imports.read_text())['status']
        if during_consumer[0]:during_consumer[0]()
        log.write_text('synthetic owner consumer output\n')
        return {'exit_code':0,'stop_reason':None,'cleanup_error':None}
    backend=SimpleNamespace(workflow=SimpleNamespace(
        Workflow=Engine,cut_context=lambda *values:context,plan=lambda *values:('synthetic owned plan',),
        workflow_environment=lambda python,current:{'bound':'synthetic','PWD':str(current)},verify_current_imports=imports),
        partitions=SimpleNamespace(source_digest=digest,test_environment=lambda current,env:dict(env),
                                   verify_partition_receipt=verify_partition),
        support=SimpleNamespace(admit_environment=admit,atomic_json=atomic,utc_now=lambda:'synthetic-time',run_watched=watched))
    monkeypatch.setattr(adapter,'owners',lambda:backend)
    return SimpleNamespace(module=adapter,args=args,calls=calls,faults=faults,backend=backend,output=output,source=source,
        extracted=extracted,consumer=consumer,archive=archive,final=final,artifact_final=artifact_final,
        artifact=artifact,current_imports=current_imports,refresh=refresh,root_record=root_record,
        after_import=after_import,during_consumer=during_consumer,partition_admissions=partition_admissions,
        import_admissions=import_admissions)


def test_complete_binding_reaches_external_owner_only_after_all_verifiers(admitted):
    f=admitted;result=f.module.consume(**f.args)
    assert f.calls==['workflow','partition-source','imports-source','partition-artifact','imports-artifact',
                     'history','history','consumer','history']
    assert result['status']=='OWNER_CONSUMER_COMPLETED' and result['owner_invoked'] is True
    assert result['seal_status']=='NOT_ESTABLISHED_BY_ADAPTER'
    assert not f.args['target'].exists()


def test_both_import_admissions_use_distinct_requested_interpreter(admitted):
    f=admitted
    assert f.args['python'] != f.module.sys.executable
    f.module.consume(**f.args)
    assert f.import_admissions == [
        {'source':f.source,'python':f.args['python']},
        {'source':f.extracted,'python':f.args['python']}]
    assert 'consumer' in f.calls


def test_both_partition_admissions_keep_original_workflow_pwd(admitted):
    f=admitted;f.module.consume(**f.args)
    assert f.source!=f.extracted
    assert [row['output'] for row in f.partition_admissions]==[
        f.args['evidence']/'source-partition',f.args['evidence']/'artifact-partition']
    assert [row['env']['PWD'] for row in f.partition_admissions]==[str(f.source),str(f.source)]
    assert f.backend.workflow.workflow_environment('synthetic-python',f.extracted)['PWD']==str(f.extracted)
    assert 'consumer' in f.calls


@pytest.mark.parametrize('field,value,message',[
    ('owner_authorized',False,'authorization'),('workflow_sha256','0'*64,'SHA-256'),
    ('consumer_sha256','0'*64,'SHA-256'),('timeout',0,'positive')])
def test_preflight_refusals_never_create_evidence_or_invoke_owner(admitted,field,value,message):
    f=admitted;f.args[field]=value
    with pytest.raises(ValueError,match=message):f.module.consume(**f.args)
    assert not f.calls and not f.args['evidence'].exists()


@pytest.mark.parametrize('which',['target','evidence'])
@pytest.mark.parametrize('kind',['file','directory','dangling_symlink'])
def test_occupied_destinations_are_preserved(admitted,which,kind):
    f=admitted;path=f.args[which]
    if kind=='file':path.write_text('retain')
    elif kind=='directory':path.mkdir();(path/'retain').write_text('retain')
    else:path.symlink_to(path.parent/'missing')
    with pytest.raises(ValueError,match='occupied'):f.module.consume(**f.args)
    assert not f.calls and (path.exists() or path.is_symlink())


@pytest.mark.parametrize('which',['target','evidence'])
@pytest.mark.parametrize('parent',['source','output'])
def test_owner_destinations_cannot_overlap_bound_inputs(admitted,which,parent):
    f=admitted;f.args[which]=getattr(f,parent)/'unwritten'
    with pytest.raises(ValueError,match='separate'):f.module.consume(**f.args)
    assert not f.calls and not f.args[which].exists()


@pytest.mark.parametrize('stage',['workflow','partition-source','imports-source','partition-artifact','imports-artifact','history'])
def test_any_independent_verifier_refusal_blocks_external_owner(admitted,stage):
    f=admitted;f.faults[stage]=True
    with pytest.raises(ValueError,match='injected'):f.module.consume(**f.args)
    attempt=json.loads((f.args['evidence']/'attempt.json').read_text())
    assert 'consumer' not in f.calls and attempt['owner_invoked'] is False
    assert attempt['status']=='OWNER_CONSUMPTION_REFUSED'


@pytest.mark.parametrize('stage',['imports-source','imports-artifact'])
def test_nonpassing_import_verifier_result_never_advances(admitted,stage):
    f=admitted;f.faults['held-'+stage]=True
    with pytest.raises(ValueError,match='not PASS'):f.module.consume(**f.args)
    assert 'consumer' not in f.calls


@pytest.mark.parametrize('value',['WORKING','FAILED','REFUSED_RESUME'])
def test_root_labels_cannot_replace_independent_complete_workflow(admitted,value):
    f=admitted;f.root_record['status']=value;f.refresh()
    with pytest.raises(ValueError,match='incomplete'):f.module.consume(**f.args)
    assert f.calls==['workflow']


@pytest.mark.parametrize('which',['final','artifact_final'])
@pytest.mark.parametrize('status',['PENDING','FAILED','MEASURED'])
def test_only_final_complete_partition_evidence_can_advance(admitted,which,status):
    f=admitted;path=getattr(f,which);value=json.loads(path.read_text());value['status']=status;dump(path,value)
    if which=='artifact_final':
        artifact=json.loads(f.artifact.read_text());artifact['partition_receipt']['sha256']=f.module.file_pin(path)['sha256'];dump(f.artifact,artifact)
    f.refresh()
    with pytest.raises(ValueError,match='final PASS'):f.module.consume(**f.args)
    assert 'consumer' not in f.calls


@pytest.mark.parametrize('field,value,message',[
    ('archive_sha256','0'*64,'verified archive'),('status','EXTRACTED','verified archive'),
    ('extracted_source_sha256','0'*64,'verified archive'),('summary',{},'verified outcomes'),
    ('import_safety',{'status':'HOLD'},'complete import')])
def test_artifact_counts_or_labels_do_not_substitute_for_bound_evidence(admitted,field,value,message):
    f=admitted;artifact=json.loads(f.artifact.read_text());artifact[field]=value;dump(f.artifact,artifact);f.refresh()
    with pytest.raises(ValueError,match=message):f.module.consume(**f.args)
    assert 'consumer' not in f.calls


def test_missing_source_final_receipt_never_reaches_owner(admitted):
    f=admitted;f.final.unlink();f.refresh()
    with pytest.raises(ValueError,match='missing or ambiguous'):f.module.consume(**f.args)
    assert f.calls==['workflow']


def test_ambiguous_code_archives_cannot_reach_owner(admitted):
    f=admitted;stage=next(row for row in f.root_record['stages'] if row['name']=='package')
    attempt=f.output/stage['active']['path'];value=json.loads(attempt.read_text())
    other=f.archive.with_name('other.zip');other.write_bytes(b'another archive')
    row=f.module.file_pin(other);value['outputs'].append(dict(row,path=other.relative_to(f.output).as_posix()))
    dump(attempt,value);stage['active']['sha256']=f.module.file_pin(attempt)['sha256']
    dump(f.args['workflow'],f.root_record);f.args['workflow_sha256']=f.module.file_pin(f.args['workflow'])['sha256']
    with pytest.raises(ValueError,match='ambiguous CODE ZIP'):f.module.consume(**f.args)
    assert 'consumer' not in f.calls


def test_attempt_receipt_drift_after_verifiers_blocks_owner(admitted):
    f=admitted;stage=next(row for row in f.root_record['stages'] if row['name']=='final')
    attempt=f.output/stage['active']['path'];f.after_import[0]=lambda:attempt.write_text('{}')
    with pytest.raises(ValueError,match='SHA-256 mismatch'):f.module.consume(**f.args)
    assert 'consumer' not in f.calls


def test_source_drift_blocks_owner(admitted):
    f=admitted;(f.source/'marker').write_text('drift')
    with pytest.raises(ValueError,match='source changed'):f.module.consume(**f.args)
    assert f.calls==['workflow']


@pytest.mark.parametrize('which',['archive','final','consumer'])
def test_input_drift_after_verifiers_is_refused_before_external_invocation(admitted,which):
    f=admitted;path=getattr(f,which);f.after_import[0]=lambda:path.write_bytes(b'changed after admission')
    with pytest.raises(ValueError,match='changed|SHA-256'):f.module.consume(**f.args)
    assert 'consumer' not in f.calls


def test_target_occupied_during_verification_is_preserved(admitted):
    f=admitted;f.after_import[0]=lambda:f.args['target'].write_text('prior owner output')
    with pytest.raises(ValueError,match='occupied'):f.module.consume(**f.args)
    assert f.args['target'].read_text()=='prior owner output' and 'consumer' not in f.calls


@pytest.mark.parametrize('watch',[{'exit_code':2,'stop_reason':None,'cleanup_error':None},
    {'exit_code':0,'stop_reason':'MEMORY_LIMIT','cleanup_error':None},
    {'exit_code':0,'stop_reason':None,'cleanup_error':'retained child'}])
def test_consumer_return_or_stop_never_becomes_seal_success(admitted,monkeypatch,watch):
    f=admitted;monkeypatch.setattr(f.backend.support,'run_watched',lambda *a,**k:watch)
    with pytest.raises(ValueError,match='failed, stopped'):f.module.consume(**f.args)
    attempt=json.loads((f.args['evidence']/'attempt.json').read_text())
    assert attempt['owner_invoked'] is True and attempt['seal_status']=='NOT_ESTABLISHED_BY_ADAPTER'
    assert attempt['status']=='OWNER_CONSUMPTION_REFUSED'


def test_unreturned_watch_retains_unknown_invocation_and_refuses_in_place_retry(admitted,monkeypatch):
    f=admitted
    def interrupted(*a,**k):raise KeyboardInterrupt()
    monkeypatch.setattr(f.backend.support,'run_watched',interrupted)
    with pytest.raises(KeyboardInterrupt):f.module.consume(**f.args)
    attempt=json.loads((f.args['evidence']/'attempt.json').read_text())
    assert attempt['owner_invoked'] is None and attempt['status']=='OWNER_CONSUMPTION_INTERRUPTED'
    with pytest.raises(ValueError,match='occupied'):f.module.consume(**f.args)


def test_owner_mutating_bound_inputs_is_not_reported_complete(admitted):
    f=admitted;f.during_consumer[0]=lambda:f.archive.write_bytes(b'owner changed input')
    with pytest.raises(ValueError,match='changed|SHA-256'):f.module.consume(**f.args)
    attempt=json.loads((f.args['evidence']/'attempt.json').read_text())
    assert attempt['owner_invoked'] is True and attempt['status']=='OWNER_CONSUMPTION_REFUSED'


def test_help_and_missing_authorization_do_not_load_release_owners(adapter,monkeypatch,capsys,tmp_path):
    def forbidden():raise AssertionError('owners must not load')
    monkeypatch.setattr(adapter,'owners',forbidden)
    with pytest.raises(SystemExit) as raised:adapter.main(['--help'])
    assert raised.value.code==0 and '--owner-authorized' in capsys.readouterr().out
    argv=[]
    for key in ['source','workflow','evidence','target','consumer']:
        argv.extend(['--'+key,str(tmp_path/key)])
    argv.extend(['--workflow-sha256','a'*64,'--consumer-sha256','b'*64])
    assert adapter.main(argv)==2
    assert 'authorization' in capsys.readouterr().err


@pytest.mark.parametrize('globally_disabled', [False, True],
                         ids=['global-disable-0', 'global-disable-CRITICAL'])
def test_cli_logging_preserves_exact_streams_without_global_configuration(adapter,capsys,globally_disabled):
    import logging
    previous_disable = logging.Logger.manager.disable
    disabled_level = logging.CRITICAL if globally_disabled else 0
    try:
        logging.disable(disabled_level)
        before = {name: (list(logger.handlers), logger.level, logger.propagate)
                  for name, logger in logging.Logger.manager.loggerDict.items()
                  if isinstance(logger, logging.Logger)}
        root_before = (list(logging.getLogger().handlers), logging.getLogger().level)
        adapter._report_cli('success record')
        adapter._report_cli('refusal record', error=True)
        captured = capsys.readouterr()
        assert captured.out == 'success record\n' and captured.err == 'refusal record\n'
        after = {name: (list(logger.handlers), logger.level, logger.propagate)
                 for name, logger in logging.Logger.manager.loggerDict.items()
                 if isinstance(logger, logging.Logger)}
        assert before == after
        assert root_before == (list(logging.getLogger().handlers), logging.getLogger().level)
        assert logging.Logger.manager.disable == disabled_level
    finally:
        logging.disable(previous_disable)


def test_explicit_optional_import_readiness_remains_visible_to_owner(admitted):
    fixture=admitted
    for path in [fixture.output/'imports-final/current.json',fixture.current_imports]:
        dump(path,{'status':'READY_WITH_OPTIONAL_UNAVAILABLE'})
    record=json.loads(fixture.artifact.read_text())
    record['import_safety']['status']='READY_WITH_OPTIONAL_UNAVAILABLE'
    record['import_safety']['current_sha256']=fixture.module.file_pin(fixture.current_imports)['sha256']
    dump(fixture.artifact,record);fixture.refresh()
    result=fixture.module.consume(**fixture.args)
    assert result['status']=='OWNER_CONSUMER_COMPLETED'
