"""Explicit source/stage/environment registry binding on tiny fabricated metadata."""
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture
def api(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT/'tools'))
    return importlib.import_module('release_workflow')


@pytest.fixture
def selected(api,tmp_path):
    root=tmp_path/'source';tools=root/'tools';tools.mkdir(parents=True)
    for name in ['verify_export_registry.py','synthetic_id_registry_guard.py']:
        shutil.copyfile(ROOT/'tools'/name,tools/name)
    (tools/'test_synthetic_ids.txt').write_text('AS'+'-'+str(8*100)+'\n')
    registry=tmp_path/'explicit_synthetic_registry.tsv'
    registry.write_text('strain_id\n'+'AS'+'-'+str(8*10)+'\n')
    (tools/'sync_version.py').write_text('RULES = {}\n')
    (tools/'sync_wiki_mirrors.py').write_text('MIRRORS = {}\n')
    args=SimpleNamespace(synthetic_registry=registry,synthetic_registry_sha256=sha(registry),
        synthetic_guard_sha256=sha(tools/'synthetic_id_registry_guard.py'),
        synthetic_allowlist_sha256=sha(tools/'test_synthetic_ids.txt'))
    return root,registry,args


@pytest.mark.parametrize('field',['registry','registry_sha256','guard_sha256','allowlist_sha256'])
def test_missing_explicit_selection_is_typed_hold_without_locator(api,selected,field):
    root,registry,args=selected;setattr(args,'synthetic_'+field,None)
    with pytest.raises(api.RegistryRefused) as caught:api.registry_selection(root,args)
    assert caught.value.code==2 and caught.value.state=='HOLD'
    assert str(registry) not in str(caught.value)


@pytest.mark.parametrize('field',['guard_sha256','allowlist_sha256'])
def test_changed_selected_source_refuses_before_owner_execution(api,selected,field):
    root,_,args=selected;setattr(args,'synthetic_'+field,'0'*64)
    with pytest.raises(api.RegistryRefused,match='digest mismatch'):api.registry_selection(root,args)


@pytest.mark.parametrize('collision,code',[(False,0),(True,1)])
def test_actual_owner_cli_preserves_typed_code_and_redacted_snapshot_scope(api,selected,capsys,collision,code):
    root,registry,args=selected
    if collision:
        registry.write_text('strain_id\n'+'AS'+'-'+str(8*100)+'\n');args.synthetic_registry_sha256=sha(registry)
    binding=api.registry_selection(root,args)
    assert api.main(['_registry','--source',str(root),*api.registry_options(binding)])==code
    captured=capsys.readouterr();assert captured.out==''
    record=json.loads(captured.err)
    assert record['state']==('FAIL' if collision else 'PASS_BOUND_SNAPSHOT')
    assert record['fixture_role_clearance']==record['source_disclosure_clearance']=='HOLD'
    assert str(registry) not in captured.err
    assert ('AS'+'-'+str(8*100)) not in captured.err
    assert record['source_tree_sha256']==api.partitions.source_digest(root)


def test_all_declared_phases_forward_selection_and_context_without_raw_locator(api,selected):
    root,registry,args=selected;binding=api.registry_selection(root,args)
    stages=api.plan(root,'8.8.8','20261017','a',1,binding)
    assert stages[0].name=='registry-preflight'
    for stage in stages:
        for flag,value in zip(api.registry_options(binding)[::2],api.registry_options(binding)[1::2]):
            assert stage.argv[stage.argv.index(flag)+1]==value
    context=api.cut_context('8.8.8','20261017','a',1,binding)
    assert str(registry) not in json.dumps(context)
    assert context['registry_selection']['guard_sha256']==args.synthetic_guard_sha256
    assert context['registry_selection']['fixture_role_clearance']=='HOLD'


