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
    assert report['status']==('HOLD' if collision in {'file','extension'} else 'PASS'),report


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


# Lightweight v2 contract controls; no native backend or whole-source import run.

def _path_pair(source):
    return [str(source/'tools'),str(source),'/foreign/runtime'],[str(source),str(source/'tools'),'/foreign/runtime']


@pytest.mark.parametrize('kind',['regular_over_namespace','disjoint_namespace','duplicates'])
def test_contract_v2_proven_paths(smoke,tmp_path,kind):
    source=fixture_source(tmp_path,{'tools/local_helper.py':'VALUE=1\n'})
    if kind=='regular_over_namespace':
        (source/'shared').mkdir();(source/'shared/__init__.py').write_text('VALUE=1\n')
        (source/'tools/shared').mkdir();(source/'tools/shared/leaf.py').write_text('VALUE=2\n')
    if kind=='disjoint_namespace':
        for base,name in [(source,'one'),(source/'tools','two')]:
            (base/'shared').mkdir();(base/'shared'/(name+'.py')).write_text('VALUE=1\n')
            (base/'shared'/(name+'.txt')).write_text('resource\n')
    before,after=_path_pair(source)
    if kind=='duplicates':
        before=[before[0]]*300+before;after=after[:2]*100+after
    proof=smoke.import_contract.trusted_path_equivalence(source,before,after)
    assert proof['equivalent'],proof
    assert smoke.import_contract.unpack_paths(proof['before'])==before
    assert smoke.import_contract.unpack_paths(proof['after'])==after


@pytest.mark.parametrize('kind',['module','namespace_leaf','resource','resource_kind','symlink_init','symlink_nested','foreign_priority','foreign_tail','unsupported','walk_error'])
def test_contract_v2_unsafe_paths_hold(smoke,tmp_path,monkeypatch,kind):
    source=fixture_source(tmp_path,{})
    before,after=_path_pair(source)
    if kind=='module':
        (source/'collision.py').write_text('VALUE=1\n');(source/'tools/collision.py').write_text('VALUE=2\n')
    elif kind in {'namespace_leaf','resource','resource_kind','symlink_init','symlink_nested','walk_error'}:
        for base in [source,source/'tools']:(base/'shared').mkdir()
        if kind=='namespace_leaf':
            for base in [source,source/'tools']:(base/'shared/leaf.py').write_text('VALUE=1\n')
        if kind=='resource':
            for base in [source,source/'tools']:(base/'shared/data.txt').write_text('resource\n')
        if kind=='resource_kind':
            (source/'shared/data').mkdir();(source/'tools/shared/data').write_text('resource\n')
        if kind=='symlink_init':(source/'tools/shared/__init__.py').symlink_to(source/'mamey/__init__.py')
        if kind=='symlink_nested':
            (source/'shared/nested').mkdir();(source/'shared/nested/leaf.py').symlink_to(source/'mamey/__init__.py')
        if kind=='walk_error':
            def bad_walk(*args,**kwargs):
                kwargs['onerror'](PermissionError('planted namespace read refusal'))
                yield
            monkeypatch.setattr(smoke.import_contract.os,'walk',bad_walk)
    elif kind=='foreign_priority':after.insert(0,'/foreign/shadow')
    elif kind=='foreign_tail':after[-1]='/foreign/changed'
    elif kind=='unsupported':before.append(None)
    proof=smoke.import_contract.trusted_path_equivalence(source,before,after)
    assert not proof['equivalent'],proof


def test_contract_v2_actual_finder_origins_and_local_priority(smoke,tmp_path,monkeypatch):
    from importlib.machinery import PathFinder
    source=fixture_source(tmp_path,{'tools/lane_local.py':'VALUE="local"\n'})
    foreign=tmp_path/'foreign';foreign.mkdir();(foreign/'lane_local.py').write_text('VALUE="foreign"\n')
    (source/'shared').mkdir();(source/'shared/__init__.py').write_text('VALUE=1\n')
    (source/'tools/shared').mkdir()
    before,after=_path_pair(source);before[-1]=after[-1]=str(foreign)
    for paths in [before,after]:
        assert PathFinder.find_spec('lane_local',paths).origin==str(source/'tools/lane_local.py')
        assert PathFinder.find_spec('shared',paths).origin==str(source/'shared/__init__.py')
    monkeypatch.chdir(foreign)
    assert smoke.import_contract.trusted_path_equivalence(source,before,after)['equivalent']


def _vendor_fixture(smoke,tmp_path):
    import shutil
    source=fixture_source(tmp_path,{})
    # Exactly ten code inputs; no scientific data, registry or whole source clone.
    for relative,pinned in smoke.import_contract.VENDOR_PINS.items():
        target=source/relative;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/relative,target)
        assert smoke.support.sha256_file(target)==pinned
    return source


def _native_absence(smoke,source,backend='yajl2_c'):
    contract=smoke.import_contract
    relative=contract.VENDOR_BASE+'backends/'+backend+'.py'
    entry={'path':relative,'module':'mamey._vendor.ijson.backends.'+backend,'sha256':contract.VENDOR_PINS[relative]}
    evidence={'type':'ImportError','type_module':'builtins','name':'mamey._vendor.ijson.backends',
        'message':"cannot import name '_yajl2' from 'mamey._vendor.ijson.backends' ("+str(source/contract.VENDOR_BASE/'backends/__init__.py')+")",
        'class_origin':None,'frames':[{'path':str(source/relative),'sha256':entry['sha256'],'function':'<module>','line':1}]}
    return entry,evidence


def test_contract_v2_exact_optional_absence_and_required_fallback(smoke,tmp_path):
    source=_vendor_fixture(smoke,tmp_path);contract=smoke.import_contract
    policy=contract.vendor_policy(source,[],{})
    entry,evidence=_native_absence(smoke,source)
    availability=contract.optional_unavailability(source,entry,evidence,policy)
    assert availability['status']=='OPTIONAL_UNAVAILABLE'
    unavailable={'module':entry['module'],'status':'OPTIONAL_UNAVAILABLE'}
    assert contract.import_readiness([unavailable],policy)=='HOLD'
    fallback={'module':contract.FALLBACK_MODULE,'status':'PASS','fallback_capability':{'status':'PASS'}}
    assert contract.import_readiness([unavailable,fallback],policy)=='READY_WITH_OPTIONAL_UNAVAILABLE'
    assert contract.import_readiness([unavailable,dict(fallback,status='HOLD')],policy)=='HOLD'


