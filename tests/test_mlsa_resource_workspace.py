"""Synthetic whole-worker resource/receipt controls; no installed native tools."""
import json
from pathlib import Path
import tempfile

import pytest

from tools import _mlsa_resources as resource
from tools import build_mlsa as mlsa


@pytest.fixture
def inputs(tmp_path):
    genomes = tmp_path / 'genome inputs'; genomes.mkdir()
    (genomes / 'SYNTHETIC_REFERENCE.fna').write_text('>SYNTHETIC_REFERENCE_CONTIG\nACGT\n')
    seeds = tmp_path / 'seed inputs'; seeds.mkdir()
    for locus in mlsa.LOCI:
        (seeds / (locus + '.faa')).write_text('>SYNTHETIC_REFERENCE_SEED\nMPEP\n')
    bins = tmp_path / 'binary directory'; bins.mkdir()
    for name in mlsa._BIN_ALIASES:
        p = bins / name; p.write_text('#!/bin/sh\nexit 0\n'); p.chmod(0o755)
    output = tmp_path / 'output with spaces'
    return genomes, seeds, bins, output


@pytest.fixture
def safe_root():
    with tempfile.TemporaryDirectory(prefix='synthetic-mlsa-', dir=Path('/tmp').resolve()) as path:
        yield Path(path).resolve()


def arguments(inputs, root, extra=()):
    genomes, seeds, bins, output = inputs
    return resource.parser().parse_args([str(genomes), str(output), '--seeds-dir', str(seeds),
        '--bin-dir', str(bins), '--native-work-root', str(root), '--threads', '1',
        '--min-free-disk-bytes', '1', *extra])


def abundant(monkeypatch):
    monkeypatch.setattr(resource.shutil, 'disk_usage', lambda path: type('Disk', (), {'free': 10**12})())


def fake_compute(argv, *, native_workdir, native_copy_limit, bound_bins):
    output = Path(argv[1]); output.mkdir()
    assert native_copy_limit > 0
    assert resource.workspace.shell_safe_path(native_workdir) == Path(native_workdir)
    assert set(bound_bins) == set(mlsa._BIN_ALIASES)
    (output / 'tree.treefile').write_text('(SYNTHETIC_REFERENCE_A:1,SYNTHETIC_REFERENCE_B:1);\n')
    (output / 'mlsa.log').write_text('SYNTHETIC_REFERENCE_WORKER_COMPLETED\n')
    (output / 'run_status.json').write_text(json.dumps({'status': 'COMPLETE'}))
    return 0


def watch_with_worker(monkeypatch, *, after=None, verdict=None):
    observed = []
    def watch(argv, **kw):
        assert argv[1] == '-B' and argv[3] == '--_mlsa-worker'
        request_path = Path(argv[4]); request = resource.load(request_path)
        assert kw['cwd'] == request_path.parent
        assert kw['additional_disk_floors'] == ((Path(request['disk_policy']['roots'][1]['path']),
            request['disk_policy']['roots'][1]['watch_floor_bytes']),)
        assert kw['min_disk'] == request['disk_policy']['roots'][0]['watch_floor_bytes']
        assert {key: kw['env'][key] for key in resource.THREAD_KEYS} == {key: '1' for key in resource.THREAD_KEYS}
        assert len(resource.THREAD_KEYS) == 6
        observed.append(request)
        with monkeypatch.context() as env:
            for key in resource.THREAD_KEYS: env.setenv(key, kw['env'][key])
            assert resource.worker(request_path, argv[5]) == 0
        if after: after(request)
        return verdict or {'exit_code': 0, 'stop_reason': None, 'cleanup_error': None}
    monkeypatch.setattr(resource, 'run_watched', watch)
    return observed


