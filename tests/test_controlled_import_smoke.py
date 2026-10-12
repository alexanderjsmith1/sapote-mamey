"""Complete roster, actual sandbox enforcement and planted import-state regressions."""
from pathlib import Path
import importlib
import json
import os
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def smoke(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT/'tools'))
    return importlib.import_module('_release_import_smoke')


def fixture_source(tmp_path, modules):
    source=tmp_path/'source';source.mkdir();(source/'mamey').mkdir();(source/'tools').mkdir()
    (source/'mamey/__init__.py').write_text('# source-only fixture\n')
    for name,text in modules.items():
        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
    return source


def test_static_roster_counts_nested_tests_and_alias_setters_without_importing(smoke,tmp_path):
    source=fixture_source(tmp_path,{
        'mamey/clean.py':'raise AssertionError("static inventory must not import")\n',
        'tools/nested/tool.py':'import csv as c\nc.field_size_limit(999)\n',
        'tools/aliased.py':'from csv import field_size_limit as set_limit\nset_limit(999)\n',
        'tools/dynamic.py':'getattr(__import__("csv"), "field_size_limit")(999)\n',
        'tools/test_real.py':'raise AssertionError("test file stays explicitly outside production")\n',
        'tools/nested/tests/helper.py':'raise AssertionError("test helper")\n',
        'tools/ladder_test.py':'# production command; suffix alone does not exclude it\n',
        'mamey/bad_syntax.py':'this is not python syntax!\n'})
    rows=smoke.roster(source);by_path={row['path']:row for row in rows}
    assert len(rows)==9
    assert by_path['tools/test_real.py']['role']=='TEST_OR_FIXTURE'
    assert by_path['tools/nested/tests/helper.py']['role']=='TEST_OR_FIXTURE'
    assert by_path['tools/ladder_test.py']['role']=='PRODUCTION'
    assert by_path['tools/aliased.py']['csv_setter']
    assert by_path['tools/nested/tool.py']['csv_setter']
    assert by_path['tools/dynamic.py']['csv_setter']
    assert by_path['mamey/bad_syntax.py']['parse_error']


@pytest.mark.skipif(sys.platform!='darwin',reason='Only the actual macOS sandbox backend is admitted')
def test_complete_clean_shared_roster_and_csv_orders_pass_in_real_sandbox(smoke,tmp_path):
    source=fixture_source(tmp_path,{'mamey/clean.py':'VALUE=1\n',
        'mamey/validate.py':'import csv,sys\ncsv.field_size_limit(min(sys.maxsize,2**31-1))\n',
        'tools/setter.py':'from csv import field_size_limit as setter\nimport sys\nsetter(min(sys.maxsize,2**31-1))\n',
        'tools/nested/clean.py':'VALUE=2\n','tools/test_ignore.py':'raise AssertionError("not production")\n'})
    report=smoke.run_import_smoke(source,tmp_path/'smoke',sys.executable)
    assert report['status']=='PASS',report
    assert report['sandbox']['status']=='ADMITTED'
    assert len(report['orders'])==4
    assert [row['mode'] for row in report['orders']]==['general','general','csv','csv']
    assert report['scope_counts']=={'PRODUCTION':5,'TEST_OR_FIXTURE':1}
    assert all(len(row['results'])==row['modules'] for row in report['orders'])
    assert report['source_sha256']==report['source_after_sha256']
    forward=report['orders'][0]['results'];reverse=report['orders'][1]['results']
    assert [row['path'] for row in forward]==list(reversed([row['path'] for row in reverse]))
    assert all(not row['state_changes'] and not row['operations'] for result in report['orders'] for row in result['results'])
    assert all('cached_validate' in [check['phase'] for check in row['csv_checks']]
               for order in report['orders'] if order['mode']=='csv' for row in order['results'])