@pytest.mark.parametrize('mutation',['vendor','class','origin','internal_missing','explicit_backend','explicit_dll','native_present','unknown_error'])
def test_contract_v2_unknown_optional_failures_hold(smoke,tmp_path,mutation):
    source=_vendor_fixture(smoke,tmp_path);contract=smoke.import_contract
    env={};entry,evidence=_native_absence(smoke,source)
    if mutation=='vendor':(source/entry['path']).write_text('# changed\n')
    if mutation=='class':evidence['type_module']='foreign'
    if mutation=='origin':evidence['frames'][0]['path']='/foreign/yajl2_c.py'
    if mutation=='internal_missing':evidence.update(type='ModuleNotFoundError',name='unrelated_internal',message='missing internal')
    if mutation=='explicit_backend':env['IJSON_BACKEND']='yajl2_c'
    if mutation=='explicit_dll':env['YAJL_DLL']='/explicit/library'
    if mutation=='native_present':(source/contract.VENDOR_BASE/'backends/_yajl2.py').write_text('VALUE=1\n')
    if mutation=='unknown_error':evidence['message']='wrong ABI / version'
    assert contract.optional_unavailability(source,entry,evidence,contract.vendor_policy(source,[],env)) is None


def test_contract_v2_required_python_backend_tiny_json(smoke):
    # Actual third-party pure backend, never project/preloaded native analysis.
    import importlib
    backend=importlib.import_module('ijson.backends.python')
    contract=smoke.import_contract
    policy={'runtime_roots':[str(Path(backend.__file__).resolve().parents[2])]}
    result=contract.check_python_fallback(backend,ROOT,policy)
    assert result['status']=='PASS' and result['backend']=='python'
    assert [row['case'] for row in result['invalid_inputs']]==['incomplete','malformed','trailing_garbage']


def _font_noop_fixture(smoke,tmp_path):
    import hashlib
    cache=tmp_path/'private_cache';cache.mkdir(mode=0o700)
    mpl=tmp_path/'toy_matplotlib';mpl.mkdir();caller=mpl/'__init__.py'
    caller.write_text('def _get_config_or_cache_dir(cache, observer):\n    from pathlib import Path\n    Path(cache).mkdir(mode=0o777,exist_ok=True)\n')
    font={'status':'PREPARED','manifest_sha256':'a'*64,'request':{'cache_root':str(cache),'dependency':{'root':str(mpl)}}}
    identity=smoke.import_contract.directory_identity(cache)
    proof={'event_index':0,'path':str(cache),'before':dict(identity),'after':dict(identity),'exist_ok':True,'mkdir_mode':0o777,'dir_fd':None,
        'result':'EEXIST','caller':{'path':str(caller),'sha256':hashlib.sha256(caller.read_bytes()).hexdigest(),'function':'_get_config_or_cache_dir'},
        'request_payload_sha256':hashlib.sha256(smoke._font_cache.canonical(font['request'])).hexdigest(),'manifest_sha256':'a'*64}
    row={'operations':[{'event':'os.mkdir','path':str(cache),'mode':0o777,'dir_fd':None}],'directory_noops':[proof]}
    return font,row


def test_contract_v2_existing_cache_noop_preserves_raw_event(smoke,tmp_path,monkeypatch):
    contract=smoke.import_contract;font,row=_font_noop_fixture(smoke,tmp_path)
    cache=Path(font['request']['cache_root']);caller=Path(font['request']['dependency']['root'])/'__init__.py'
    original=os.mkdir;seen=[]
    def observed(path,mode=0o777,*,dir_fd=None):
        proof=contract.font_directory_candidate(path,mode,dir_fd,font)
        assert proof is not None
        before=contract.directory_identity(cache)
        try:original(path,mode,dir_fd=dir_fd)
        except FileExistsError:
            seen.append(proof)
            assert contract.directory_identity(cache)==before
            raise
    monkeypatch.setattr(os,'mkdir',observed)
    namespace={};exec(compile(caller.read_text(),str(caller),'exec'),namespace)
    namespace['_get_config_or_cache_dir'](cache,None)
    assert len(seen)==1
    assert contract.blocking_operations(row,font)==[]
    assert row['operations'][0]['event']=='os.mkdir'


@pytest.mark.parametrize('mutation',['changed_identity','wrong_caller','wrong_mode','dir_fd','wrong_path','duplicate','other_operation','missing_proof','manifest'])
def test_contract_v2_cache_probe_cannot_hide_other_operations(smoke,tmp_path,mutation):
    import copy
    font,row=_font_noop_fixture(smoke,tmp_path);row=copy.deepcopy(row)
    proof=row['directory_noops'][0]
    if mutation=='changed_identity':proof['after']['inode']+=1
    if mutation=='wrong_caller':proof['caller']['function']='project_import'
    if mutation=='wrong_mode':row['operations'][0]['mode']=0o700
    if mutation=='dir_fd':row['operations'][0]['dir_fd']=4
    if mutation=='wrong_path':row['operations'][0]['path']+='/child'
    if mutation=='duplicate':row['directory_noops'].append(copy.deepcopy(proof))
    if mutation=='manifest':proof['manifest_sha256']='b'*64
    if mutation=='other_operation':
        row['operations'].append({'event':'thread.start'})
        assert smoke.import_contract.blocking_operations(row,font)==[{'event':'thread.start'}];return
    if mutation=='missing_proof':
        row['directory_noops']=[]
        assert smoke.import_contract.blocking_operations(row,font)==row['operations'];return
    with pytest.raises(ValueError):smoke.import_contract.blocking_operations(row,font)


@pytest.mark.parametrize('kind',['new','symlink','outside','mode','dirfd','wrongcaller'])
def test_contract_v2_unproven_mkdir_has_no_exception(smoke,tmp_path,kind):
    font,row=_font_noop_fixture(smoke,tmp_path);cache=Path(font['request']['cache_root'])
    path=cache;mode=0o777;dirfd=None
    if kind=='new':path=cache/'new'
    if kind=='symlink':
        link=tmp_path/'cache_link';link.symlink_to(cache);path=link
    if kind=='outside':path=tmp_path
    if kind=='mode':mode=0o700
    if kind=='dirfd':dirfd=2
    # This direct call also proves the ordinary project/wrong-caller case.
    assert smoke.import_contract.font_directory_candidate(path,mode,dirfd,font) is None