def test_full_worker_receipt_chain_both_filesystems_source_bytes_and_cleanup(inputs, safe_root, monkeypatch):
    abundant(monkeypatch)
    before = resource.input_bindings(inputs[0], inputs[1], resource.DEFAULT_COPY)
    monkeypatch.setattr(mlsa, '_compute_main', fake_compute)
    observed = watch_with_worker(monkeypatch)
    assert resource.coordinate(arguments(inputs, safe_root)) == 0
    out = inputs[3]
    attempt = next((out / 'RESOURCE_ATTEMPT').iterdir())
    success = resource.load(attempt / 'SUCCEEDED.json')
    assert success['request'] == resource.bind(attempt / 'REQUEST.json')
    assert success['resource'] == resource.bind(attempt / 'RESOURCE.json')
    assert success['completion'] == resource.bind(attempt / 'WORKER_COMPLETION.json')
    assert success['scratch_cleanup'] == 'OWNED_TEMP_REMOVED'
    assert not Path(observed[0]['scratch']['path']).exists()
    assert resource.load(out / 'run_status.json')['status'] == 'COMPLETE'
    assert (out / 'tree.treefile').read_text().startswith('(SYNTHETIC_REFERENCE_A:1,')
    assert before == resource.input_bindings(inputs[0], inputs[1], resource.DEFAULT_COPY)
    assert observed[0]['disk_policy']['same_filesystem'] in (True, False)


@pytest.mark.parametrize('extra', [('--rss-limit-bytes', '0'), ('--timeout-seconds', 'nan'),
    ('--native-copy-limit-bytes', '1'), ('--threads', '0')])
def test_refused_budget_or_copy_preflight_has_no_output_scratch_or_child(inputs, safe_root, monkeypatch, extra):
    abundant(monkeypatch)
    monkeypatch.setattr(resource, 'run_watched', lambda *a, **k: pytest.fail('child launched'))
    with pytest.raises(resource.MlsaRefused):
        resource.coordinate(arguments(inputs, safe_root, extra))
    assert not inputs[3].exists() and list(safe_root.iterdir()) == []


@pytest.mark.parametrize('low', ['output', 'scratch'])
def test_each_low_filesystem_refuses_before_output_or_scratch(inputs, safe_root, monkeypatch, low):
    parent = inputs[3].parent
    monkeypatch.setattr(resource.shutil, 'disk_usage', lambda path: type('Disk', (),
        {'free': 1 if Path(path) == (parent if low == 'output' else safe_root) else 10**12})())
    monkeypatch.setattr(resource, 'run_watched', lambda *a, **k: pytest.fail('child launched'))
    with pytest.raises(resource.MlsaRefused, match='disk'):
        resource.coordinate(arguments(inputs, safe_root))
    assert not inputs[3].exists() and list(safe_root.iterdir()) == []


def test_unsafe_explicit_root_refuses_before_any_write(inputs, safe_root, monkeypatch):
    unsafe = safe_root / 'tab\tand space'; unsafe.mkdir()
    monkeypatch.setattr(resource, 'run_watched', lambda *a, **k: pytest.fail('child launched'))
    with pytest.raises(resource.MlsaRefused, match='shell-safe'):
        resource.coordinate(arguments(inputs, unsafe))
    assert not inputs[3].exists() and list(unsafe.iterdir()) == []


def test_occupied_output_preserves_all_bytes_without_child(inputs, safe_root, monkeypatch):
    out = inputs[3]; out.mkdir(); (out / 'tree.treefile').write_bytes(b'SYNTHETIC_REFERENCE_SENTINEL')
    monkeypatch.setattr(resource, 'run_watched', lambda *a, **k: pytest.fail('child launched'))
    with pytest.raises(resource.MlsaRefused, match='new or empty'):
        resource.coordinate(arguments(inputs, safe_root))
    assert (out / 'tree.treefile').read_bytes() == b'SYNTHETIC_REFERENCE_SENTINEL'
    assert list(safe_root.iterdir()) == []


