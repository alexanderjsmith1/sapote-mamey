"""Independent protocol acceptance; no native CORASON/scientific tool required."""
from pathlib import Path
from types import SimpleNamespace
import hashlib
import importlib.util
import json
import os
import sys
import tempfile

import pytest

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location('corason_adapter_under_test', TOOLS / 'corason_adapter.py')
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)
from ._corason_contract_fixture import make_case, file_record, write_json, region, sha, CONVERTER, ENTRY, FILTER


@pytest.fixture
def case():
    # Native shell strings cannot safely handle the campaign path's spaces.
    # An explicit owned temporary root is removed only by this fixture.
    # /tmp is space-free on both macOS and Linux; resolve the physical path below.
    base = '/tmp'
    with tempfile.TemporaryDirectory(prefix='corason_test_', dir=base) as raw:
        root = Path(raw).resolve()
        def factory(**options):
            child = root / ('case_' + str(len(list(root.iterdir())))); child.mkdir()
            return make_case(child, A, **options)
        yield factory


def plan_args(c, name='plan'):
    return SimpleNamespace(intake=c['intake'], selection=c['selection'], runtime_manifest=c['runtime'],
        out=c['root']/name, write_root=c['root'], native_work_root=c['workroot'], read_only_root=[])


def planned(c):
    A.plan_command(plan_args(c))
    return c['root']/'plan'/'PLAN.json'


def run_args(c, plan, name='attempt'):
    return SimpleNamespace(plan=plan, out=c['root']/name, write_root=c['root'], read_only_root=[], approved=True)


def completed(c):
    p = planned(c)
    state = A.run_command(run_args(c,p))
    assert state['status'] == 'COMPLETE_SCOPED_EVIDENCE'
    assert state['input_runtime_immutable'] is True
    assert [r['phase'] for r in state['phases']] == ['convert','analyse']
    assert all(r['exit_code']==0 and r['stop_reason'] is None for r in state['phases'])
    return state, json.loads((c['root']/'attempt'/'SELECTED_RESULT.json').read_text())


