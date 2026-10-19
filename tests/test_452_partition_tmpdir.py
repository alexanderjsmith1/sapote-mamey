"""Prepared mocked boundaries. No child pytest or native command is launched here."""
import importlib
import json
from pathlib import Path
import sys
import uuid

import pytest


@pytest.fixture
def boundary(tmp_path, monkeypatch):
    tools = Path(__file__).resolve().parents[1] / 'tools'
    monkeypatch.syspath_prepend(str(tools))
    monkeypatch.delenv('SAPOTE_SUITE_TOOL_DIR', raising=False)
    m = importlib.import_module('_release_partition_runner')
    assert Path(m.__file__).resolve() == (tools / '_release_partition_runner.py').resolve()
    source = tmp_path / 'source'
    source.mkdir()
    selected = source / 'test_one.py'
    selected.write_text('def test_one():\n    assert True\n')
    temp = tmp_path / 'declared-temp'
    temp.mkdir()
    monkeypatch.setenv('TMPDIR', str(temp))
    monkeypatch.setattr(m, 'source_digest', lambda source: 'a' * 64)
    monkeypatch.setattr(m, 'machinery_digest', lambda: 'b' * 64)
    monkeypatch.setattr(m, 'suite_tool_header', lambda *a: {})
    return m, source, selected, temp


def execute_route(m, source, selected, output):
    runner = m.PartitionRunner(source, output, sys.executable, env=dict(m.os.environ))
    runner.resolved_python = sys.executable
    runner.record = {'binding': {'source_tree_sha256': 'a' * 64}}
    stage = {'attempts': [], 'status': 'PENDING',
             'plan': {'files': [selected.name], 'expected_nodes': [selected.name + '::test_one']}}
    return runner.execute(stage, collect_only=False, retry_reason=None)


def subset_route(m, source, selected, output):
    return m.measure_manifest_subset([selected], source, evidence=output,
                                    environment={'resolved_executable': sys.executable,
                                                 'identity_sha256': 'c' * 64})


@pytest.mark.parametrize('route', ['subset', 'execute'])
def test_declared_tmpdir_reaches_command_and_failure_is_retained(boundary, tmp_path, monkeypatch, route):
    """Same meaningful command-location assertion before/after; watcher never starts."""
    m, source, selected, temp = boundary
    before = selected.read_bytes()

    class BoundaryStop(RuntimeError):
        pass

    def stopped(command, *, env, **kwargs):
        scratch = Path(command[command.index('--basetemp') + 1])
        assert scratch.parent == temp, 'declared TMPDIR was bypassed'
        assert env['TMPDIR'] == str(temp)
        raise BoundaryStop('no child started')

    monkeypatch.setattr(m.support, 'run_watched', stopped)
    output = tmp_path / 'evidence'
    function = subset_route if route == 'subset' else execute_route
    with pytest.raises(BoundaryStop, match='no child started'):
        function(m, source, selected, output)
    receipts = list(output.rglob('subset.json' if route == 'subset' else 'attempt.json'))
    assert len(receipts) == 1
    receipt = json.loads(receipts[0].read_text())
    assert receipt['status'] == ('FAILED' if route == 'subset' else 'INTERRUPTED')
    assert selected.read_bytes() == before
    # Failure scratch and all durable failure evidence are retained.
    assert Path(receipt['scratch']['resolved_path']).is_dir()


@pytest.mark.parametrize('route', ['subset', 'execute'])
def test_success_cleans_reserved_scratch_only(boundary, tmp_path, monkeypatch, route):
    m, source, selected, temp = boundary
    unrelated = temp / 'unrelated'
    unrelated.mkdir()
    (unrelated / 'sentinel').write_text('keep')
    seen = []

    def green(command, *, log, **kwargs):
        scratch = Path(command[command.index('--basetemp') + 1])
        assert scratch.parent == temp and scratch.is_dir()
        # Pytest normally recreates --basetemp; emulate that ownership transition.
        scratch.rmdir()
        scratch.mkdir()
        (scratch / 'child-file').write_text('synthetic child evidence')
        seen.append(scratch)
        capture = Path(command[command.index('--release-evidence') + 1])
        capture.write_text(json.dumps({'collected': [selected.name + '::test_one'],
                                     'collection_skips': [], 'outcomes': []}))
        log.write_text('mocked successful command\n')
        return {'exit_code': 0, 'stop_reason': None}

    monkeypatch.setattr(m.support, 'run_watched', green)
    monkeypatch.setattr(m.contract, 'validate_capture', lambda *a, **k:
                        {'main_counts': {'passed': 1}, 'subtest_counts': {}, 'collection_skips': 0})
    output = tmp_path / 'evidence'
    function = subset_route if route == 'subset' else execute_route
    result = function(m, source, selected, output)
    if route == 'subset':
        assert result[:3] == (1, 0, 0)
    else:
        assert result['status'] == 'PASS'
    assert len(seen) == 1 and not seen[0].exists()
    assert (unrelated / 'sentinel').read_text() == 'keep'
    receipt = json.loads(next(output.rglob('subset.json' if route == 'subset' else 'attempt.json')).read_text())
    assert receipt['successful_scratch_removed'] is True