@pytest.mark.skipif(sys.platform!='darwin',reason='Actual sandbox enforcement required')
@pytest.mark.parametrize('name,text,expected',[
 ('mamey/environment.py','import os\nos.environ["PLANTED_IMPORT_STATE"]="secret-not-for-receipts"\n','environment'),
 ('tools/lowering.py','import csv\ncsv.field_size_limit(128)\n','csv_limit'),
 ('tools/exit_now.py','raise SystemExit(0)\n','SystemExit'),
 ('tools/process.py','import subprocess\nsubprocess.run(["/usr/bin/true"])\n','subprocess.Popen'),
 ('tools/terminal.py','print("unrequested output")\n','terminal-write'),
 ('tools/limits.py','import resource\nresource.setrlimit(resource.RLIMIT_NOFILE,(64,64))\n','resource.setrlimit'),
 ('tools/logger.py','import logging\nlogging.getLogger().addHandler(logging.NullHandler())\n','logging'),
])
def test_planted_state_and_hidden_work_are_held_with_complete_outcomes(smoke,tmp_path,name,text,expected):
    source=fixture_source(tmp_path,{name:text,'mamey/validate.py':'import csv,sys\ncsv.field_size_limit(min(sys.maxsize,2**31-1))\n'})
    output=tmp_path/'smoke';report=smoke.run_import_smoke(source,output,sys.executable)
    assert report['status']=='HOLD',report
    rows=[row for order in report['orders'] for row in order['results'] if row['path']==name]
    assert rows and any(row['status']=='HOLD' for row in rows)
    assert expected in json.dumps(rows)
    assert 'secret-not-for-receipts' not in (output/'import-smoke.json').read_text()
    assert len(report['orders'])==4


def test_trace_coverage_refuses_missing_or_duplicate_nodes(smoke,tmp_path):
    source=fixture_source(tmp_path,{'mamey/clean.py':'VALUE=1\n'})
    rows=smoke.roster(source)
    trace=tmp_path/'trace.jsonl'
    trace.write_text(json.dumps({'type':'start','roster_sha256':smoke.roster_digest(rows)})+'\n'+
                     json.dumps({'type':'complete','roster_sha256':smoke.roster_digest(rows),'results':[],'count':0,'status':'PASS'})+'\n')
    with pytest.raises(ValueError,match='omit, duplicate'):
        smoke.verify_worker(trace,rows,'forward','general')


def test_unsupported_backend_refuses_without_importing(smoke,tmp_path,monkeypatch):
    source=fixture_source(tmp_path,{'tools/must_not_run.py':'raise AssertionError("not admitted")\n'})
    monkeypatch.setattr(smoke.sys,'platform','linux')
    with pytest.raises(ValueError,match='No admitted'):
        smoke.admit_sandbox(source,tmp_path/'out',Path(sys.executable),dict(os.environ))


def test_assignment_alias_setter_and_getter_are_distinguished(smoke,tmp_path):
    source=fixture_source(tmp_path,{'tools/alias.py':'import csv\nf=csv.field_size_limit\ng=f\ng(128)\n',
        'tools/getter.py':'import csv\nVALUE=csv.field_size_limit()\n'})
    rows={row['path']:row for row in smoke.roster(source)}
    assert rows['tools/alias.py']['csv_setter']
    assert not rows['tools/getter.py']['csv_setter']


def test_source_symlink_is_refused_before_import(smoke,tmp_path):
    source=fixture_source(tmp_path,{})
    (source/'tools/link.py').symlink_to(source/'mamey/__init__.py')
    with pytest.raises(ValueError,match='symlink'):
        smoke.roster(source)


@pytest.mark.skipif(sys.platform!='darwin',reason='Actual macOS sandbox backend required')
def test_lowering_cannot_be_hidden_by_a_later_validate_import(smoke,tmp_path):
    source=fixture_source(tmp_path,{'tools/lower.py':'import csv\ncsv.field_size_limit(128)\n',
        'mamey/validate.py':'import csv,sys\ncsv.field_size_limit(min(sys.maxsize,2**31-1))\n'})
    report=smoke.run_import_smoke(source,tmp_path/'smoke',sys.executable)
    assert report['status']=='HOLD'
    reverse=next(order for order in report['orders'] if order['mode']=='csv' and order['order']=='reverse')
    lower=next(row for row in reverse['results'] if row['path']=='tools/lower.py')
    assert lower['csv_guard']['failed_checks'][0]['value']==128
    assert lower['status']=='HOLD'
    assert any(check['phase']=='initial_validate' and check['value']>=2**31-1 for check in lower['csv_checks'])