def _bytecode_cache_inventory(cache):
    """Bind existing cache contents/identity without requiring its absence."""
    import hashlib
    inventory={}
    if not cache.exists() and not cache.is_symlink():
        return inventory
    for path in [cache,*sorted(cache.rglob('*'))] if not cache.is_symlink() else [cache]:
        relative=path.relative_to(cache).as_posix()
        info=path.lstat()
        identity=(info.st_dev,info.st_ino,info.st_mode,info.st_size,info.st_mtime_ns,info.st_ctime_ns)
        if path.is_symlink():
            inventory[relative]=('symlink',identity,os.readlink(path))
        elif path.is_dir():
            inventory[relative]=('directory',identity)
        else:
            assert path.is_file(),'unexpected nonregular bytecode-cache entry'
            inventory[relative]=('file',identity,hashlib.sha256(path.read_bytes()).hexdigest())
    return inventory


@pytest.mark.parametrize('kind',['clean','trusted_paths','foreign_paths','thread'])
def test_contract_v2_tiny_worker_and_verifier(smoke,tmp_path,kind):
    import subprocess
    modules={'tools/clean.py':'VALUE=1\n'}
    if kind=='trusted_paths':modules['tools/change.py']='import sys\nfrom pathlib import Path\nroot=Path(__file__).resolve().parents[1]\nsys.path[:0]=[str(root),str(root/"tools")]\n'
    if kind=='foreign_paths':modules['tools/change.py']='import sys\nsys.path.insert(0,"/planted/foreign")\n'
    if kind=='thread':modules['tools/change.py']='import threading\nthreading.Thread(target=lambda:None).start()\n'
    source=fixture_source(tmp_path,modules);chosen=smoke.roster(source)
    policy=smoke.import_contract.vendor_policy(source,[],dict(os.environ))
    font={'status':'NOT_REQUESTED'};context={'source_sha256':'1'*64,'environment_sha256':'2'*64,'machinery_sha256':'3'*64}
    request={'source':str(source),'roster':chosen,'roster_sha256':smoke.roster_digest(chosen),
        'order':'forward','mode':'general','vendor_policy':policy,'runtime_roots':[],'font_cache':font,'context':context}
    request_path=tmp_path/'request.json';request_path.write_text(json.dumps(request));scratch=tmp_path/'scratch';scratch.mkdir()
    worker=Path(smoke.import_contract.__file__)
    cache=worker.parent/'__pycache__';cache_before=_bytecode_cache_inventory(cache)
    # The launch stays hermetic, but the worker must re-enable bytecode protection
    # itself. run_path executes the script without caching the worker module.
    bootstrap=("import runpy, sys\n"
        "worker = sys.argv[1]\n"
        "sys.argv = sys.argv[1:]\n"
        "assert sys.dont_write_bytecode is True\n"
        "sys.dont_write_bytecode = False\n"
        "assert sys.dont_write_bytecode is False\n"
        "runpy.run_path(worker, run_name='__main__')\n")
    result=subprocess.run([sys.executable,'-I','-B','-c',bootstrap,str(worker),'--request',str(request_path),'--scratch',str(scratch)],
        cwd=scratch,capture_output=True,text=True,timeout=20)
    assert _bytecode_cache_inventory(cache)==cache_before,'tiny worker changed its machinery bytecode cache'
    assert not list(source.rglob('*.pyc'))
    assert result.returncode==(2 if kind in {'foreign_paths','thread'} else 0),result.stderr
    actual=smoke.verify_worker(scratch/'trace.jsonl',chosen,'forward','general',source=source,policy=policy,font=font,context=context)
    assert actual['status']==('HOLD' if kind in {'foreign_paths','thread'} else 'PASS')
    if kind=='trusted_paths':
        row=next(row for row in actual['results'] if row['path']=='tools/change.py')
        assert row['trusted_path_change']['equivalent'] and not row['state_changes']
    if kind=='thread':assert any(row['operations'] for row in actual['results'])


def _trace_contract_fixture(smoke,tmp_path,optional=False):
    contract=smoke.import_contract
    source=_vendor_fixture(smoke,tmp_path) if optional else fixture_source(tmp_path,{'tools/clean.py':'VALUE=1\n'})
    font={'status':'NOT_REQUESTED'};policy=contract.vendor_policy(source,[],{})
    context={'source_sha256':'1'*64,'environment_sha256':'2'*64,'machinery_sha256':'3'*64}
    paths=[str(source/'tools'),str(source),'/foreign/runtime'];packed=contract.pack_paths(paths)
    selected=[row for row in smoke.roster(source) if row['path']=='tools/clean.py']
    if optional:
        selected=[row for row in smoke.roster(source) if row['module'] in {'mamey._vendor.ijson.backends.yajl2_c',contract.FALLBACK_MODULE}]
        selected.sort(key=lambda row:row['module']==contract.FALLBACK_MODULE)
    threshold=min(sys.maxsize,2**31-1)
    rows=[{'path':entry['path'],'module':entry['module'],'cached_before':False,'status':'PASS',
        'csv_checks':[{'phase':'import','value':threshold}],'path_state':{'before':packed,'after':packed},
        'operations':[],'directory_noops':[],'state_changes':{},'csv_limit_after':threshold,
        'resolved_module_path':str(source/entry['path'])} for entry in selected]
    if optional:
        entry,evidence=_native_absence(smoke,source)
        rows[0].update(status='OPTIONAL_UNAVAILABLE',exception_type=evidence['type'],reason=evidence['message'],
            exception_evidence=evidence,optional_availability=contract.optional_unavailability(source,entry,evidence,policy),csv_checks=[])
        rows[0].pop('resolved_module_path')
        common=source/contract.VENDOR_BASE/'common.py'
        rows[1]['fallback_capability']={'status':'PASS','backend':'python',
            'valid_input_sha256':smoke.hashlib.sha256(b'{"import_contract":[1,true,null]}').hexdigest(),
            'events_sha256':contract.digest(contract.FALLBACK_EVENTS),
            'invalid_inputs':[{'case':label,'input_sha256':smoke.hashlib.sha256(payload).hexdigest(),'exception':expected}
                for label,payload,expected in contract.FALLBACK_INVALID_INPUTS],
            'common_origin':{'path':str(common),'sha256':smoke.support.sha256_file(common)}}
    trace=tmp_path/'trace.jsonl'
    def write():
        digest=smoke.roster_digest(selected)
        start={'type':'start','schema':contract.WORKER_SCHEMA,'source':str(source),'roster_sha256':digest,
            'order':'forward','mode':'general','count':len(selected),'context':context,'vendor_policy_sha256':contract.digest(policy),
            'font_descriptor_sha256':contract.digest(font),'initial_paths':packed}
        complete={'type':'complete','schema':contract.WORKER_SCHEMA,'roster_sha256':digest,'order':'forward','mode':'general',
            'count':len(selected),'csv_minimum':threshold,'results':rows,'font_cache_validation':{'status':'NOT_REQUESTED'},
            'status':contract.import_readiness(rows,policy)}
        trace.write_text('\n'.join(json.dumps(item) for item in [start,*[dict(row,type='module') for row in rows],complete])+'\n')
    return source,selected,rows,trace,policy,font,context,write