def refresh_runtime(c, edit):
    data=json.loads(c['runtime'].read_text()); edit(data)
    identity=data['identity']; review=Path(data['review_receipt']['path'])
    value=json.loads(review.read_text());value['identity_sha256']=sha(json.dumps(identity,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode())
    write_json(review,value);data['review_receipt']=file_record(review);write_json(c['runtime'],data)


def test_import_and_plan_do_not_probe_extract_or_launch(case, monkeypatch):
    c=case()
    def forbidden(*args,**kwargs): raise AssertionError('planning launched external code')
    monkeypatch.setattr(A.subprocess,'run',forbidden);monkeypatch.setattr(A,'run_watched',forbidden)
    result=A.plan_command(plan_args(c))
    assert result['release']=='PRIVATE' and result['scope']=='SYNTHETIC_PROTOCOL_ONLY'
    assert result['original_locus_count']==2 and not list(c['workroot'].iterdir())
    assert (c['root']/'plan'/'COMMAND.sh').read_text().endswith('exit 2\n')
    assert not (c['root']/'plan'/'CORASON_GENOMES').exists()


@pytest.mark.parametrize('which',['public_state','public_hash','validation','archive','version','query','accession_roster'])
def test_admission_mismatch_refuses_before_output(case, which):
    c=case(); intake=json.loads(c['intake'].read_text()); first=intake['records'][0]
    if which in ('public_state','public_hash'):
        p=Path(first['public_receipt']['path']);d=json.loads(p.read_text());d['state']='FOLDER_NAMED_PUBLIC'
        write_json(p,d)
        if which=='public_state': first['public_receipt']=file_record(p)
        write_json(c['intake'],intake)
    elif which=='accession_roster':
        p=Path(first['public_receipt']['path']);d=json.loads(p.read_text())
        d['accession_versions']=['FOREIGN.1'];d['primary_sources'][0]['accession_version']='FOREIGN.1'
        write_json(p,d);first['public_receipt']=file_record(p);write_json(c['intake'],intake)
    elif which=='validation':
        Path(first['validation_receipt']['path']).write_text('{}\n')
    elif which=='archive': Path(first['source_zip']).write_bytes(b'changed')
    elif which=='version':
        d=json.loads(c['selection'].read_text());d['loci'][0]=d['loci'][0].replace('CP000001.1','CP000001.2');write_json(c['selection'],d)
    else:
        d=json.loads(c['selection'].read_text());d['query']['exact_locus']='foreign';write_json(c['selection'],d)
    with pytest.raises((A.AdapterError,ValueError)): A.plan_command(plan_args(c))
    assert not (c['root']/'plan').exists() and not list(c['workroot'].iterdir())


@pytest.mark.parametrize('kind',['empty','occupied','dangling','inside_package','outside_root'])
def test_output_boundary_preserves_existing_bytes(case,kind):
    c=case();args=plan_args(c)
    if kind=='empty': args.out.mkdir()
    elif kind=='occupied': args.out.mkdir();(args.out/'old').write_bytes(b'previous evidence')
    elif kind=='dangling': args.out.symlink_to(c['root']/'missing')
    elif kind=='inside_package': args.out=c['root']/'package1'/'new'
    else: args.out=c['root'].parent/'outside'
    original=(c['root']/'package1'/'manifest.json').read_bytes()
    with pytest.raises(A.AdapterError): A.plan_command(args)
    assert (c['root']/'package1'/'manifest.json').read_bytes()==original
    if kind=='occupied': assert (args.out/'old').read_bytes()==b'previous evidence'
    assert not list(c['workroot'].iterdir())


@pytest.mark.parametrize('mutation',['identity_hash','entry','observer','unreviewed','resources','native_source','unsafe_path'])
def test_runtime_profile_is_required_even_for_fake_children(case,mutation):
    c=case();d=json.loads(c['runtime'].read_text())
    if mutation=='identity_hash': d['identity']['environment']['unreviewed']='yes';write_json(c['runtime'],d)
    elif mutation=='entry': refresh_runtime(c,lambda x:x['identity'].update(entry=x['identity']['helpers']['gbkIndex.pl']))
    elif mutation=='observer':
        review=Path(d['review_receipt']['path']);v=json.loads(review.read_text());v['observer_sha256']='2'*64;write_json(review,v);d['review_receipt']=file_record(review);write_json(c['runtime'],d)
    elif mutation=='unreviewed':
        review=Path(d['review_receipt']['path']);v=json.loads(review.read_text());v['state']='UNKNOWN';write_json(review,v);d['review_receipt']=file_record(review);write_json(c['runtime'],d)
    elif mutation=='resources': refresh_runtime(c,lambda x:x['identity']['resources'].update(source_reviewed=False))
    elif mutation=='native_source':
        # A fake entry cannot become pinned original native merely by a label.
        d['kind']='NATIVE';review=Path(d['review_receipt']['path']);v=json.loads(review.read_text());v['intent']='NATIVE';write_json(review,v);d['review_receipt']=file_record(review);write_json(c['runtime'],d)
    else:
        bad=c['root']/'unsafe path.py';bad.write_text('pass\n')
        refresh_runtime(c,lambda x:x['identity'].update(interpreter=file_record(bad)))
    with pytest.raises(A.AdapterError): A.plan_command(plan_args(c))
    assert not (c['root']/'plan').exists()


@pytest.mark.parametrize('route,goal,genes,sites',[
 ('MULTILOCUS_CORE','MET_STRUCTURAL_ONLY',2,[3,2]),
 ('QUERY_ONLY_SHAVED','NOT_MET',1,[2]),
 ('QUERY_ONLY_UNSHAVED','NOT_MET',1,[4]),
 ('BLAST_ORDER','NOT_MET',1,[])])
def test_actual_fake_child_routes_keep_goal_and_full_identity(case,route,goal,genes,sites):
    c=case(mode=route);before={p:sha(p.read_bytes()) for p in [c['intake'],c['selection'],c['runtime']]}
    state,result=completed(c)
    assert result['route']==route and result['multilocus_goal']==goal
    assert result['core_genes']==genes and result['core_alignment_lengths']==sites
    assert result['release']=='PRIVATE' and result['scope']=='SYNTHETIC_PROTOCOL_ONLY'
    assert result['denominators']['converted_genes']==6
    assert result['denominators']['prefilter_neighborhoods']==2
    assert {r['exact_locus'] for r in result['loci']}==set(c['identities'])
    assert all(' / CP00000' in r['exact_locus'] and ' / region001 / BGC001' in r['exact_locus'] for r in result['loci'])
    assert result['denominators']['tree_tips']==(0 if route=='BLAST_ORDER' else 2)
    if route=='MULTILOCUS_CORE': assert result['core_partition_order']==['2','1']
    assert {p:sha(p.read_bytes()) for p in before}==before
    export=A.read_command(SimpleNamespace(run_receipt=c['root']/'attempt'/'RUN_STATE.json',out=c['root']/'read',write_root=c['root'],read_only_root=[]))
    assert export['route']==route and (c['root']/'read'/'loci.tsv').is_file()
    assert 'Foo / CP000001.1 / region001 / BGC001' in (c['root']/'read'/'HANDOFF.md').read_text()


@pytest.mark.parametrize('mode', ['CONVERT_DROP','NO_CAPTURE','SVG_ONLY','WRONG_CORE','FOREIGN_LEAF','BAD_CONCAT','MISSING_TREE','FILTER_FAIL'])
def test_zero_exit_partial_or_failed_child_is_not_completion(case,mode):
    c=case(mode=mode);p=planned(c)
    with pytest.raises((A.AdapterError,OSError,ValueError)): A.run_command(run_args(c,p))
    state=json.loads((c['root']/'attempt'/'RUN_STATE.json').read_text())
    assert state['status']=='FAILED' and state['input_runtime_immutable'] is True
    assert not (c['root']/'attempt'/'SELECTED_RESULT.json').exists()
    assert (c['root']/'attempt'/'logs'/'convert.log').is_file()
    if mode=='CONVERT_DROP': assert len(state['phases'])==1
    else: assert len(state['phases'])==2
    with pytest.raises(A.AdapterError): A.read_command(SimpleNamespace(run_receipt=c['root']/'attempt'/'RUN_STATE.json',out=c['root']/'read',write_root=c['root'],read_only_root=[]))
    assert not (c['root']/'read').exists()


def test_real_prefilter_capture_preserves_filtered_neighborhood(case):
    c=case(mode='FILTER',strains=('Foo','foo','Third'),contigs=('CP000001.1','CP000002.1','CP000003.1'))
    state,result=completed(c)
    assert result['denominators']['prefilter_neighborhoods']==3
    assert result['denominators']['admitted_neighborhoods']==2
    assert result['denominators']['filtered_neighborhoods']==1
    assert sum(x['state']=='NATIVE_FILTERED' for x in result['neighborhoods'])==1
    assert sum(x['state']=='NATIVE_FILTERED_ALL' for x in result['loci'])==1
    qa=c['root']/'attempt'/'qa'
    assert len(list(qa.glob('prefilter_*.input')))==3
    capture=json.loads((qa/'PREFILTER.json').read_text())
    assert all(Path(v['capture']).is_file() for v in capture['files'].values())


def test_multiple_hits_remain_three_neighborhoods_two_loci(case):
    c=case(mode='MULTIPLE_HITS');_,r=completed(c)
    assert r['denominators']['staged_loci']==2 and r['denominators']['prefilter_neighborhoods']==3
    assert r['denominators']['tree_tips']==3
    assert len({x['exact_locus'] for x in r['leaf_crosswalk']})==2
    assert len({x['raw_tip'] for x in r['leaf_crosswalk']})==3


def test_affirmative_no_hit_denominator_is_not_missing_output(case):
    c=case(mode='NO_HIT',strains=('Foo','foo','Third'),contigs=('CP000001.1','CP000002.1','CP000003.1'))
    _,r=completed(c)
    assert r['denominators']['query_hit_loci']==2 and r['denominators']['staged_loci']==3
    assert sum(x['state']=='NO_QUERY_HIT_IN_BOUND_SEARCH' for x in r['loci'])==1


@pytest.mark.parametrize('which',['source','output','producer','capture','converted','method','phase'])
def test_read_requires_exact_producer_and_original_artifact_bytes(case,which):
    c=case();state,r=completed(c);root=c['root']/'attempt'
    if which=='source':
        record=json.loads(c['intake'].read_text())['records'][0];Path(record['source_zip']).write_bytes(b'changed')
    elif which=='output':
        work=Path(state['work_path']);(work/'query.faa-output'/'query.faa.svg').write_text('<svg>changed</svg>')
    elif which=='producer': (root/'RUN_MANIFEST.json').write_text('{}\n')
    elif which=='capture': next((root/'qa').glob('prefilter_*.input')).write_text('changed\n')
    elif which=='converted': next((Path(state['work_path'])/'GENOMES').glob('*.faa')).write_text('>fake\nX\n')
    elif which=='method':
        # Do not mutate distributed source: replace recorded method binding and
        # recompute caller-owned outer receipts to prove the inner binding check.
        manifest=json.loads((root/'RUN_MANIFEST.json').read_text());p=c['root']/'method.py';p.write_text('pass\n')
        manifest['method']=file_record(p);manifest['method']['sha256']='0'*64
        write_json(root/'RUN_MANIFEST.json',manifest)
        r['producer']=file_record(root/'RUN_MANIFEST.json');write_json(root/'SELECTED_RESULT.json',r)
        state['manifest']=file_record(root/'RUN_MANIFEST.json');state['result']=file_record(root/'SELECTED_RESULT.json');write_json(root/'RUN_STATE.json',state)
    else:
        state['phases'][1]['cwd']='wrong';write_json(root/'RUN_STATE.json',state)
    with pytest.raises((A.AdapterError,OSError,ValueError)): A.read_command(SimpleNamespace(run_receipt=root/'RUN_STATE.json',out=c['root']/'read',write_root=c['root'],read_only_root=[]))
    if (c['root']/'read').exists():
        assert json.loads((c['root']/'read'/'WORKER_STATE.json').read_text())['status']=='FAILED'
        assert not (c['root']/'read'/'WHOLE_WORKER_ADMISSION.json').exists()


def test_occupied_rerun_cannot_replace_old_success(case):
    c=case();state,r=completed(c);old=(c['root']/'attempt'/'SELECTED_RESULT.json').read_bytes()
    with pytest.raises(A.AdapterError): A.run_command(run_args(c,c['root']/'plan'/'PLAN.json'))
    assert (c['root']/'attempt'/'SELECTED_RESULT.json').read_bytes()==old
    assert json.loads((c['root']/'attempt'/'RUN_STATE.json').read_text())['status']=='COMPLETE_SCOPED_EVIDENCE'


def test_forged_plan_selection_cannot_bypass_bound_intake(case):
    c=case();p=planned(c);d=json.loads(p.read_text());d['selected_loci'][0]['full_contig']='FOREIGN';write_json(p,d)
    with pytest.raises(A.AdapterError,match='PLAN_SELECTION_DERIVATION'): A.run_command(run_args(c,p))
    state=json.loads((c['root']/'attempt'/'RUN_STATE.json').read_text())
    assert state['status']=='FAILED' and state['error']=='PLAN_SELECTION_DERIVATION'
    assert not (c['root']/'attempt'/'WHOLE_WORKER_ADMISSION.json').exists()
    assert not list(c['workroot'].iterdir())


def test_approval_required_before_any_attempt(case):
    c=case();p=planned(c);args=run_args(c,p);args.approved=False
    with pytest.raises(A.AdapterError,match='APPROVAL_REQUIRED'): A.run_command(args)
    assert not (c['root']/'attempt').exists()


def test_compound_location_refused_and_terminal_stop_transform_recorded(case):
    c=case(compound=True);p=planned(c)
    with pytest.raises(A.AdapterError,match='CDS_LOCATION_UNSUPPORTED'): A.run_command(run_args(c,p))
    assert json.loads((c['root']/'attempt'/'RUN_STATE.json').read_text())['status']=='FAILED'
    d=case(stop=True);_,r=completed(d)
    manifest=json.loads((d['root']/'attempt'/'RUN_MANIFEST.json').read_text())
    assert sum(g['transformation']=='REMOVE_ONE_TERMINAL_STOP' for g in manifest['gene_map'].values())==2


def test_ambiguous_partition_order_does_not_invent_readdir_order():
    with pytest.raises(A.AdapterError,match='ORDER_AMBIGUOUS'):
        A.unique_partition_order({'1':{'T':'XX'},'2':{'T':'XX'}},{'T':'XXXX'})
    assert A.unique_partition_order({'1':{'T':'XX'},'2':{'T':'X-X'}},{'T':'X-XXX'})==['2','1']


@pytest.mark.parametrize('key', ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS',
    'NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS','OMP_THREAD_LIMIT','PYTHONDONTWRITEBYTECODE'])
