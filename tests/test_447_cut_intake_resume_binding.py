"""Synthetic-only T10/T11 admission and actual-main resume controls; engine stubbed."""
import csv
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load():
    spec = importlib.util.spec_from_file_location('cut_intake', ROOT / 'tools/intake_harness.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def archive(path, members):
    with zipfile.ZipFile(path, 'w') as z:
        for name, text in members.items():
            z.writestr(name, text)
    return path


@pytest.mark.parametrize('paths', [
    ['left/region001.gbk', 'right/region002.gbk'],
    ['one/region001.gbk', 'one/nested/region002.gbk'],
])
def test_ambiguous_region_parents_refuse_without_input_package(tmp_path, paths):
    m = load()
    source = archive(tmp_path / 'synthetic.zip', {name: 'synthetic marker' for name in paths})
    stage = tmp_path / 'stage'
    with pytest.raises(m.AmbiguousRegionDirectories, match='AMBIGUOUS_REGION_DIRECTORIES'):
        m.detect_and_stage(source, stage, 'SYNTH')
    assert not (stage / 'SYNTH.input.zip').exists()


def test_one_parent_keeps_every_region_and_support_file(tmp_path):
    m = load()
    members = {'one/region002.gbk': 'second sentinel', 'one/region001.gbk': 'first sentinel',
               'one/clusterblast/control.txt': 'support sentinel'}
    source = archive(tmp_path / 'synthetic.zip', members)
    kind, staged, cb, org = m.detect_and_stage(source, tmp_path / 'stage', 'SYNTH')
    assert kind == 'ANTISMASH'
    with zipfile.ZipFile(staged) as z:
        assert {name: z.read(name).decode() for name in z.namelist()} == {
            name.removeprefix('one/'): value for name, value in members.items()}


def batch(tmp_path, monkeypatch):
    m = load()
    source = archive(tmp_path / 'SYNTH_SAMPLE.zip', {'one/region001.gbk': 'synthetic marker'})
    out = tmp_path / 'out'
    engine = {'root': 'synthetic engine', 'version': m._BUNDLE_ENGINE_VERSION, 'code_sha256': 'code-A'}
    monkeypatch.setattr(m, '_engine_binding', lambda: dict(engine))
    calls = []
    def fake_engine(cmd, **kw):
        calls.append(cmd)
        name = cmd[cmd.index('--strain') + 1]
        destination = Path(cmd[cmd.index('--outdir') + 1]) / name / 'package'
        destination.mkdir(parents=True, exist_ok=True)
        (destination / 'manifest_short.json').write_text(json.dumps({'mamey_version': m._BUNDLE_ENGINE_VERSION}))
        (destination / 'synthetic_result.txt').write_text('output sentinel')
        return 0, .01, 1., '{"assembly_tier":"SYNTHETIC","raw_bgcs":1,"corrected_bgcs":1}'
    monkeypatch.setattr(m, 'run_monitored', fake_engine)
    monkeypatch.setattr(m, 'rescue_summary', lambda *a: {key: 0 for key in
        ['rescue_leads', 'rescue_HIGH', 'rescue_MODERATE', 'IDC_split_HIGH']})
    monkeypatch.setattr(m, 'cores_present', lambda *a: '')
    def run(resume=False, extra=(), new_out=None):
        target = new_out or out
        argv = ['intake_harness.py', '--inputs', str(source), '--outdir', str(target),
                '--registry', str(target / 'registry.csv'), '--metrics', str(target / 'metrics.csv')]
        if resume:
            argv.append('--resume')
        monkeypatch.setattr(sys, 'argv', argv + list(extra))
        return m.main()
    return m, source, out, engine, calls, run


def package(out):
    return out / 'SYNTH_SAMPLE' / 'package'


def receipt(out):
    return out / 'SYNTH_SAMPLE' / 'intake_completion_receipt.json'


def statuses(out):
    with (out / 'metrics.csv').open() as stream:
        return [row['status'] for row in csv.DictReader(stream)]


def test_actual_main_ambiguity_is_run_failed_not_engine_call(tmp_path, monkeypatch, capsys):
    m, source, out, engine, calls, run = batch(tmp_path, monkeypatch)
    archive(source, {'a/region001.gbk': 'one', 'b/region002.gbk': 'two'})
    assert run() == 1 and calls == [] and statuses(out) == ['RUN_FAILED']
    assert not (out / 'registry.csv').exists() and not package(out).exists()
    assert 'AMBIGUOUS_REGION_DIRECTORIES' in capsys.readouterr().out


def test_exact_successful_receipt_skips_without_checkpoint_rewrite(tmp_path, monkeypatch, capsys):
    m, source, out, engine, calls, run = batch(tmp_path, monkeypatch)
    assert run() == 0
    proof = json.loads(receipt(out).read_text())
    assert proof['status'] == 'OK' and proof['run']['input'] == m._file_binding(source)
    assert proof['output'] == m._tree_binding(package(out))
    before = {p: p.read_bytes() for p in [out / 'registry.csv', out / 'metrics.csv', receipt(out)]}
    assert run(resume=True) == 0 and len(calls) == 1
    assert {p: p.read_bytes() for p in before} == before
    assert 'verified completion receipt' in capsys.readouterr().out


@pytest.mark.parametrize('change', ['input', 'engine', 'output', 'missing_output', 'receipt_missing',
    'receipt_bad_json', 'receipt_schema', 'receipt_status', 'option_source', 'option_mode', 'option_release'])
def test_mismatched_or_unbound_success_holds_repeatedly_before_overwrite(tmp_path, monkeypatch, change):
    m, source, out, engine, calls, run = batch(tmp_path, monkeypatch)
    assert run() == 0
    extra = []
    if change == 'input':
        archive(source, {'one/region001.gbk': 'changed synthetic marker'})
    elif change == 'engine':
        engine['code_sha256'] = 'code-B'
    elif change == 'output':
        (package(out) / 'synthetic_result.txt').write_text('changed output')
    elif change == 'missing_output':
        (package(out) / 'synthetic_result.txt').unlink()
    elif change == 'receipt_missing':
        receipt(out).unlink()
    elif change == 'receipt_bad_json':
        receipt(out).write_text('{bad')
    elif change.startswith('receipt_'):
        data = json.loads(receipt(out).read_text())
        data['schema' if change == 'receipt_schema' else 'status'] = 'unknown'
        receipt(out).write_text(json.dumps(data))
    else:
        extra = ['--' + change.removeprefix('option_'), {'option_source': 'changed source',
                 'option_mode': 'standard', 'option_release': 'PRIVATE'}[change]]
    before = m._tree_binding(package(out))
    for repeat in range(2):
        assert run(resume=True, extra=extra) == 1
        assert len(calls) == 1 and m._tree_binding(package(out)) == before
    assert statuses(out)[-2:] == ['RUN_FAILED', 'RUN_FAILED']


def test_output_location_is_bound_even_when_entire_run_is_copied(tmp_path, monkeypatch):
    m, source, out, engine, calls, run = batch(tmp_path, monkeypatch)
    assert run() == 0
    other = tmp_path / 'copied_out'
    shutil.copytree(out, other)
    assert run(resume=True, new_out=other) == 1 and len(calls) == 1


def test_taxonomy_map_path_and_content_are_bound(tmp_path, monkeypatch):
    m, source, out, engine, calls, run = batch(tmp_path, monkeypatch)
    mapping = tmp_path / 'taxonomy.json'
    mapping.write_text(json.dumps({'SYNTH_SAMPLE': 'not verified'}))
    assert run(extra=['--taxonomy-map', str(mapping)]) == 0
    mapping.write_text(json.dumps({'SYNTH_SAMPLE': 'not verified', 'UNUSED': 'not verified'}))
    assert run(resume=True, extra=['--taxonomy-map', str(mapping)]) == 1 and len(calls) == 1


@pytest.mark.parametrize('legacy_tier', ['SYNTHETIC', '', None])
def test_legacy_unbound_success_never_skips_or_runs(tmp_path, monkeypatch, legacy_tier):
    m, source, out, engine, calls, run = batch(tmp_path, monkeypatch)
    out.mkdir()
    m.append_rows(str(out / 'registry.csv'), [{'strain': 'SYNTH_SAMPLE', 'assembly_tier': legacy_tier}])
    assert run(resume=True) == 1 and calls == [] and not package(out).exists()


def test_needs_antismash_is_retryable_when_same_name_input_changes(tmp_path, monkeypatch):
    m, source, out, engine, calls, run = batch(tmp_path, monkeypatch)
    archive(source, {'assembly.fasta': 'synthetic text without sequence'})
    assert run() == 0 and calls == [] and statuses(out) == ['NEEDS_ANTISMASH']
    assert not receipt(out).exists()
    archive(source, {'one/region001.gbk': 'synthetic marker'})
    assert run(resume=True) == 0 and len(calls) == 1
    assert statuses(out) == ['NEEDS_ANTISMASH', 'OK'] and receipt(out).exists()


def test_existing_unbound_package_remains_held_after_failed_hold_checkpoint(tmp_path, monkeypatch):
    m, source, out, engine, calls, run = batch(tmp_path, monkeypatch)
    package(out).mkdir(parents=True)
    (package(out) / 'unbound.txt').write_text('preserve')
    for repeat in range(2):
        assert run(resume=True) == 1 and calls == []
    assert (package(out) / 'unbound.txt').read_text() == 'preserve'


def test_output_symlink_cannot_bank_or_resume_success(tmp_path, monkeypatch):
    m, source, out, engine, calls, run = batch(tmp_path, monkeypatch)
    assert run() == 0
    (package(out) / 'alias.txt').symlink_to(package(out) / 'synthetic_result.txt')
    assert run(resume=True) == 1 and len(calls) == 1


def test_source_changed_during_engine_stub_cannot_bank_success(tmp_path, monkeypatch):
    m, source, out, engine, calls, run = batch(tmp_path, monkeypatch)
    original = m.run_monitored
    def changing(*a, **kw):
        result = original(*a, **kw)
        archive(source, {'one/region001.gbk': 'changed during run'})
        return result
    monkeypatch.setattr(m, 'run_monitored', changing)
    assert run() == 1 and statuses(out) == ['RUN_FAILED']
    assert not receipt(out).exists() and not (out / 'registry.csv').exists()


def test_real_engine_digest_binds_code_resources_and_launcher(tmp_path, monkeypatch):
    m = load()
    root = tmp_path / 'synthetic_bundle'
    tools = root / 'tools'
    tools.mkdir(parents=True)
    (root / 'mamey').mkdir()
    code = root / 'mamey' / 'synthetic.py'
    resource = root / 'mamey' / 'resource.json'
    launcher = root / 'mamey_run.py'
    for p in [code, resource, launcher, tools / '_wbio.py', tools / '_console.py']:
        p.write_text('synthetic original')
    monkeypatch.setattr(m, 'ROOT', str(root))
    monkeypatch.setattr(m, 'HERE', str(tools))
    previous = m._engine_binding()
    for p in [code, resource, launcher]:
        p.write_text('synthetic changed')
        current = m._engine_binding()
        assert current['code_sha256'] != previous['code_sha256']
        previous = current
    cache = root / 'mamey' / '__pycache__'
    cache.mkdir()
    (cache / 'ignored.pyc').write_bytes(b'synthetic ignored bytecode')
    assert m._engine_binding() == previous


def test_same_input_bytes_at_changed_resolved_source_path_do_not_skip(tmp_path, monkeypatch):
    m, source, out, engine, calls, run = batch(tmp_path, monkeypatch)
    assert run() == 0
    moved = tmp_path / 'other_source.zip'
    source.rename(moved)
    source.symlink_to(moved)
    assert run(resume=True) == 1 and len(calls) == 1


def test_success_receipt_follows_both_success_checkpoints(tmp_path, monkeypatch):
    m, source, out, engine, calls, run = batch(tmp_path, monkeypatch)
    original = m.append_rows
    checkpoints = []
    def checking(path, rows, *a, **kw):
        checkpoints.append(Path(path).name)
        assert not receipt(out).exists()
        return original(path, rows, *a, **kw)
    monkeypatch.setattr(m, 'append_rows', checking)
    assert run() == 0 and checkpoints == ['registry.csv', 'metrics.csv']
    assert receipt(out).exists()


def test_receipt_publication_error_is_failed_and_legacy_bank_stays_held(tmp_path, monkeypatch):
    m, source, out, engine, calls, run = batch(tmp_path, monkeypatch)
    original = m.atomic_open
    def refusing(path, *a, **kw):
        if Path(path).name == 'intake_completion_receipt.json':
            raise OSError('synthetic receipt publication failure')
        return original(path, *a, **kw)
    monkeypatch.setattr(m, 'atomic_open', refusing)
    assert run() == 1 and statuses(out) == ['OK', 'RUN_FAILED']
    assert not receipt(out).exists()
    assert run(resume=True) == 1 and len(calls) == 1


def test_engine_symlink_directory_is_explicit_binding_hold(tmp_path, monkeypatch):
    m = load()
    root = tmp_path / 'synthetic_bundle'
    (root / 'mamey').mkdir(parents=True)
    target = tmp_path / 'external'
    target.mkdir()
    (root / 'mamey' / 'external_alias').symlink_to(target, target_is_directory=True)
    monkeypatch.setattr(m, 'ROOT', str(root))
    with pytest.raises(ValueError, match='symlinked engine directory'):
        m._engine_binding()



@pytest.mark.parametrize('kind', ['package', 'engine'])
def test_inventory_traversal_errors_fail_closed(tmp_path, monkeypatch, kind):
    m = load()
    root = tmp_path / 'synthetic_bundle'
    (root / 'mamey').mkdir(parents=True)
    monkeypatch.setattr(m, 'ROOT', str(root))
    callbacks = []
    def failing_walk(path, *, onerror=None, **kw):
        callbacks.append(onerror)
        error = PermissionError('synthetic traversal denied')
        if onerror is not None:
            onerror(error)
        yield str(path), [], []  # old os.walk behavior could silently omit content
    monkeypatch.setattr(m.os, 'walk', failing_walk)
    with pytest.raises(PermissionError, match='synthetic traversal denied'):
        m._tree_binding(root / 'mamey') if kind == 'package' else m._engine_binding()
    assert callbacks == [m._walk_error]


@pytest.mark.parametrize('kind', ['package', 'engine'])
def test_inventory_normal_traversal_retains_all_files(tmp_path, monkeypatch, kind):
    m = load()
    root = tmp_path / 'synthetic_bundle'
    tools = root / 'tools'
    tools.mkdir(parents=True)
    nested = root / 'mamey' / 'nested'
    nested.mkdir(parents=True)
    (root / 'mamey' / 'synthetic.py').write_text('synthetic code')
    (nested / 'resource.json').write_text('synthetic resource')
    for p in [root / 'mamey_run.py', tools / '_wbio.py', tools / '_console.py']:
        p.write_text('synthetic launcher/helper')
    monkeypatch.setattr(m, 'ROOT', str(root))
    monkeypatch.setattr(m, 'HERE', str(tools))
    original = m.os.walk
    callbacks = []
    def checking_walk(path, *, onerror=None, **kw):
        callbacks.append(onerror)
        yield from original(path, onerror=onerror, **kw)
    monkeypatch.setattr(m.os, 'walk', checking_walk)
    if kind == 'package':
        inventory = m._tree_binding(root / 'mamey')
        assert [item['file'] for item in inventory['files']] == ['nested/resource.json', 'synthetic.py']
    else:
        before = m._engine_binding()['code_sha256']
        (nested / 'resource.json').write_text('changed synthetic resource')
        assert m._engine_binding()['code_sha256'] != before
    assert callbacks and all(callback is m._walk_error for callback in callbacks)