def test_contract_v2_verifier_typed_optional_and_clean(smoke,tmp_path):
    for optional in [False,True]:
        folder=tmp_path/str(optional);folder.mkdir()
        source,selected,rows,trace,policy,font,context,write=_trace_contract_fixture(smoke,folder,optional)
        write();actual=smoke.verify_worker(trace,selected,'forward','general',source=source,policy=policy,font=font,context=context)
        assert actual['status']==('READY_WITH_OPTIONAL_UNAVAILABLE' if optional else 'PASS')
        assert actual['optional_unavailable']==int(optional)
        assert actual['held']==0


@pytest.mark.parametrize('mutation',['raw_path_chain','missing_path_change','forged_path_proof','resolved_origin','exception','operation','csv','optional_operation','optional_state','fallback_missing','fallback_forged','unknown_optional_origin','optional_reason'])
def test_contract_v2_verifier_rejects_forged_readiness(smoke,tmp_path,mutation):
    optional=mutation.startswith('optional_') or mutation.startswith('fallback_') or mutation=='unknown_optional_origin'
    source,selected,rows,trace,policy,font,context,write=_trace_contract_fixture(smoke,tmp_path,optional)
    row=rows[0];contract=smoke.import_contract
    if mutation=='raw_path_chain':row['path_state']['before']=contract.pack_paths(['/changed'])
    if mutation=='missing_path_change':row['path_state']['after']=contract.pack_paths(['/changed'])
    if mutation=='forged_path_proof':
        row['path_state']['after']=contract.pack_paths(['/changed']);row['trusted_path_change']={'equivalent':True}
    if mutation=='resolved_origin':row['resolved_module_path']='/foreign/module.py'
    if mutation=='exception':row['exception_type']='RuntimeError'
    if mutation in {'operation','optional_operation'}:row['operations']=[{'event':'thread.start'}]
    if mutation=='csv':row['csv_limit_after']=128
    if mutation=='optional_state':row['state_changes']={'environment':{'changed_keys':['PLANTED']}}
    if mutation=='fallback_missing':rows[1].pop('fallback_capability')
    if mutation=='fallback_forged':rows[1]['fallback_capability']['events_sha256']='0'*64
    if mutation=='unknown_optional_origin':row['exception_evidence']['frames'][0]['path']='/foreign/backend.py'
    if mutation=='optional_reason':row['optional_availability']['reason']='arbitrary_exception_skip'
    write()
    if mutation=='fallback_missing':
        data=[json.loads(line) for line in trace.read_text().splitlines()]
        assert data[-1]['status']=='HOLD'
        data[-1]['status']='READY_WITH_OPTIONAL_UNAVAILABLE'
        trace.write_text('\n'.join(json.dumps(item) for item in data)+'\n')
    with pytest.raises(ValueError):smoke.verify_worker(trace,selected,'forward','general',source=source,policy=policy,font=font,context=context)


@pytest.mark.parametrize('backend',['yajl','yajl2','yajl2_cffi'])
def test_contract_v2_exact_yajl_library_absence(smoke,tmp_path,backend):
    source=_vendor_fixture(smoke,tmp_path);contract=smoke.import_contract
    entry,evidence=_native_absence(smoke,source,backend)
    origin=source/contract.VENDOR_BASE/'backends/__init__.py'
    evidence.update(type='YAJLImportError',type_module='mamey._vendor.ijson.backends',message='YAJL shared object not found.',
        class_origin={'path':str(origin),'sha256':smoke.support.sha256_file(origin)})
    if backend=='yajl2_cffi':
        evidence.update(message='Unable to load YAJL.',contexts=[{'type':'OSError','type_module':'builtins','message':'dlopen: no such file','errno':None}])
    evidence['frames'].append(dict(evidence['class_origin'],function='find_yajl_cffi' if backend=='yajl2_cffi' else 'find_yajl_ctypes',line=1))
    policy=contract.vendor_policy(source,[],{})
    assert contract.optional_unavailability(source,entry,evidence,policy)['reason']=='YAJL_LIBRARY_UNAVAILABLE_IN_ADMITTED_ENV'
    evidence['frames'][-1]['function']='arbitrary_loader'
    assert contract.optional_unavailability(source,entry,evidence,policy) is None


def test_contract_v2_cffi_absence_is_exact(smoke,tmp_path):
    source=_vendor_fixture(smoke,tmp_path);contract=smoke.import_contract
    entry,evidence=_native_absence(smoke,source,'yajl2_cffi')
    evidence.update(type='ModuleNotFoundError',type_module='builtins',name='cffi',message="No module named 'cffi'")
    policy=contract.vendor_policy(source,[],{})
    assert contract.optional_unavailability(source,entry,evidence,policy)['reason']=='OPTIONAL_CFFI_UNAVAILABLE'
    evidence['name']='_cffi_backend'
    assert contract.optional_unavailability(source,entry,evidence,policy) is None


def test_contract_v2_font_worker_grant_is_exact_directory_only(smoke,tmp_path,monkeypatch):
    source=fixture_source(tmp_path,{})
    font,row=_font_noop_fixture(smoke,tmp_path)
    font['request']['output']=str(tmp_path/'prepared')
    font['request']['font_tools']=[]
    monkeypatch.setattr(smoke,'admitted_runtime_reads',lambda *args:[])
    profile=smoke.mac_profile(source,tmp_path/'scratch',tmp_path/'controls',Path(smoke.import_contract.__file__),Path(sys.executable),{},font)
    target=json.dumps(font['request']['cache_root'])
    assert '(allow file-write-create file-write-data (literal '+target+'))' in profile
    assert '(subpath '+target+')' not in profile.split('(allow file-write-create file-write-data')[1]
    assert '(deny process-fork)' in profile and '(deny network*)' in profile
    assert 'cache_native_content_write' in smoke.PROBE and 'cache_mode_change' in smoke.PROBE and 'cache_directory_noop' in smoke.PROBE