def test_missing_or_unbounded_thread_environment_is_not_admitted(case,key):
    c=case()
    refresh_runtime(c,lambda x:x['identity']['environment'].update({key:'2'}))
    with pytest.raises(A.AdapterError,match='THREAD_ENVIRONMENT_HOLD'):
        A.plan_command(plan_args(c))
    assert not (c['root']/'plan').exists()


@pytest.mark.parametrize('observed', [10, None, 0])
def test_native_twelve_thread_profile_refuses_insufficient_host_observation(monkeypatch, observed):
    monkeypatch.setattr(A.os,'cpu_count',lambda:observed)
    with pytest.raises(A.AdapterError,match='HOST_CPU_BUDGET_HOLD'):
        A.native_cpu_budget(12)


def test_native_cpu_budget_has_no_oversubscription_bypass(monkeypatch):
    monkeypatch.setattr(A.os,'cpu_count',lambda:12)
    assert A.native_cpu_budget(12)==12
    with pytest.raises(A.AdapterError,match='HOST_CPU_BUDGET_HOLD'):
        A.native_cpu_budget(13)


def test_outer_worker_owns_python_staging_and_native_children(case,monkeypatch):
    c=case();p=planned(c);observed={}
    def watched(command,**options):
        observed.update(command=command,options=options)
        return {'exit_code':None,'stop_reason':'MEMORY_LIMIT','cleanup_error':None}
    monkeypatch.setattr(A,'run_watched',watched)
    with pytest.raises(A.AdapterError,match='WHOLE_WORKER_FAILED'):
        A.run_command(run_args(c,p))
    command=observed['command'];options=observed['options']
    assert command[2]=='--_worker' and command[1]==str(TOOLS/'corason_adapter.py')
    assert options['timeout']==1800 and options['rss_limit']==3800000000
    assert options['min_disk']==2000000000
    assert options['additional_disk_floors']==((c['workroot'],2000000000),)
    assert all(options['env'][k]=='1' for k in A.THREAD_ENV_KEYS)
    assert options['env']['PYTHONDONTWRITEBYTECODE']=='1'
    request=json.loads((c['root']/'attempt'/'WORKER_REQUEST.json').read_text())
    assert request['mode']=='run' and request['arguments']['approved'] is True
    assert request['method']['sha256']==sha((TOOLS/'corason_adapter.py').read_bytes())
    assert not list(c['workroot'].iterdir())  # No worker ever launched.
    assert json.loads((c['root']/'attempt'/'RUN_STATE.json').read_text())['status']=='FAILED'
    assert not (c['root']/'attempt'/'WHOLE_WORKER_ADMISSION.json').exists()