@pytest.mark.parametrize('mode', ['stop_zero', 'source_drift', 'tool_drift', 'completion_drift', 'output_symlink'])
def test_postlaunch_failures_keep_diagnostics_never_promote_complete_or_tree(inputs, safe_root, monkeypatch, mode):
    abundant(monkeypatch); monkeypatch.setattr(mlsa, '_compute_main', fake_compute)
    def after(request):
        if mode == 'source_drift':
            Path(request['inputs'][0]['path']).write_text('>SYNTHETIC_REFERENCE_CHANGED\nACGA\n')
        elif mode == 'tool_drift':
            Path(request['tools']['blastp']['locator']).write_text('#!/bin/sh\nexit 9\n')
        elif mode == 'completion_drift':
            path = Path(request['worker_output']).parent / 'WORKER_COMPLETION.json'
            data = resource.load(path); data['request_sha256'] = '0' * 64
            path.write_text(json.dumps(data))
        elif mode == 'output_symlink':
            tree = Path(request['worker_output']) / 'tree.treefile'
            tree.unlink(); tree.symlink_to(request['inputs'][0]['path'])
    verdict = {'exit_code': 0, 'stop_reason': 'TIME_LIMIT', 'cleanup_error': None} if mode == 'stop_zero' else None
    observed = watch_with_worker(monkeypatch, after=after, verdict=verdict)
    assert resource.coordinate(arguments(inputs, safe_root)) != 0
    attempt = next((inputs[3] / 'RESOURCE_ATTEMPT').iterdir())
    assert (attempt / 'FAILED.json').is_file() and not (attempt / 'SUCCEEDED.json').exists()
    assert resource.load(inputs[3] / 'run_status.json')['status'] == 'FAILED'
    assert not (inputs[3] / 'tree.treefile').exists()
    assert not Path(observed[0]['scratch']['path']).exists()
    assert (attempt / 'RESOURCE.json').is_file()


def test_monitor_cleanup_uncertain_retains_only_owned_scratch_for_diagnosis(inputs, safe_root, monkeypatch):
    abundant(monkeypatch); observed = []
    def watch(argv, **kw):
        observed.append(resource.load(argv[4]))
        return {'exit_code': 0, 'stop_reason': 'MONITOR_ERROR', 'cleanup_error': 'SYNTHETIC_REFERENCE_UNREAPED'}
    monkeypatch.setattr(resource, 'run_watched', watch)
    assert resource.coordinate(arguments(inputs, safe_root)) != 0
    descriptor = observed[0]['scratch']
    owned = resource.workspace.OwnedWorkspace(descriptor['path'], descriptor['device'], descriptor['inode'])
    assert owned.path.is_dir()
    attempt = next((inputs[3] / 'RESOURCE_ATTEMPT').iterdir())
    assert resource.load(attempt / 'FAILED.json')['scratch_cleanup'] == 'RETAINED_MONITOR_CLEANUP_UNCONFIRMED'
    assert not (inputs[3] / 'tree.treefile').exists()
    owned.cleanup()  # Synthetic test knows no real child was launched.


def test_worker_request_digest_and_thread_context_refuse_before_compute(inputs, safe_root, monkeypatch):
    abundant(monkeypatch)
    def watch(argv, **kw):
        monkeypatch.setattr(mlsa, '_compute_main', lambda *a, **k: pytest.fail('compute entered'))
        with pytest.raises(resource.MlsaRefused, match='digest'):
            resource.worker(argv[4], '0' * 64)
        for key in resource.THREAD_KEYS: monkeypatch.setenv(key, '1')
        monkeypatch.setenv('OMP_THREAD_LIMIT', '2')
        with pytest.raises(resource.MlsaRefused, match='six-key'):
            resource.worker(argv[4], argv[5])
        return {'exit_code': 1, 'stop_reason': None, 'cleanup_error': None}
    monkeypatch.setattr(resource, 'run_watched', watch)
    assert resource.coordinate(arguments(inputs, safe_root)) != 0
    assert list(safe_root.iterdir()) == []