def test_extracted_stage_is_bound_to_original_helper_guard_list_and_its_own_environment(api,selected,tmp_path):
    root,_,args=selected;binding=api.registry_selection(root,args);stage=tmp_path/'extracted-code'
    (stage/'tools').mkdir(parents=True)
    for name in ['verify_export_registry.py','synthetic_id_registry_guard.py','test_synthetic_ids.txt']:
        shutil.copyfile(root/'tools'/name,stage/'tools'/name)
    source_record,_=api.registry_preflight(root,binding,sys.executable)
    stage_record,code=api.registry_preflight(stage,binding,sys.executable)
    assert code==0 and stage_record['source_tree_sha256']==api.partitions.source_digest(stage)
    assert stage_record['source_tree_sha256']!=source_record['source_tree_sha256']
    assert stage_record['environment_sha256']!=source_record['environment_sha256']
    with (stage/'tools/synthetic_id_registry_guard.py').open('a') as stream:stream.write('\n# changed stage owner\n')
    with pytest.raises(api.RegistryRefused,match='source/stage'):api.registry_preflight(stage,binding,sys.executable)


def test_unknown_child_stderr_is_not_echoed_or_admitted(api,selected):
    root,registry,args=selected
    (root/'tools/verify_export_registry.py').write_text('import sys\nsys.stderr.write("PRIVATE_FIXTURE_MARKER")\n')
    binding=api.registry_selection(root,args)
    with pytest.raises(api.RegistryRefused) as caught:api.registry_preflight(root,binding,sys.executable)
    assert caught.value.code==2 and 'PRIVATE_FIXTURE_MARKER' not in str(caught.value)
    assert str(registry) not in str(caught.value)


def test_generic_workflow_external_inputs_pin_selected_registry(api,selected,tmp_path):
    root,registry,args=selected;binding=api.registry_selection(root,args)
    workflow=api.Workflow(root,tmp_path/'workflow',(api.Stage('never',('{PYTHON}','-c','pass')),),sys.executable,
        inputs=api.registry_inputs(binding),env=dict(os.environ),min_disk=0,timeout=3)
    workflow.check_inputs();registry.write_text('changed explicitly selected metadata\n')
    with pytest.raises(ValueError,match='external workflow input changed'):workflow.check_inputs()


def test_owner_that_changes_source_cannot_return_a_green_admission(api,selected):
    root,_,args=selected;values={name:getattr(args,'synthetic_'+name) for name in ['registry_sha256','guard_sha256','allowlist_sha256']}
    payload={'schema':'sapote.export-registry-preflight.v1','state':'PASS_BOUND_SNAPSHOT','collision_count':0,**values}
    (root/'tools/verify_export_registry.py').write_text('from pathlib import Path\nimport json,sys\nPath("changed.txt").write_text("concurrent source change")\nsys.stderr.write(json.dumps('+repr(payload)+'))\n')
    binding=api.registry_selection(root,args)
    with pytest.raises(api.RegistryRefused,match='changed during admission'):api.registry_preflight(root,binding,sys.executable)