def test_whole_worker_receipt_is_required_and_bound_for_read(case):
    c=case();state,_=completed(c);root=c['root']/'attempt'
    admission=json.loads((root/'WHOLE_WORKER_ADMISSION.json').read_text())
    receipt=json.loads((root/'WHOLE_WORKER_RECEIPT.json').read_text())
    assert admission['terminal']==file_record(root/'RUN_STATE.json')
    assert receipt['exit_code']==0 and receipt['stop_reason'] is None
    assert {x['path'] for x in receipt['disk_floors']}=={str(root),str(c['workroot'])}
    assert all(x['monitor']=='OUTER_WORKER_PROCESS_TREE' for x in state['phases'])
    assert all(x['argv'][0] != 'nice' for x in state['phases'])
    (root/'WHOLE_WORKER_ADMISSION.json').unlink()
    with pytest.raises(A.AdapterError,match='METADATA_LIMIT_OR_MISSING'):
        A.read_command(SimpleNamespace(run_receipt=root/'RUN_STATE.json',out=c['root']/'read',write_root=c['root'],read_only_root=[]))
    assert not (c['root']/'read').exists()



def test_human_tsv_is_formula_safe_without_changing_canonical_identity(case):
    import csv
    c=case(strains=('=1+1','@formula'));_,result=completed(c)
    exported=A.read_command(SimpleNamespace(run_receipt=c['root']/'attempt'/'RUN_STATE.json',
        out=c['root']/'read',write_root=c['root'],read_only_root=[]))
    expected={'=1+1 / CP000001.1 / region001 / BGC001','@formula / CP000002.1 / region001 / BGC001'}
    assert {x['exact_locus'] for x in exported['loci']}==expected
    payload=json.loads((c['root']/'read'/'EVIDENCE.json').read_text())
    assert {x['exact_locus'] for x in payload['loci']}==expected
    with (c['root']/'read'/'loci.tsv').open(newline='') as stream:
        rows=list(csv.DictReader(stream,delimiter='\t'))
    assert {x['exact_locus'] for x in rows}=={"'"+x for x in expected}
    assert len(rows)==2


