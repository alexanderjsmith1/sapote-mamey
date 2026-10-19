"""Synthetic subset evidence-boundary controls; never start a child process."""
import importlib
import json
import os
from pathlib import Path
import stat
import sys

import pytest


@pytest.fixture
def runner(monkeypatch):
    monkeypatch.delenv("SAPOTE_SUITE_TOOL_DIR", raising=False)
    tools = Path(__file__).resolve().parents[1] / 'tools'
    monkeypatch.syspath_prepend(str(tools))
    module = importlib.import_module('_release_partition_runner')
    assert Path(module.__file__).resolve() == (tools / '_release_partition_runner.py').resolve()
    return module


def snapshot(root):
    """Keep entry kinds, link text and bytes, including otherwise empty directories."""
    result = {}
    for path in sorted(root.rglob('*')):
        kind = stat.S_IFMT(path.lstat().st_mode)
        content = os.readlink(path) if stat.S_ISLNK(kind) else path.read_bytes().hex() if stat.S_ISREG(kind) else None
        result[path.relative_to(root).as_posix()] = [kind, content]
    return result


def source_fixture(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    selected = source / 'test_synthetic.py'
    selected.write_text('def test_synthetic():\n    assert True\n')
    (source / 'retained.txt').write_bytes(b'existing source evidence\n')
    return source, selected


@pytest.mark.parametrize('location', ['new_child', 'existing_child', 'source_root', 'alias_child'])
def test_refused_subset_location_preserves_source_entries(tmp_path, monkeypatch, runner, location):
    source, selected = source_fixture(tmp_path)
    evidence = source / 'evidence'
    if location in {'existing_child', 'alias_child'}:
        evidence.mkdir()
        (evidence / 'prior.txt').write_bytes(b'retained prior entry\n')
    if location == 'source_root':
        evidence = source
    if location == 'alias_child':
        alias = tmp_path / 'source-alias'
        alias.symlink_to(source, target_is_directory=True)
        evidence = alias / 'evidence'
    before = snapshot(source)

    def forbidden(*args, **kwargs):
        raise AssertionError('source-overlapping subset attempted child execution')

    monkeypatch.setattr(runner.support, 'run_watched', forbidden)
    with pytest.raises(ValueError, match='manifest subset evidence is inside source'):
        runner.measure_manifest_subset([selected], source, evidence=evidence, environment={})
    assert snapshot(source) == before, 'refused subset location changed source entries'
    if location == 'alias_child':
        assert os.readlink(alias) == str(source)


def test_external_subset_reaches_mocked_watcher_and_retains_failure(tmp_path, monkeypatch, runner):
    source, selected = source_fixture(tmp_path)
    before = snapshot(source)
    evidence = tmp_path / 'external-evidence'

    class StoppedBeforeChild(RuntimeError):
        pass

    def stopped(command, *, cwd, log, env):
        assert cwd == source
        assert command[-1] == 'test_synthetic.py'
        assert log.is_relative_to(evidence)
        raise StoppedBeforeChild('synthetic boundary; no child started')

    monkeypatch.setattr(runner.support, 'run_watched', stopped)
    environment = {'resolved_executable': sys.executable, 'identity_sha256': 'a' * 64}
    with pytest.raises(StoppedBeforeChild, match='no child started'):
        runner.measure_manifest_subset([selected], source, evidence=evidence, environment=environment)
    assert snapshot(source) == before
    receipts = list(evidence.glob('*/subset.json'))
    assert len(receipts) == 1
    receipt = json.loads(receipts[0].read_text())
    assert receipt['status'] == 'FAILED'
    assert receipt['reason'] == 'synthetic boundary; no child started'
    assert receipt['selected_files'] == ['test_synthetic.py']