@pytest.mark.parametrize('kind', ['root', 'child', 'alias', 'relative', 'missing'])
def test_bad_declared_temp_is_refused_before_source_mutation(boundary, tmp_path, monkeypatch, kind):
    m, source, selected, temp = boundary
    if kind == 'child':
        target = source / 'temp'
        target.mkdir()
    elif kind == 'alias':
        target = tmp_path / 'alias'
        target.symlink_to(source, target_is_directory=True)
    else:
        target = source if kind == 'root' else Path('relative-temp') if kind == 'relative' else tmp_path / 'missing'
    monkeypatch.setenv('TMPDIR', str(target))
    before = sorted(p.relative_to(source).as_posix() for p in source.rglob('*'))

    def forbidden(*a, **k):
        raise AssertionError('invalid scratch root reached watcher')

    monkeypatch.setattr(m.support, 'run_watched', forbidden)
    with pytest.raises((ValueError, FileNotFoundError)):
        subset_route(m, source, selected, tmp_path / 'evidence')
    assert sorted(p.relative_to(source).as_posix() for p in source.rglob('*')) == before
    assert selected.read_text() == 'def test_one():\n    assert True\n'


@pytest.mark.parametrize('kind', ['file', 'directory', 'symlink'])
def test_existing_uuid_scratch_is_not_adopted(boundary, tmp_path, kind):
    m, source, selected, temp = boundary
    token = uuid.uuid4().hex
    occupied = temp / ('sapote-release-' + token)
    target = tmp_path / 'foreign'
    target.mkdir()
    (target / 'sentinel').write_text('keep')
    if kind == 'file':
        occupied.write_text('prior')
    elif kind == 'directory':
        occupied.mkdir()
        (occupied / 'prior').write_text('keep')
    else:
        occupied.symlink_to(target, target_is_directory=True)
    with pytest.raises(FileExistsError):
        m._reserve_scratch(source, {'TMPDIR': str(temp)}, token)
    assert occupied.exists() and (target / 'sentinel').read_text() == 'keep'
    if kind == 'file':
        assert occupied.read_text() == 'prior'
    elif kind == 'directory':
        assert (occupied / 'prior').read_text() == 'keep'
    else:
        assert occupied.is_symlink()


def test_cleanup_refuses_retargeted_parent(boundary, tmp_path):
    m, source, selected, temp = boundary
    other = tmp_path / 'other-temp'
    other.mkdir()
    alias = tmp_path / 'temp-alias'
    alias.symlink_to(temp, target_is_directory=True)
    scratch = m._reserve_scratch(source, {'TMPDIR': str(alias)}, uuid.uuid4().hex)
    original = Path(scratch['resolved_path'])
    foreign = other / original.name
    foreign.mkdir()
    (foreign / 'sentinel').write_text('keep')
    alias.unlink()
    alias.symlink_to(other, target_is_directory=True)
    with pytest.raises(ValueError, match='parent or ownership changed'):
        m._remove_scratch(source, scratch)
    assert original.is_dir() and (foreign / 'sentinel').read_text() == 'keep'


def test_cleanup_refuses_replaced_scratch_symlink(boundary, tmp_path):
    m, source, selected, temp = boundary
    scratch = m._reserve_scratch(source, {'TMPDIR': str(temp)}, uuid.uuid4().hex)
    actual = Path(scratch['resolved_path'])
    actual.rmdir()
    foreign = tmp_path / 'foreign'
    foreign.mkdir()
    (foreign / 'sentinel').write_text('keep')
    actual.symlink_to(foreign, target_is_directory=True)
    with pytest.raises(ValueError, match='real owned directory'):
        m._remove_scratch(source, scratch)
    assert actual.is_symlink() and (foreign / 'sentinel').read_text() == 'keep'


def test_absent_or_empty_tmpdir_keeps_legacy_fallback_without_creating_it(boundary):
    m, source, selected, temp = boundary
    token = '0' * 32
    assert m._scratch_path(source, {}, token) == Path('/tmp/sapote-release-' + token)
    assert m._scratch_path(source, {'TMPDIR': ''}, token) == Path('/tmp/sapote-release-' + token)


def test_binding_records_declared_temp_root(boundary):
    m, source, selected, temp = boundary
    env = {'identity_sha256': 'c' * 64, 'visible_environment': {'TMPDIR': str(temp)}}
    binding = m.binding(source, env, 1, {'rss_limit': 1, 'min_disk': 0, 'timeout': 1})
    assert binding['pytest_temp_root'] == str(temp)