@pytest.mark.parametrize('root_value', [None, '', 7, 'missing-directory'])
def test_native_source_root_is_a_typed_admission_refusal(case, root_value):
    c = case()
    def mutate(data):
        data['kind'] = 'NATIVE'
        if root_value is not None:
            data['identity']['source_root'] = (str(c['root']/'missing-directory')
                if root_value == 'missing-directory' else root_value)
    refresh_runtime(c, mutate)
    data = json.loads(c['runtime'].read_text())
    review_path = Path(data['review_receipt']['path'])
    review = json.loads(review_path.read_text()); review['intent'] = 'NATIVE'
    write_json(review_path, review)
    data['review_receipt'] = file_record(review_path); write_json(c['runtime'], data)
    with pytest.raises(A.AdapterError, match='NATIVE_SOURCE_ROOT'):
        A.plan_command(plan_args(c))
    assert not (c['root']/'plan').exists()
    assert not list(c['workroot'].iterdir())


@pytest.mark.parametrize('worker_failure', [False, True])
def test_private_worker_accepts_authenticated_argv_string_and_records_failure(tmp_path, monkeypatch, worker_failure):
    # Independently constructed coordination metadata, not a producer golden.
    out = tmp_path/'worker'; out.mkdir()
    plan_path = write_json(tmp_path/'plan.json', {'test_scope':'coordination-only'})
    request_path = write_json(out/'WORKER_REQUEST.json', {
        'schema':'corason.worker-request.v1', 'mode':'run', 'method':file_record(Path(A.__file__)),
        'plan':file_record(plan_path), 'arguments':{'out':str(out),'approved':True}})
    request_sha = sha(request_path.read_bytes())
    monkeypatch.chdir(out)
    monkeypatch.setenv('CORASON_WORKER_REQUEST_SHA256', request_sha)
    for key in (*A.THREAD_ENV_KEYS, 'PYTHONDONTWRITEBYTECODE'):
        monkeypatch.setenv(key, '1')
    observed = []
    def worker(args):
        observed.append(vars(args))
        if worker_failure:
            raise A.AdapterError('INDEPENDENT_WORKER_FAILURE')
    monkeypatch.setattr(A, '_run_worker', worker)
    if worker_failure:
        with pytest.raises(A.AdapterError, match='INDEPENDENT_WORKER_FAILURE'):
            A.private_worker(str(request_path), request_sha)
        assert json.loads((out/'WORKER_ERROR.json').read_text()) == {'error':'INDEPENDENT_WORKER_FAILURE'}
    else:
        assert A.private_worker(str(request_path), request_sha) == 0
        assert not (out/'WORKER_ERROR.json').exists()
    assert observed == [{'out':str(out),'approved':True}]