def test_contract_v2_bootstrap_profile_has_no_project_runtime_root(smoke,tmp_path,monkeypatch):
    source=fixture_source(tmp_path,{})
    monkeypatch.setattr(smoke,'admitted_runtime_reads',lambda *args:[source])
    with pytest.raises(ValueError,match='contains project source'):
        smoke.font_bootstrap_profile(source,tmp_path/'out',Path(sys.executable),{},[])


def test_contract_v2_font_inventory_does_not_skip_dynamic_modules(smoke,tmp_path):
    source=fixture_source(tmp_path,{'tools/static.py':'import matplotlib.font_manager\n',
        'tools/dynamic.py':'__import__("matplotlib.font_manager")\n'})
    rows=smoke.roster(source)
    assert smoke.font_cache_required(rows)
    assert {row['path'] for row in rows if row['role']=='PRODUCTION'}=={'mamey/__init__.py','tools/static.py','tools/dynamic.py'}
    assert not next(row for row in rows if row['path']=='tools/dynamic.py')['matplotlib_import']


@pytest.mark.parametrize('status',['PASS','READY_WITH_OPTIONAL_UNAVAILABLE','HOLD','REFUSED'])
def test_contract_v2_cli_and_workflow_preserve_actual_status(smoke,tmp_path,monkeypatch,status):
    from types import SimpleNamespace
    import release_validate
    import release_workflow
    source=fixture_source(tmp_path,{})
    report={'status':status,'environment_identity_sha256':'environment'}
    def run(current,output,python,**kwargs):
        output.mkdir(parents=True);smoke.support.atomic_json(output/'import-smoke.json',report)
        return report
    monkeypatch.setattr(smoke,'run_import_smoke',run)
    monkeypatch.setattr(smoke,'verify_import_receipt',lambda *args,**kwargs:{'status':status})
    monkeypatch.setattr(release_workflow,'workflow_environment',lambda *args:{})
    args=SimpleNamespace(operation='import-smoke',source=source,out=tmp_path/'cli',python=sys.executable)
    outcome=release_validate.run_operation(args)
    assert outcome.code==(0 if status in smoke.IMPORT_READY_STATES else 2)
    assert 'SMOKE: '+status+' —' in outcome.text
    stage=tmp_path/'stage'
    if status not in smoke.IMPORT_READY_STATES:
        with pytest.raises(ValueError):list(release_workflow.run_import_stage(source,stage))
        assert json.loads((stage/'current.json').read_text())['status']==status
        return
    outcomes=list(release_workflow.run_import_stage(source,stage))
    assert 'STAGE: '+status+' —' in outcomes[0].text
    def admit(python,*,output,env):
        output.mkdir(parents=True)
        return {'status':'READY','identity_sha256':'environment'}
    monkeypatch.setattr(release_workflow.support,'admit_environment',admit)
    assert release_workflow.verify_current_imports(source,stage,tmp_path/'admission')['status']==status
    monkeypatch.setattr(smoke,'verify_import_receipt',lambda *args,**kwargs:{'status':'FORGED_OTHER'})
    with pytest.raises(ValueError,match='status differs'):
        release_workflow.verify_current_imports(source,stage,tmp_path/'mismatch_admission')


def test_contract_v2_bootstrap_controller_runtime_mismatch_refuses_first(smoke,tmp_path,monkeypatch):
    source=fixture_source(tmp_path,{})
    current={'executable':'/actual/python','version':'3.12','prefix':'/actual','base_prefix':'/base'}
    selected={'executable_target':'/actual/python','version':'3.12','prefix':'/different','base_prefix':'/base'}
    monkeypatch.setattr(smoke._font_cache,'runtime_identity',lambda:current)
    with pytest.raises(ValueError,match='selected Python executable and prefix'):
        smoke.prepare_font_cache(source,tmp_path/'never_created',Path(sys.executable),{'identity':selected},{},{})
    assert not (tmp_path/'never_created').exists()


@pytest.mark.parametrize('message,expected',[('dlopen: no such file',True),('wrong architecture; no such file',False),('permission denied; no such file',False),('unknown loader failure',False),('undefined symbol',False)])
def test_contract_v2_loader_failure_requires_clean_absence(smoke,message,expected):
    evidence={'contexts':[{'type':'OSError','type_module':'builtins','message':message,'errno':None}]}
    assert smoke.import_contract.clean_library_absence(evidence) is expected


def test_contract_v2_reconstructed_bootstrap_profile_never_stats_old_output(smoke,tmp_path,monkeypatch):
    source=fixture_source(tmp_path,{})
    old=tmp_path/'original_missing_output'
    resolve=Path.resolve;is_dir=Path.is_dir
    def guarded_resolve(path,*args,**kwargs):
        assert not path.is_relative_to(old),'old output resolve forbidden'
        return resolve(path,*args,**kwargs)
    def guarded_is_dir(path):
        assert not path.is_relative_to(old),'old output stat forbidden'
        return is_dir(path)
    monkeypatch.setattr(Path,'resolve',guarded_resolve)
    monkeypatch.setattr(Path,'is_dir',guarded_is_dir)
    monkeypatch.setattr(smoke,'admitted_runtime_reads',lambda *args:[])
    profile=smoke.font_bootstrap_profile(source,old,Path(sys.executable),{},[])
    assert '(subpath '+json.dumps(str(old/'font-bootstrap'))+')' in profile
    font={'status':'PREPARED','request':{'output':str(old/'font-bootstrap'),'cache_root':str(old/'font-bootstrap/matplotlib'),'font_tools':[]}}
    worker=Path(smoke.import_contract.__file__)
    profile=smoke.mac_profile(source,tmp_path/'current_scratch',tmp_path/'current_controls',worker,Path(sys.executable),{},font)
    assert '(literal '+json.dumps(font['request']['cache_root'])+'))' in profile