@pytest.mark.skipif(sys.platform!='darwin',reason='Actual macOS sandbox enforcement required')
def test_broken_sandbox_policy_refuses_before_production_import(smoke,tmp_path,monkeypatch):
    marker=tmp_path/'must-not-import'
    source=fixture_source(tmp_path,{'tools/unsafe.py':f'from pathlib import Path\nPath({str(marker)!r}).write_text("bad")\n'})
    monkeypatch.setattr(smoke,'mac_profile',lambda *args:'(version 1)\n(allow default)\n')
    report=smoke.run_import_smoke(source,tmp_path/'smoke',sys.executable)
    assert report['status']=='REFUSED' and 'every required control' in report['reason']
    assert not marker.exists() and report['orders']==[]


@pytest.mark.skipif(sys.platform!='darwin',reason='Actual macOS sandbox enforcement required')
def test_normal_native_loading_is_allowed_while_native_controls_are_proven(smoke,tmp_path):
    source=fixture_source(tmp_path,{'tools/native.py':'import ctypes\nLIB=ctypes.CDLL(None)\n'})
    report=smoke.run_import_smoke(source,tmp_path/'smoke',sys.executable)
    assert report['status']=='PASS',report
    assert report['sandbox']['measured']['native_fork']['blocked']
    assert report['sandbox']['measured']['native_network']['blocked']
    assert report['sandbox']['measured']['native_source_write']['blocked']
    assert any(row['native_loads'] for order in report['orders'] for row in order['results'])


@pytest.mark.skipif(sys.platform!='darwin',reason='Actual macOS sandbox enforcement required')
@pytest.mark.parametrize('collision',[False,'file','namespace','extension'])
def test_only_unambiguous_source_priority_swaps_are_admitted(smoke,tmp_path,collision):
    source=fixture_source(tmp_path,{'tools/reorder.py':'import sys\nfrom pathlib import Path\nsys.path.insert(0,str(Path(__file__).parents[1]))\n'})
    if collision == 'file':
        (source/'reorder.py').write_text('VALUE="root shadow"\n')
    elif collision == 'namespace':
        (source/'reorder').mkdir()
    elif collision == 'extension':
        from importlib.machinery import EXTENSION_SUFFIXES
        (source/('reorder'+EXTENSION_SUFFIXES[0])).write_bytes(b'not-loaded extension fixture')
    report=smoke.run_import_smoke(source,tmp_path/'smoke',sys.executable)
    assert report['status']==('HOLD' if collision else 'PASS'),report


