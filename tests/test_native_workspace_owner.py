"""Invented files only: shared path/copy/ownership contract, no native companions."""
import hashlib
from pathlib import Path
import shutil
import tempfile

import pytest

from mamey import native_workspace as workspace
from tools import _protein_pcoa_resources as pcoa


@pytest.fixture
def safe_root():
    with tempfile.TemporaryDirectory(prefix="synthetic-native-owner-", dir=Path('/tmp').resolve()) as name:
        yield Path(name).resolve()


@pytest.mark.parametrize('suffix', ['space path', 'tab\tpath', 'line\nbreak', 'semi;colon', 'dollar$',
                                    'tick`', 'quote\'', 'double"', 'paren()', 'pipe|', 'amp&',
                                    'glob*', 'bracket[', 'unicode_é'])
def test_unsafe_work_root_refuses_without_allocating(safe_root, suffix, monkeypatch):
    root = safe_root / suffix; root.mkdir()
    monkeypatch.setattr(workspace.tempfile, 'mkdtemp', lambda **kw: pytest.fail('allocation before refusal'))
    with pytest.raises(workspace.NativeWorkspaceRefused, match='shell-safe'):
        workspace.OwnedWorkspace.create(root)
    assert list(root.iterdir()) == []


def test_explicit_alias_refused_default_resolved_alias_admitted(safe_root, tmp_path, monkeypatch):
    alias = tmp_path / 'alias'; alias.symlink_to(safe_root, target_is_directory=True)
    with pytest.raises(workspace.NativeWorkspaceRefused, match='symlink'):
        workspace.work_root(alias)
    monkeypatch.setattr(workspace.tempfile, 'gettempdir', lambda: str(alias))
    assert workspace.work_root() == safe_root


def test_copy_binds_original_and_consumed_bytes_and_never_clobbers(tmp_path):
    source = tmp_path / 'source with spaces.faa'; source.write_bytes(b'>SYNTHETIC_REFERENCE\nMPEP\n')
    target = tmp_path / 'copy.faa'
    with pytest.raises(workspace.NativeWorkspaceRefused, match='ceiling'):
        workspace.bounded_copy(source, target, 1)
    assert not target.exists()
    result = workspace.bounded_copy(source, target, 100)
    expected = hashlib.sha256(source.read_bytes()).hexdigest()
    assert result['source']['sha256'] == result['copy']['sha256'] == expected
    assert source.read_bytes() == target.read_bytes()
    target.write_bytes(b'SYNTHETIC_REFERENCE_SENTINEL')
    with pytest.raises(FileExistsError):
        workspace.bounded_copy(source, target, 100)
    assert target.read_bytes() == b'SYNTHETIC_REFERENCE_SENTINEL'


def test_changed_consumed_source_is_refused(tmp_path, monkeypatch):
    source = tmp_path / 'source'; source.write_bytes(b'abcdef')
    target = tmp_path / 'copy'
    actual = workspace.digest
    calls = []
    def changed(path, **kw):
        if Path(path) == target:
            source.write_bytes(b'abcdeg')
        calls.append(Path(path))
        return actual(path, **kw)
    monkeypatch.setattr(workspace, 'digest', changed)
    with pytest.raises(workspace.NativeWorkspaceRefused, match='consumed-byte'):
        workspace.bounded_copy(source, target, 100)
    assert target.read_bytes() == b'abcdef' and source.read_bytes() == b'abcdeg'


def test_cleanup_preserves_replaced_directory_and_unowned_sentinel(safe_root, tmp_path):
    owned = workspace.OwnedWorkspace.create(safe_root)
    moved = owned.path.with_name(owned.path.name + '-moved'); owned.path.rename(moved)
    sentinel = tmp_path / 'sentinel'; sentinel.mkdir(); (sentinel / 'keep').write_text('SYNTHETIC_REFERENCE_SENTINEL')
    owned.path.symlink_to(sentinel, target_is_directory=True)
    with pytest.raises(workspace.NativeWorkspaceRefused, match='symlink'):
        owned.cleanup()
    assert (sentinel / 'keep').read_text() == 'SYNTHETIC_REFERENCE_SENTINEL'
    owned.path.unlink(); shutil.rmtree(moved)


def test_diamond_adapter_uses_shared_owner_with_existing_typed_refusal(safe_root, tmp_path, monkeypatch):
    binary = safe_root / 'diamond'; binary.write_bytes(b'SYNTHETIC_REFERENCE_NOT_EXECUTED')
    source = tmp_path / 'original with spaces.faa'; source.write_bytes(b'>SYNTHETIC_REFERENCE\nMPEP\n')
    destination = tmp_path / 'refs_clusters.tsv'
    monkeypatch.setattr(pcoa.shutil, 'disk_usage', lambda p: type('Disk', (), {'free': 10**12})())
    limits = {'min_free_disk_bytes': 1}
    stat = safe_root.stat()
    policy = {'root': str(safe_root), 'device': stat.st_dev, 'inode': stat.st_ino,
              'estimated_disk_bytes': 1000, 'input_copy_ceiling_bytes': 1000}
    created = []
    original_create = workspace.OwnedWorkspace.create.__func__
    def create(cls, *args, **kw):
        result = original_create(cls, *args, **kw); created.append(result); return result
    monkeypatch.setattr(workspace.OwnedWorkspace, 'create', classmethod(create))
    def child(argv, **kw):
        assert argv == [str(binary), 'cluster', '-d', 'input.faa', '-o', 'clusters.tsv',
                        '--approx-id', '70', '--member-cover', '80', '--threads', '1',
                        '--tmpdir', 'tmp', '--quiet']
        assert kw == {'cwd': created[0].path, 'check': True}
        assert (created[0].path / 'input.faa').read_bytes() == source.read_bytes()
        (created[0].path / 'clusters.tsv').write_bytes(b'SYNTHETIC_REFERENCE\tSYNTHETIC_REFERENCE\n')
    monkeypatch.setattr(pcoa.subprocess, 'run', child)
    result = pcoa.run_cluster_workspace(binary, source, destination, name='refs', approx_id=70,
        threads=1, member_count=1, maximum_id_bytes=24, policy=policy, limits=limits)
    assert len(created) == 1 and not created[0].path.exists()
    assert result['cleanup'] == 'OWNED_TEMP_REMOVED'
    assert result['input_copy']['source']['sha256'] == workspace.digest(source)['sha256']