def test_private_worker_rejects_wrong_argv_string_digest_before_dispatch(tmp_path, monkeypatch):
    out = tmp_path/'worker'; out.mkdir()
    request_path = write_json(out/'WORKER_REQUEST.json', {'schema':'corason.worker-request.v1'})
    monkeypatch.chdir(out)
    monkeypatch.setenv('CORASON_WORKER_REQUEST_SHA256', '0'*64)
    def forbidden(args):
        raise AssertionError('untrusted request reached worker')
    monkeypatch.setattr(A, '_run_worker', forbidden)
    with pytest.raises(A.AdapterError, match='WORKER_REQUEST_CHANNEL'):
        A.private_worker(str(request_path), '0'*64)
    assert not (out/'WORKER_ERROR.json').exists()
    assert not (out/'RUN_STATE.json').exists()


def test_region_translation_missing_rich_parser_refuses_before_reading_input(monkeypatch):
    import builtins
    original = builtins.__import__
    blocked = []
    def unavailable(name, *args, **kwargs):
        if name == 'Bio':
            blocked.append(name)
            raise ImportError('synthetic missing optional rich parser')
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', unavailable)
    with pytest.raises(RuntimeError, match='requires optional Biopython') as error:
        A.translated_region({}, b'not parsed: dependency admission comes first')
    assert blocked == ['Bio']
    assert isinstance(error.value.__cause__, ImportError)


def test_region_translation_present_parser_still_rejects_invalid_genbank():
    pytest.importorskip('Bio.SeqIO')
    with pytest.raises(A.AdapterError, match='REGION_RECORD_COUNT'):
        A.translated_region({}, b'')