def test_not_requested_diagnostic_touches_no_metadata_or_owner(api, tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('unrequested diagnostic touched an owner, runtime or source')
    monkeypatch.setattr(api, 'selected_interpreter', forbidden)
    monkeypatch.setattr(api.partitions, 'source_digest', forbidden)
    monkeypatch.setattr(api.support, 'sha256_file', forbidden)
    monkeypatch.setattr(api.subprocess, 'run', forbidden)
    source = tmp_path/'no-source-or-registry'
    selected = api.registry_selection(source, SimpleNamespace())
    assert selected is None
    assert api.registry_options(selected) == api.registry_inputs(selected) == ()
    record, code = api.registry_preflight(source, selected, 'not-an-interpreter')
    assert code == 0 and record['state'] == 'NOT_REQUESTED'
    assert record['diagnostic_status'] == 'NOT_RUN'
    assert record['selected_hashes_verified'] is False
    assert record['fixture_role_clearance'] == record['source_disclosure_clearance'] == 'NOT_EVALUATED'
    assert not source.exists()


@pytest.mark.parametrize('mask', range(1, 15))
def test_every_partial_option_set_remains_a_typed_hold(api, tmp_path, mask):
    fields = ('registry', 'registry_sha256', 'guard_sha256', 'allowlist_sha256')
    args = SimpleNamespace(**{'synthetic_'+field: 'explicit' if mask & (1 << i) else None
                              for i, field in enumerate(fields)})
    with pytest.raises(api.RegistryRefused, match='all four') as caught:
        api.registry_selection(tmp_path/'absent-source', args)
    assert caught.value.code == 2 and caught.value.state == 'HOLD'


@pytest.mark.parametrize('field', ['registry', 'registry_sha256', 'guard_sha256', 'allowlist_sha256'])
def test_empty_explicit_option_is_not_treated_as_unrequested(api, tmp_path, field):
    with pytest.raises(api.RegistryRefused) as caught:
        api.registry_selection(tmp_path, SimpleNamespace(**{'synthetic_'+field: ''}))
    assert caught.value.code == 2


@pytest.mark.parametrize('field', ['registry_sha256', 'guard_sha256', 'allowlist_sha256'])
def test_requested_malformed_pin_is_still_redacted_hold(api, selected, field):
    source, registry, args = selected
    setattr(args, 'synthetic_'+field, 'invalid')
    with pytest.raises(api.RegistryRefused) as caught:
        api.registry_selection(source, args)
    assert caught.value.code == 2 and str(registry) not in str(caught.value)


def test_unrequested_plan_binds_state_and_forwards_no_registry_flags(api, selected):
    source, _, _ = selected
    stages = api.plan(source, '8.8.8', '20261017', 'a', 2)
    assert all(not any(arg.startswith('--synthetic-') for arg in stage.argv) for stage in stages)
    context = api.cut_context('8.8.8', '20261017', 'a', 2)
    assert context['registry_selection']['state'] == 'NOT_REQUESTED'
    assert context['registry_selection']['diagnostic_status'] == 'NOT_RUN'
    assert api.registry_inputs(None) == ()


@pytest.mark.parametrize('was_selected', [False, True])
def test_resume_cannot_switch_registry_selection_before_any_admission(api, selected, tmp_path, monkeypatch, was_selected):
    source, _, args = selected
    bound = api.registry_selection(source, args)
    previous, current = (bound, None) if was_selected else (None, bound)
    output = tmp_path/'workflow'
    def instance(binding):
        return api.Workflow(source, output, api.plan(source, '8.8.8', '20261017', 'a', 2, binding),
            sys.executable, inputs=api.registry_inputs(binding), env=dict(os.environ),
            context=api.cut_context('8.8.8', '20261017', 'a', 2, binding))
    original = instance(previous)
    output.mkdir()
    # Deliberately authored initial record; no environment or stage claims.
    record = {'schema': 'sapote-mamey.release-stages.v1', 'status': 'ADMITTING',
        'definition_sha256': original.definition_sha256, 'context': original.context,
        'committed_source_sha256': api.partitions.source_digest(source),
        'stages': [{'name': s.name, 'status': 'PENDING', 'attempts': []} for s in original.stages]}
    (output/'workflow.json').write_text(json.dumps(record))
    def forbidden(*args, **kwargs):
        raise AssertionError('selection transition reached environment admission')
    monkeypatch.setattr(api.support, 'admit_environment', forbidden)
    with pytest.raises(ValueError, match='definition or schema changed'):
        instance(current).run(resume=True)
    after = json.loads((output/'workflow.json').read_text())
    assert after['status'] == 'REFUSED_RESUME'
    assert all(not stage['attempts'] for stage in after['stages'])


@pytest.mark.parametrize('was_selected', [False, True])
def test_independent_verify_cannot_switch_registry_selection(api, selected, tmp_path, monkeypatch, was_selected):
    source, _, args = selected
    binding = api.registry_selection(source, args)
    previous, current = (binding, None) if was_selected else (None, binding)
    output = tmp_path/'output'; output.mkdir()
    record = output/'workflow.json'
    record.write_text(json.dumps({'context': api.cut_context('8.8.8', '20261017', 'a', 2, previous)}))
    before = record.read_bytes()
    def forbidden(*args, **kwargs):
        raise AssertionError('selection transition reached owner or workflow execution')
    monkeypatch.setattr(api, 'require_registry_preflight', forbidden)
    parsed = api.parse_args(['verify', '--source', str(source), '--out', str(output),
        '--sha256', sha(record), '--admission', str(tmp_path/'admission'), *api.registry_options(current)])
    events = list(api.command_events(parsed))
    assert events[-1].code == 2 and 'workflow selection differs' in events[-1].text
    assert record.read_bytes() == before and not (tmp_path/'admission').exists()


@pytest.mark.parametrize('mode, code', [('none', 0), ('partial', 2), ('bad-pin', 2),
                                     ('clean', 0), ('collision', 1), ('drift', 2)])
def test_direct_tier_declaration_prefix_preserves_optional_and_strict_modes(api, selected, tmp_path, mode, code):
    source, registry, args = selected
    (source/'tools/cut_preflight.sh').write_text('sapote_assert_no_review_root(){ :; }\n')
    if mode == 'collision':
        registry.write_text('strain_id\n'+'AS'+'-'+str(8*100)+'\n')
        args.synthetic_registry_sha256 = sha(registry)
    options = api.registry_options(api.registry_selection(source, args))
    if mode == 'none':
        options = ()
        for name in ('verify_export_registry.py', 'synthetic_id_registry_guard.py', 'test_synthetic_ids.txt'):
            (source/'tools'/name).unlink()  # Newly authored fixture only: prove helpers are not required.
        registry.unlink()
    elif mode == 'partial':
        options = options[:2]
    elif mode == 'bad-pin':
        options = options[:3]+('0'*64,)+options[4:]
    elif mode == 'drift':
        registry.write_text('strain_id\nchanged fabricated metadata\n')
    text = (ROOT/'tools/make_public_tier.sh').read_text()
    prefix = text.split('# END EXPLICIT SYNTHETIC REGISTRY PREFLIGHT', 1)[0]
    harness = tmp_path/'tier-prefix.sh'; harness.write_text(prefix)
    import subprocess
    out = tmp_path/'not-staged'
    result = subprocess.run(['bash', str(harness), 'code', str(source), str(out), *options],
        env=dict(os.environ, PYTHON=sys.executable), text=True, capture_output=True, timeout=15)
    assert result.returncode == code, result.stdout+result.stderr
    assert result.stdout == '' and not out.exists()
    record = json.loads(result.stderr)
    assert record['state'] == ('NOT_REQUESTED' if mode == 'none' else 'PASS_BOUND_SNAPSHOT' if mode == 'clean' else 'FAIL' if mode == 'collision' else 'HOLD')
    assert str(registry) not in result.stderr
    if mode == 'none':
        assert record['diagnostic_status'] == 'NOT_RUN'
        assert record['fixture_role_clearance'] == 'NOT_EVALUATED'
        assert record['selected_hashes_verified'] is False


@pytest.mark.parametrize('requested', [False, True])
def test_monolithic_parser_forwards_absent_or_exact_selection(api, selected, tmp_path, requested):
    source, _, args = selected
    shutil.copyfile(ROOT/'tools/release_workflow.py', source/'tools/release_workflow.py')
    options = api.registry_options(api.registry_selection(source, args)) if requested else ()
    text = (ROOT/'tools/release_cut.sh').read_text().split('\nPHASE=', 1)[0]
    harness = tmp_path/'cut-prefix.sh'
    full_text = (ROOT/'tools/release_cut.sh').read_text()
    preflight = full_text[full_text.index('registry_preflight(){'):full_text.index('\nprepare_release(){')]
    harness.write_text(text+'\nrecord(){ printf "registry_arguments=%s\\n" "$#"; }; record ${REGISTRY_ARGS[@]+"${REGISTRY_ARGS[@]}"}\n'+preflight+'\nregistry_preflight\n')
    import subprocess
    env = {k: v for k, v in os.environ.items() if not k.startswith('RELEASE_')}
    env['PYTHON'] = sys.executable; env.pop('PYTEST_ADDOPTS', None)
    env['PYTHONPATH'] = os.pathsep.join([str(Path(api.__file__).parent),
        str(Path(api.support.__file__).parent), env.get('PYTHONPATH', '')])
    out = tmp_path/'not-cut'
    result = subprocess.run(['bash', str(harness), '8.8.8', str(source), str(out), *options],
                            cwd=(ROOT/'tools/release_workflow.py').parent.parent,
                            env=env, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert 'registry_arguments='+('8' if requested else '0') in result.stdout
    assert json.loads(result.stderr)['state'] == ('PASS_BOUND_SNAPSHOT' if requested else 'NOT_REQUESTED')
    assert not out.exists()


def test_standalone_diagnostic_still_holds_without_explicit_metadata(api, selected):
    source, _, _ = selected
    import subprocess
    result = subprocess.run([sys.executable, '-B', str(source/'tools/verify_export_registry.py'),
                             '--root', str(source)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 2 and result.stdout == ''
    assert json.loads(result.stderr)['state'] == 'HOLD'


@pytest.mark.parametrize('legacy', [None, {'state': 'HOLD_UNBOUND', 'fixture_role_clearance': 'HOLD'}])
def test_ambiguous_legacy_selection_is_not_equivalent_to_not_requested(api, selected, tmp_path, legacy):
    source, _, _ = selected
    out = tmp_path/'legacy'; out.mkdir()
    root = out/'workflow.json'
    root.write_text(json.dumps({'context': {'registry_selection': legacy}}))
    args = api.parse_args(['verify', '--source', str(source), '--out', str(out),
                          '--sha256', sha(root), '--admission', str(tmp_path/'not-admitted')])
    events = list(api.command_events(args))
    assert events[-1].code == 2 and 'legacy record is unbound' in events[-1].text
    assert not (tmp_path/'not-admitted').exists()


def test_not_requested_still_requires_independent_workflow_environment_admission(api, selected, tmp_path, monkeypatch):
    source, _, _ = selected
    calls = []
    def refuse(python, *, output, **kwargs):
        calls.append(python); output.mkdir(parents=True)
        report = {'status': 'REFUSED', 'reason': 'fabricated unavailable runtime', 'steps': []}
        (output/'environment.json').write_text(json.dumps(report))
        return report
    monkeypatch.setattr(api.support, 'admit_environment', refuse)
    out = tmp_path/'workflow'
    workflow = api.Workflow(source, out, api.plan(source, '8.8.8', '20261017', 'a', 2), sys.executable,
                            env=dict(os.environ), context=api.cut_context('8.8.8', '20261017', 'a', 2))
    with pytest.raises(ValueError, match='workflow environment refused'):
        workflow.run()
    record = json.loads((out/'workflow.json').read_text())
    assert len(calls) == 1 and record['status'] == 'REFUSED_ENVIRONMENT'
    assert record['context']['registry_selection']['state'] == 'NOT_REQUESTED'
    assert all(not s['attempts'] for s in record['stages'])


@pytest.mark.parametrize('legacy_root', [{}, {'context': None}, []])
def test_missing_legacy_context_is_typed_hold_before_execution(api, selected, tmp_path, legacy_root):
    source, _, _ = selected
    out = tmp_path/'legacy'; out.mkdir()
    root = out/'workflow.json'; root.write_text(json.dumps(legacy_root))
    args = api.parse_args(['verify', '--source', str(source), '--out', str(out),
                          '--sha256', sha(root), '--admission', str(tmp_path/'not-admitted')])
    events = list(api.command_events(args))
    assert events[-1].code == 2 and 'legacy record is unbound' in events[-1].text
    assert not (tmp_path/'not-admitted').exists()


def test_actual_unrequested_diagnostic_cli_reports_not_run(api, tmp_path, capsys):
    source = tmp_path/'empty-source'; source.mkdir()
    assert api.main(['_registry', '--source', str(source)]) == 0
    captured = capsys.readouterr()
    assert captured.out == ''
    record = json.loads(captured.err)
    assert record['state'] == 'NOT_REQUESTED' and record['diagnostic_status'] == 'NOT_RUN'
    assert record['selected_hashes_verified'] is False
    assert not list(source.iterdir())