@pytest.mark.parametrize('order',['forward','reverse'])
def test_contract_v2_trusted_alias_leaves_ordinary_helper_first_load_guarded(smoke,tmp_path,order):
    import shutil
    import subprocess
    source=fixture_source(tmp_path,{'tools/importer.py':'import _release_font_cache\n'})
    helper=source/'tools/_release_font_cache.py'
    shutil.copyfile(Path(smoke._font_cache.__file__),helper)
    chosen=smoke.roster(source)
    assert len(chosen)==3 and all(row['role']=='PRODUCTION' for row in chosen)
    if order=='reverse':chosen=list(reversed(chosen))
    contract=smoke.import_contract
    policy=contract.vendor_policy(source,[],dict(os.environ))
    font={'status':'NOT_REQUESTED'};context={'source_sha256':'1'*64,'environment_sha256':'2'*64,'machinery_sha256':'3'*64}
    request={'source':str(source),'roster':chosen,'roster_sha256':smoke.roster_digest(chosen),'order':order,'mode':'general',
        'vendor_policy':policy,'runtime_roots':[],'font_cache':font,'context':context}
    request_path=tmp_path/'request.json';request_path.write_text(json.dumps(request));scratch=tmp_path/'scratch';scratch.mkdir()
    # This fresh child observes the real worker. The test-only audit observer
    # attempts a guarded thread start immediately before each ordinary helper's
    # first execution. The installed worker guard refuses it and retains the raw
    # operation in the importing row; no thread starts and no helper role changes.
    driver=r'''
import importlib.util,json,sys,threading
from pathlib import Path
worker_path,request,scratch,helper=map(Path,sys.argv[1:])
spec=importlib.util.spec_from_file_location('_controlled_worker_alias_test',worker_path)
worker=importlib.util.module_from_spec(spec);sys.modules[spec.name]=worker;spec.loader.exec_module(worker)
names=['_release_font_cache','tools._release_font_cache']
initial={'ordinary_absent':all(name not in sys.modules for name in names),
         'machinery_alias':worker._font_cache.__name__,
         'machinery_registered':sys.modules.get('_release_font_cache_machinery') is worker._font_cache}
assert initial['ordinary_absent'] and initial['machinery_registered']
assert worker._font_cache.__name__=='_release_font_cache_machinery'
seen=[]
def observer(event,args):
    if event=='exec' and Path(args[0].co_filename)==helper:
        guarded=threading.Thread.start.__name__=='refuse_thread'
        assert guarded
        try:threading.Thread(target=lambda:None).start()
        except worker.ImportOperationRefused:
            seen.append({'installed_thread_guard':guarded,'refused':True})
        else:raise AssertionError('ordinary helper ran without the installed thread guard')
sys.addaudithook(observer)
code=worker.main(['--request',str(request),'--scratch',str(scratch)])
assert code==2 and len(seen)==2 and all(name in sys.modules for name in names)
sys.__stdout__.write(json.dumps({'initial':initial,'ordinary_executions':seen,'worker_exit':code}))
'''
    result=subprocess.run([sys.executable,'-I','-B','-c',driver,str(Path(contract.__file__)),str(request_path),str(scratch),str(helper)],
        cwd=scratch,capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stderr
    observed=json.loads(result.stdout)
    observation=dict(observed,order=order,roster=chosen,trace_sha256=smoke.support.sha256_file(scratch/'trace.jsonl'))
    (tmp_path/'alias_observation.json').write_text(json.dumps(observation,indent=2)+'\n')
    assert observed['initial']['ordinary_absent'] and len(observed['ordinary_executions'])==2
    actual=smoke.verify_worker(scratch/'trace.jsonl',chosen,order,'general',source=source,policy=policy,font=font,context=context)
    assert actual['status']=='HOLD' and actual['modules']==3
    rows={row['path']:row for row in actual['results']}
    assert rows['tools/_release_font_cache.py']['cached_before'] is False
    for path in ['tools/_release_font_cache.py','tools/importer.py']:
        assert rows[path]['status']=='HOLD'
        assert any(event['event']=='thread.start' and event['disposition']=='BLOCKED' for event in rows[path]['operations'])


def _unsupported_trace(smoke,tmp_path,optional=False):
    values=_trace_contract_fixture(smoke,tmp_path,optional)
    source,selected,rows,trace,policy,font,context,write=values
    marker={'unsupported_path_type':'PlantedPathToken'}
    paths=[str(source/'tools'),str(source),marker, '/fixed/runtime','/fixed/runtime']
    packed=smoke.import_contract.pack_paths(paths)
    for row in rows:row['path_state']={'before':packed,'after':packed}
    write()
    events=[json.loads(line) for line in trace.read_text().splitlines()]
    events[0]['initial_paths']=packed
    trace.write_text('\n'.join(json.dumps(event) for event in events)+'\n')
    return values,paths


@pytest.mark.parametrize('optional',[False,True])
def test_contract_v2_unchanged_unsupported_baseline_cannot_forge_ready(smoke,tmp_path,optional):
    values,paths=_unsupported_trace(smoke,tmp_path,optional)
    source,selected,rows,trace,policy,font,context,write=values
    events=[json.loads(line) for line in trace.read_text().splitlines()]
    assert events[-1]['status']==('READY_WITH_OPTIONAL_UNAVAILABLE' if optional else 'PASS')
    assert all(row['path_state']['before']==row['path_state']['after'] for row in rows)
    with pytest.raises(ValueError,match='unsupported import path entries'):
        smoke.verify_worker(trace,selected,'forward','general',source=source,policy=policy,font=font,context=context)


def test_contract_v2_complete_unchanged_unsupported_hold_remains_auditable(smoke,tmp_path):
    values,paths=_unsupported_trace(smoke,tmp_path)
    source,selected,rows,trace,policy,font,context,write=values
    events=[json.loads(line) for line in trace.read_text().splitlines()]
    for event in events[1:-1]:
        event.update(status='HOLD',path_guard=smoke.import_contract.unsupported_path_guard(paths,paths))
    events[-1]['status']='HOLD';events[-1]['results']=[{key:value for key,value in event.items() if key!='type'} for event in events[1:-1]]
    trace.write_text('\n'.join(json.dumps(event) for event in events)+'\n')
    actual=smoke.verify_worker(trace,selected,'forward','general',source=source,policy=policy,font=font,context=context)
    assert actual['status']=='HOLD' and actual['modules']==len(selected)==actual['held']
    row=actual['results'][0]
    assert row['state_changes']=={} and row['operations']==[]
    assert smoke.import_contract.unpack_paths(row['path_state']['before'])==paths
    assert smoke.import_contract.unpack_paths(row['path_guard']['after'])==paths
    assert row['path_guard']['reason']=='UNSUPPORTED_MODULE_SEARCH_PATH_ENTRY'


@pytest.mark.parametrize('claimed',['PASS','READY_WITH_OPTIONAL_UNAVAILABLE'])
def test_contract_v2_empty_diagnostic_unsupported_initial_state_cannot_be_ready(smoke,tmp_path,claimed):
    values,paths=_unsupported_trace(smoke,tmp_path)
    source,selected,rows,trace,policy,font,context,write=values
    events=[json.loads(line) for line in trace.read_text().splitlines()]
    start=events[0];complete=events[-1];digest=smoke.roster_digest([])
    start.update(roster_sha256=digest,count=0)
    complete.update(roster_sha256=digest,count=0,results=[],status=claimed)
    trace.write_text(json.dumps(start)+'\n'+json.dumps(complete)+'\n')
    with pytest.raises(ValueError,match='summary differs'):
        smoke.verify_worker(trace,[],'forward','general',source=source,policy=policy,font=font,context=context)
    # This standalone empty diagnostic is not admitted as a production roster.
    complete['status']='HOLD'
    trace.write_text(json.dumps(start)+'\n'+json.dumps(complete)+'\n')
    assert smoke.verify_worker(trace,[],'forward','general',source=source,policy=policy,font=font,context=context)['status']=='HOLD'


@pytest.mark.parametrize('repair',[False,True])
def test_contract_v2_worker_unsupported_baseline_is_hold_even_unchanged(smoke,tmp_path,repair):
    import subprocess
    modules={'tools/z_clean.py':'VALUE=1\n'}
    if repair:modules['tools/a_repair.py']='import sys\nsys.path[:]=[value for value in sys.path if type(value) is str]\n'
    source=fixture_source(tmp_path,modules);chosen=smoke.roster(source);contract=smoke.import_contract
    policy=contract.vendor_policy(source,[],dict(os.environ));font={'status':'NOT_REQUESTED'}
    context={'source_sha256':'1'*64,'environment_sha256':'2'*64,'machinery_sha256':'3'*64}
    request={'source':str(source),'roster':chosen,'roster_sha256':smoke.roster_digest(chosen),'order':'forward','mode':'general',
        'vendor_policy':policy,'runtime_roots':[],'font_cache':font,'context':context}
    request_path=tmp_path/'request.json';request_path.write_text(json.dumps(request));scratch=tmp_path/'scratch';scratch.mkdir()
    driver=r'''
import importlib.util,sys
from pathlib import Path
worker_path,request,scratch=map(Path,sys.argv[1:])
spec=importlib.util.spec_from_file_location('_worker_unsupported_baseline_test',worker_path)
worker=importlib.util.module_from_spec(spec);sys.modules[spec.name]=worker;spec.loader.exec_module(worker)
sys.path.append(object())
raise SystemExit(worker.main(['--request',str(request),'--scratch',str(scratch)]))
'''
    result=subprocess.run([sys.executable,'-I','-B','-c',driver,str(Path(contract.__file__)),str(request_path),str(scratch)],
        cwd=scratch,capture_output=True,text=True,timeout=20)
    assert result.returncode==2,result.stderr
    trace=scratch/'trace.jsonl'
    actual=smoke.verify_worker(trace,chosen,'forward','general',source=source,policy=policy,font=font,context=context)
    assert actual['status']=='HOLD' and actual['modules']==len(chosen)
    initial=actual['results'][0]
    assert initial['status']=='HOLD' and initial['path_state']['before']==initial['path_state']['after']
    assert initial['state_changes']=={} and initial['path_guard']['reason']=='UNSUPPORTED_MODULE_SEARCH_PATH_ENTRY'
    assert {'unsupported_path_type':'object'} in contract.unpack_paths(initial['path_guard']['before'])
    if repair:
        assert actual['results'][-1]['status']=='PASS' and actual['held']==2
    else:
        assert actual['held']==len(chosen)
        events=[json.loads(line) for line in trace.read_text().splitlines()]
        # An overall HOLD does not excuse a forged individual PASS on the same
        # unchanged unsupported path state; complete coverage remains exact.
        events[-2]['status']='PASS'
        events[-1]['results']=[{key:value for key,value in event.items() if key!='type'} for event in events[1:-1]]
        forged=tmp_path/'forged_trace.jsonl';forged.write_text('\n'.join(json.dumps(event) for event in events)+'\n')
        with pytest.raises(ValueError,match='unsupported import path entries'):
            smoke.verify_worker(forged,chosen,'forward','general',source=source,policy=policy,font=font,context=context)


def test_contract_v2_cache_inventory_accepts_existing_empty_directory(tmp_path):
    cache=tmp_path/'__pycache__';cache.mkdir()
    before=_bytecode_cache_inventory(cache)
    assert set(before)=={'.'} and before['.'][0]=='directory'
    assert _bytecode_cache_inventory(cache)==before
    assert cache.is_dir() and not list(cache.iterdir())


@pytest.mark.parametrize('change',['new_file','changed_file','same_bytes_rewrite','new_empty_cache'])
def test_contract_v2_cache_inventory_detects_planted_changes(tmp_path,change):
    cache=tmp_path/'__pycache__'
    if change!='new_empty_cache':cache.mkdir()
    planted=cache/'_release_font_cache.planted.pyc'
    if change in {'changed_file','same_bytes_rewrite'}:planted.write_bytes(b'prior bytecode fixture')
    before=_bytecode_cache_inventory(cache)
    if change=='new_empty_cache':cache.mkdir()
    elif change=='new_file':planted.write_bytes(b'new bytecode fixture')
    elif change=='changed_file':planted.write_bytes(b'changed bytecode fixture')
    else:
        planted.write_bytes(b'prior bytecode fixture')
        # Force a distinct timestamp without relying on clock granularity.
        info=planted.stat();os.utime(planted,ns=(info.st_atime_ns,info.st_mtime_ns+1_000_000_000))
    with pytest.raises(AssertionError):
        assert _bytecode_cache_inventory(cache)==before,'planted bytecode/cache change must be detected'


# Native71 CFFI lookup absence, replayed with pinned code fixtures only.

def _cffi_lookup_case(smoke,tmp_path,source=None):
    source=_vendor_fixture(smoke,tmp_path) if source is None else source
    contract=smoke.import_contract
    entry,_=_native_absence(smoke,source,'yajl2_cffi')
    origin=source/contract.VENDOR_BASE/'backends/__init__.py'
    origin={'path':str(origin),'sha256':smoke.support.sha256_file(origin)}
    evidence={'type':'YAJLImportError','type_module':'ijson.backends','name':None,'message':'Unable to load YAJL.',
        'class_origin':origin,'contexts':[{'type':'OSError','type_module':'builtins','name':None,'errno':None,
            'message':"ctypes.util.find_library() did not manage to locate a library called 'yajl'"}],
        'frames':[{'path':str(source/entry['path']),'sha256':entry['sha256'],'function':'<module>','line':63},
                  dict(origin,function='find_yajl_cffi',line=53)]}
    return source,entry,evidence,contract.vendor_policy(source,[],{})


def test_contract_v2_cffi_lookup_absence_exact_pinned_signature(smoke,tmp_path):
    source,entry,evidence,policy=_cffi_lookup_case(smoke,tmp_path)
    assert smoke.import_contract.clean_library_absence(evidence) is False
    result=smoke.import_contract.optional_unavailability(source,entry,evidence,policy)
    assert result['status']=='OPTIONAL_UNAVAILABLE'
    assert result['reason']=='YAJL_LIBRARY_UNAVAILABLE_IN_ADMITTED_ENV'
    assert result['required_fallback']==smoke.import_contract.FALLBACK_MODULE
    assert result['exception']==evidence


@pytest.mark.parametrize('mutation',['abi','symbol','permission','unexplained','other_library','extra_context','cause_errno','cause_name',
    'cause_type_module','exception_class','exception_type_module','exception_name','class_origin_hash','class_origin_foreign',
    'wrapper_hash','wrapper_frame_hash','wrapper_frame_line','finder_frame_line','finder_function','selected_backend','explicit_dll','unknown_vendor'])
def test_contract_v2_cffi_lookup_absence_adverse_mutations_hold(smoke,tmp_path,mutation):
    source,entry,evidence,policy=_cffi_lookup_case(smoke,tmp_path)
    cause=evidence['contexts'][0]
    messages={'abi':'wrong architecture','symbol':'undefined symbol','permission':'permission denied',
        'unexplained':'unknown loader failure','other_library':"ctypes.util.find_library() did not manage to locate a library called 'other'"}
    if mutation in messages:cause['message']=messages[mutation]
    if mutation=='extra_context':evidence['contexts'].append(dict(cause,message='unexplained secondary failure'))
    if mutation=='cause_errno':cause['errno']=13
    if mutation=='cause_name':cause['name']='yajl'
    if mutation=='cause_type_module':cause['type_module']='foreign'
    if mutation=='exception_class':evidence['type']='UnexpectedLoaderError'
    if mutation=='exception_type_module':evidence['type_module']='mamey._vendor.ijson.backends'
    if mutation=='exception_name':evidence['name']='unexpected'
    if mutation=='class_origin_hash':evidence['class_origin']['sha256']='0'*64
    if mutation=='class_origin_foreign':evidence['class_origin']['path']='/foreign/ijson/backends/__init__.py'
    if mutation=='wrapper_hash':entry['sha256']='0'*64
    if mutation=='wrapper_frame_hash':evidence['frames'][0]['sha256']='0'*64
    if mutation=='wrapper_frame_line':evidence['frames'][0]['line']=64
    if mutation=='finder_frame_line':evidence['frames'][1]['line']=54
    if mutation=='finder_function':evidence['frames'][1]['function']='find_yajl_ctypes'
    if mutation=='selected_backend':policy['explicit_backend']='yajl2_cffi'
    if mutation=='explicit_dll':policy['explicit_yajl_dll']=True
    if mutation=='unknown_vendor':policy['status']='UNRECOGNIZED_VENDOR'
    assert smoke.import_contract.optional_unavailability(source,entry,evidence,policy) is None


def test_contract_v2_cffi_lookup_text_does_not_extend_ctypes_wrapper_availability(smoke,tmp_path):
    source,entry,evidence,policy=_cffi_lookup_case(smoke,tmp_path)
    entry,_=_native_absence(smoke,source,'yajl2')
    evidence['frames'][0].update(path=str(source/entry['path']),sha256=entry['sha256'])
    evidence['frames'][1]['function']='find_yajl_ctypes'
    assert smoke.import_contract.optional_unavailability(source,entry,evidence,policy) is None


@pytest.mark.parametrize('mutation',[None,'operation','state','fallback_missing','finder_line','cause_abi'])
def test_contract_v2_cffi_lookup_strict_consumer_replay(smoke,tmp_path,mutation):
    import copy
    source,selected,rows,trace,policy,font,context,write=_trace_contract_fixture(smoke,tmp_path,optional=True)
    _,entry,evidence,_=_cffi_lookup_case(smoke,tmp_path,source)
    selected[0]=next(row for row in smoke.roster(source) if row['module']==entry['module'])
    availability=smoke.import_contract.optional_unavailability(source,entry,evidence,policy)
    assert availability is not None
    rows[0].update(path=entry['path'],module=entry['module'],exception_type=evidence['type'],reason=evidence['message'],
        exception_evidence=copy.deepcopy(evidence),optional_availability=copy.deepcopy(availability))
    if mutation=='operation':rows[0]['operations']=[{'event':'thread.start','disposition':'BLOCKED'}]
    if mutation=='state':rows[0]['state_changes']={'environment':{'changed_keys':['PLANTED']}}
    if mutation=='fallback_missing':rows[1].pop('fallback_capability')
    if mutation=='finder_line':rows[0]['exception_evidence']['frames'][1]['line']=54
    if mutation=='cause_abi':rows[0]['exception_evidence']['contexts'][0]['message']='wrong architecture'
    write()
    if mutation=='fallback_missing':
        events=[json.loads(line) for line in trace.read_text().splitlines()]
        assert events[-1]['status']=='HOLD'
        events[-1]['status']='READY_WITH_OPTIONAL_UNAVAILABLE'
        trace.write_text('\n'.join(json.dumps(event) for event in events)+'\n')
    if mutation is not None:
        with pytest.raises(ValueError):
            smoke.verify_worker(trace,selected,'forward','general',source=source,policy=policy,font=font,context=context)
        return
    result=smoke.verify_worker(trace,selected,'forward','general',source=source,policy=policy,font=font,context=context)
    assert result['status']=='READY_WITH_OPTIONAL_UNAVAILABLE'
    assert result['modules']==2 and result['optional_unavailable']==1 and result['held']==0
    assert result['results'][0]['status']=='OPTIONAL_UNAVAILABLE' and result['results'][1]['status']=='PASS'