@pytest.mark.skipif(sys.platform!='darwin',reason='Actual macOS sandbox enforcement required')
def test_independent_receipt_verifies_complete_evidence_and_refuses_drift(smoke,tmp_path):
    import copy
    import shutil
    source=fixture_source(tmp_path,{'mamey/validate.py':'VALUE=1\n',
        'tools/setter.py':'import csv,sys\ncsv.field_size_limit(min(sys.maxsize,2**31-1))\n'})
    output=tmp_path/'original';report=smoke.run_import_smoke(source,output,sys.executable)
    assert report['status']=='PASS',report
    receipt=output/'import-smoke.json';identity=report['environment_identity_sha256']
    assert smoke.verify_import_receipt(source,receipt,smoke.support.sha256_file(receipt),identity)['status']=='PASS'
    # A quick successful venv probe can exit between RSS samples. Preserve the
    # missing positive measurement explicitly; never interpret it as zero use.
    environment_path=output/'environment/environment.json'
    saved_environment=environment_path.read_text();environment=json.loads(saved_environment)
    environment['steps'][-1]['peak_process_tree_rss']=0
    environment_path.write_text(json.dumps(environment))
    summary=smoke.verify_import_receipt(source,receipt,smoke.support.sha256_file(receipt),identity)
    assert summary['rss_sampling']['zero_peak_records']>=1
    environment_path.write_text(saved_environment)
    with pytest.raises(ValueError,match='SHA-256 mismatch'):
        smoke.verify_import_receipt(source,receipt,'0'*64,identity)
    with pytest.raises(ValueError,match='environment binding mismatch'):
        smoke.verify_import_receipt(source,receipt,smoke.support.sha256_file(receipt),'0'*64)
    for name in ['orders','expired','summary','log','profile','trace','resource','cached_validate']:
        copied=tmp_path/name;shutil.copytree(output,copied)
        data=copy.deepcopy(report)
        if name=='orders':data['orders'].append(data['orders'][0])
        elif name=='expired':data['started_utc']=data['completed_utc']='2000-01-01T00:00:00Z'
        elif name=='summary':data['status']='HOLD'
        elif name=='log':(copied/'general-forward/worker.log').write_text('changed log')
        elif name=='profile':(copied/'general-forward/profile.sb').write_text('(version 1)\n(allow default)\n')
        elif name=='trace':(copied/'general-forward/scratch/trace.jsonl').write_text('')
        elif name=='resource':data['orders'][0]['watch']['rss_stop_bytes']=9_000_000_000
        elif name=='cached_validate':
            target=copied/'csv-reverse/scratch/trace.jsonl'
            events=[json.loads(line) for line in target.read_text().splitlines()]
            row=next(event for event in events if event['type']=='module')
            row['csv_checks']=[check for check in row['csv_checks'] if check['phase']!='cached_validate']
            events[-1]['results'][0]={key:value for key,value in row.items() if key!='type'}
            target.write_text(''.join(json.dumps(event)+'\n' for event in events))
        changed=copied/'import-smoke.json';changed.write_text(json.dumps(data))
        with pytest.raises((ValueError,OSError)):
            smoke.verify_import_receipt(source,changed,smoke.support.sha256_file(changed),identity)
    moved=tmp_path/'moved';shutil.move(output,moved)
    receipt=moved/'import-smoke.json'
    assert smoke.verify_import_receipt(source,receipt,smoke.support.sha256_file(receipt),identity)['status']=='PASS'
    (source/'tools/setter.py').write_text('VALUE=2\n')
    with pytest.raises(ValueError,match='source binding mismatch'):
        smoke.verify_import_receipt(source,receipt,smoke.support.sha256_file(receipt),identity)


@pytest.mark.skipif(sys.platform!='darwin',reason='Actual macOS sandbox enforcement required')
def test_complete_hold_evidence_is_auditable_but_cannot_be_consumed_as_pass(smoke,tmp_path):
    source=fixture_source(tmp_path,{'tools/terminal.py':'print("import side effect")\n'})
    output=tmp_path/'smoke';report=smoke.run_import_smoke(source,output,sys.executable)
    receipt=output/'import-smoke.json';digest=smoke.support.sha256_file(receipt)
    assert smoke.verify_import_receipt(source,receipt,digest,report['environment_identity_sha256'],require_pass=False)['status']=='HOLD'
    with pytest.raises(ValueError,match='unresolved HOLD'):
        smoke.verify_import_receipt(source,receipt,digest,report['environment_identity_sha256'])


@pytest.mark.parametrize('kind',['bytecode','cache_link'])
def test_source_bytecode_is_refused_before_any_production_import(smoke,tmp_path,kind):
    source=fixture_source(tmp_path,{'tools/unsafe.py':'raise AssertionError("not admitted")\n'})
    cache=source/'mamey/__pycache__'
    if kind=='bytecode':
        cache.mkdir();(cache/'unsafe.pyc').write_bytes(b'unbound cached code')
    else:
        outside=tmp_path/'outside';outside.mkdir();cache.symlink_to(outside)
    report=smoke.run_import_smoke(source,tmp_path/'smoke',sys.executable)
    assert report['status']=='REFUSED' and report['orders']==[]
    assert 'source-only import admission' in report['reason']