def test_watcher_exception_retains_scratch_without_unproven_cleanup(inputs, safe_root, monkeypatch):
    abundant(monkeypatch); observed = []
    def watch(argv, **kw):
        observed.append(resource.load(argv[4]))
        raise resource.ValidationRefused('SYNTHETIC_REFERENCE_MONITOR_EXCEPTION')
    monkeypatch.setattr(resource, 'run_watched', watch)
    assert resource.coordinate(arguments(inputs, safe_root)) != 0
    descriptor = observed[0]['scratch']
    owned = resource.workspace.OwnedWorkspace(descriptor['path'], descriptor['device'], descriptor['inode'])
    assert owned.path.is_dir() and not (inputs[3] / 'tree.treefile').exists()
    attempt = next((inputs[3] / 'RESOURCE_ATTEMPT').iterdir())
    assert resource.load(attempt / 'FAILED.json')['scratch_cleanup'] == 'RETAINED_MONITOR_CLEANUP_UNCONFIRMED'
    owned.cleanup()  # Test stub never launched a child.


def test_late_completion_receipt_failure_invalidates_owned_complete_status(inputs, safe_root, monkeypatch):
    abundant(monkeypatch); monkeypatch.setattr(mlsa, '_compute_main', fake_compute)
    watch_with_worker(monkeypatch)
    original_save = resource.save
    def fail_terminal(path, payload):
        if Path(path).name == 'SUCCEEDED.json':
            raise OSError('SYNTHETIC_REFERENCE_TERMINAL_WRITE_FAILURE')
        return original_save(path, payload)
    monkeypatch.setattr(resource, 'save', fail_terminal)
    assert resource.coordinate(arguments(inputs, safe_root)) != 0
    attempt = next((inputs[3] / 'RESOURCE_ATTEMPT').iterdir())
    assert (attempt / 'FAILED.json').is_file() and not (attempt / 'SUCCEEDED.json').exists()
    assert resource.load(inputs[3] / 'run_status.json')['status'] == 'FAILED'
    assert list(safe_root.iterdir()) == []


def test_rss_estimate_refuses_from_metadata_before_payload_hash_or_child(inputs, safe_root, monkeypatch):
    abundant(monkeypatch)
    monkeypatch.setattr(resource, 'input_bindings', lambda *a, **k: pytest.fail('payload hashing before resource admission'))
    monkeypatch.setattr(resource, 'run_watched', lambda *a, **k: pytest.fail('child launched'))
    with pytest.raises(resource.MlsaRefused, match='estimated RSS'):
        resource.coordinate(arguments(inputs, safe_root, ('--rss-limit-bytes', '1000')))
    assert not inputs[3].exists() and list(safe_root.iterdir()) == []


def test_file_appearing_at_promotion_is_never_overwritten(inputs, safe_root, monkeypatch):
    abundant(monkeypatch); monkeypatch.setattr(mlsa, '_compute_main', fake_compute)
    watch_with_worker(monkeypatch)
    original_copy = resource.workspace.bounded_copy
    sentinel = inputs[3] / 'tree.treefile'
    def race(source, target, ceiling, **kw):
        if Path(target) == sentinel:
            sentinel.write_bytes(b'SYNTHETIC_REFERENCE_UNOWNED_SENTINEL')
        return original_copy(source, target, ceiling, **kw)
    monkeypatch.setattr(resource.workspace, 'bounded_copy', race)
    assert resource.coordinate(arguments(inputs, safe_root)) != 0
    assert sentinel.read_bytes() == b'SYNTHETIC_REFERENCE_UNOWNED_SENTINEL'
    assert resource.load(inputs[3] / 'run_status.json')['status'] == 'FAILED'
    assert list(safe_root.iterdir()) == []


def test_disk_drop_during_bounded_promotion_cannot_claim_complete(inputs, safe_root, monkeypatch):
    abundant(monkeypatch); monkeypatch.setattr(mlsa, '_compute_main', fake_compute)
    def after(request):
        monkeypatch.setattr(resource.shutil, 'disk_usage', lambda path: type('Disk', (), {'free': 0})())
    watch_with_worker(monkeypatch, after=after)
    assert resource.coordinate(arguments(inputs, safe_root)) != 0
    attempt = next((inputs[3] / 'RESOURCE_ATTEMPT').iterdir())
    assert 'disk floor' in resource.load(attempt / 'FAILED.json')['detail']
    assert resource.load(inputs[3] / 'run_status.json')['status'] == 'FAILED'
    assert not (inputs[3] / 'tree.treefile').exists() and list(safe_root.iterdir()) == []