# Hermetic policy checks; no executable or sandbox runs.
def runtime_evidence(smoke, tmp_path):
    base = tmp_path/'base runtime'; (base/'bin').mkdir(parents=True)
    target = base/'bin/python'; target.write_bytes(b'synthetic interpreter identity'); target.chmod(0o700)
    prefix = tmp_path/'venv with spaces'; (prefix/'bin').mkdir(parents=True)
    invocation = prefix/'bin/python'; invocation.symlink_to(target)
    dependencies = tmp_path/'declared dependencies/site-packages'; dependencies.mkdir(parents=True)
    identity = {'base_prefix': str(base), 'prefix': str(prefix),
                'executable': str(invocation), 'executable_target': str(target),
                'invocation_executable': str(invocation), 'invocation_target': str(target),
                'distributions': [{'location': str(dependencies)}]}
    evidence = {'status': 'READY', 'identity': identity,
                'resolved_executable': str(invocation), 'executable_target': str(target),
                'executable_sha256': smoke.support.sha256_file(target),
                'test_environment_sha256': 'synthetic-bound-environment'}
    bind_runtime_evidence(smoke, evidence)
    return invocation, base, prefix, dependencies, evidence


def bind_runtime_evidence(smoke, evidence):
    import hashlib
    payload = {key: evidence[key] for key in ('executable_sha256', 'identity', 'test_environment_sha256')}
    evidence['identity_sha256'] = hashlib.sha256(smoke.support.canonical_json(payload)).hexdigest()


def test_profile_reads_separate_bound_runtime_and_dependencies_only(smoke, tmp_path):
    python, base, prefix, dependencies, evidence = runtime_evidence(smoke, tmp_path)
    source = tmp_path/'source'; source.mkdir()
    scratch = tmp_path/'controls/scratch'; scratch.mkdir(parents=True)
    profile = smoke.mac_profile(source, scratch, scratch.parent, ROOT/'tools/_release_import_worker.py', python, evidence)
    for path in [base, prefix, dependencies]:
        assert '(subpath '+json.dumps(str(path.resolve()))+')' in profile
    assert '(allow process-exec (literal '+json.dumps(str(python.resolve()))+'))' in profile
    for path in [Path.home(), Path.home()/'.cache', tmp_path, dependencies.parent]:
        assert '(subpath '+json.dumps(str(path.resolve()))+')' not in profile
    assert '(deny default)' in profile and '(deny network*)' in profile and '(deny process-fork)' in profile
    assert '(allow file-write* (subpath '+json.dumps(str(scratch.resolve()))+') (literal "/dev/null"))' in profile


@pytest.mark.parametrize('mutation', ['identity_drift', 'broad_base', 'broad_alias_prefix', 'broad_dependencies',
                                      'missing_dependencies', 'target_drift', 'unbound'])
def test_runtime_read_admission_refuses_unbound_or_broad_evidence(smoke, tmp_path, mutation):
    python, base, prefix, dependencies, evidence = runtime_evidence(smoke, tmp_path)
    if mutation == 'identity_drift':
        evidence['identity']['base_prefix'] = str(tmp_path)
    elif mutation == 'broad_base':
        evidence['identity']['base_prefix'] = str(Path.home()); bind_runtime_evidence(smoke, evidence)
    elif mutation == 'broad_alias_prefix':
        evidence['identity']['prefix'] = '/tmp'; bind_runtime_evidence(smoke, evidence)
    elif mutation == 'broad_dependencies':
        evidence['identity']['distributions'][0]['location'] = str(Path.home()/'.cache'); bind_runtime_evidence(smoke, evidence)
    elif mutation == 'missing_dependencies':
        evidence['identity']['distributions'][0]['location'] = str(tmp_path/'missing/site-packages'); bind_runtime_evidence(smoke, evidence)
    elif mutation == 'target_drift':
        python.resolve().write_bytes(b'changed synthetic executable')
    elif mutation == 'unbound':
        evidence = None
    with pytest.raises(ValueError, match='import runtime admission'):
        smoke.admitted_runtime_reads(python, evidence)
