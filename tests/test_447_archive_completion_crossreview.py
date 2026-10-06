"""Synthetic archive transaction faults; no biological or release inputs.

Tests express required receipts, including outstanding failures found in cross-review.
"""
import concurrent.futures
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import threading
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location('crossreview_' + name, ROOT / 'tools' / (name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def stage(tmp_path):
    src, out = tmp_path / 'stage', tmp_path / 'out'
    (src / 'nested').mkdir(parents=True)
    out.mkdir()
    (src / 'nested' / 'record.txt').write_bytes(b'synthetic archive fixture')
    return src, out


def pair(tmp_path):
    src, out = tmp_path / 'source', tmp_path / 'out'
    src.mkdir(); out.mkdir()
    archive = src / 'fixture.tar.gz'
    archive.write_bytes(b'opaque synthetic archive bytes')
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    sidecar = src / (archive.name + '.sha256')
    sidecar.write_text(digest + '  ' + archive.name + '\n')
    hashes = [hashlib.sha256(p.read_bytes()).hexdigest() for p in (archive, sidecar)]
    return archive, sidecar, out, *hashes


def test_old_predictable_dangling_stage_symlink_is_not_followed(tmp_path):
    mod = module('finalize_public_archive')
    src, out = stage(tmp_path)
    victim = tmp_path / 'unrelated-file'
    old = out / '.fixture.zip.archtxn.tmp'
    old.symlink_to(victim)
    assert mod.finalize_archive(src, out, 'fixture.zip').status == 'COMMITTED'
    assert old.is_symlink() and not victim.exists()


def test_scandir_failure_has_typed_refusal_before_publication(tmp_path, monkeypatch):
    mod = module('finalize_public_archive')
    src, out = stage(tmp_path)
    original = mod.os.scandir
    def fail(path):
        if not isinstance(path, int) and Path(path) == src / 'nested':
            raise PermissionError('synthetic unreadable subtree')
        return original(path)
    monkeypatch.setattr(mod.os, 'scandir', fail)
    with pytest.raises(mod.ArchiveTransactionError, match='stage_traversal_unverified'):
        mod.finalize_archive(src, out, 'fixture.zip')
    assert not (out / 'fixture.zip').exists()


@pytest.mark.parametrize('operation', ['read', 'stat'])
def test_inventory_read_and_stat_failure_have_typed_refusal(tmp_path, monkeypatch, operation):
    mod = module('finalize_public_archive')
    src, out = stage(tmp_path)
    member = src / 'nested' / 'record.txt'
    if operation == 'read':
        original = mod._sha_path
        def fail(path):
            if Path(path) == member:
                raise PermissionError('synthetic unreadable member')
            return original(path)
        monkeypatch.setattr(mod, '_sha_path', fail)
    else:
        original = Path.lstat
        def fail(path, *args, **kwargs):
            if path == member:
                raise PermissionError('synthetic unstatable member')
            return original(path, *args, **kwargs)
        monkeypatch.setattr(Path, 'lstat', fail)
    with pytest.raises(mod.ArchiveTransactionError):
        mod.finalize_archive(src, out, 'fixture.zip')
    assert not (out / 'fixture.zip').exists()


def test_two_same_name_finalizers_preserve_winner(tmp_path, monkeypatch):
    mod = module('finalize_public_archive')
    src, out = stage(tmp_path)
    barrier = threading.Barrier(2)
    original = mod._write_archive
    def simultaneous(*args):
        barrier.wait(timeout=10)
        return original(*args)
    monkeypatch.setattr(mod, '_write_archive', simultaneous)
    def run():
        try:
            return mod.finalize_archive(src, out, 'fixture.zip').status
        except mod.ArchiveTransactionError as exc:
            assert not exc.committed and exc.code == 'ARCHTXN-TXN-001'
            return 'REFUSED'
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        outcomes = list(pool.map(lambda _: run(), range(2)))
    assert sorted(outcomes) == ['COMMITTED', 'REFUSED']
    with zipfile.ZipFile(out / 'fixture.zip') as archive:
        assert archive.read('nested/record.txt') == b'synthetic archive fixture'
    assert not list(out.glob('.archtxn-*'))


def test_postcommit_close_fault_still_reports_committed_hold(tmp_path, monkeypatch, capsys):
    mod = module('finalize_public_archive')
    src, out = stage(tmp_path)
    # Probe itself remains real; inject only after the native commit completes.
    original_commit, original_close = mod.commit_noreplace, mod.os.close
    armed = False
    def commit(*args):
        nonlocal armed
        result = original_commit(*args)
        if args[-1] == 'fixture.zip':
            armed = True
        return result
    def close(fd):
        nonlocal armed
        original_close(fd)
        if armed:
            armed = False
            raise OSError('synthetic descriptor close failure after commit')
    monkeypatch.setattr(mod, 'commit_noreplace', commit)
    monkeypatch.setattr(mod.os, 'close', close)
    rc = mod._main(['--stage-root', str(src), '--output-dir', str(out), '--archive-name', 'fixture.zip'])
    assert rc != 0
    record = json.loads(capsys.readouterr().out)
    assert record['status'] == 'COMMITTED_HOLD' and record['committed'] is True
    assert (out / 'fixture.zip').is_file()


def test_pair_sidecar_lost_race_preserves_both_owners(tmp_path, monkeypatch):
    mod = module('publish_verified_pair')
    args = pair(tmp_path)
    original = mod.os.link
    def claim_sidecar(source, target):
        if str(target).endswith('.sha256'):
            Path(target).write_bytes(b'independent claimant')
        return original(source, target)
    monkeypatch.setattr(mod.os, 'link', claim_sidecar)
    result = mod.publish_pair(*args)
    assert result['status'] == 'COMMITTED_HOLD'
    assert result['committed'] == [str(args[2] / args[0].name)]
    assert (args[2] / args[0].name).read_bytes() == args[0].read_bytes()
    assert (args[2] / args[1].name).read_bytes() == b'independent claimant'


def test_two_publishers_keep_complete_winning_pair(tmp_path, monkeypatch):
    mod = module('publish_verified_pair')
    args = pair(tmp_path)
    barrier = threading.Barrier(2)
    original = mod.os.link
    def simultaneous(source, target):
        if Path(target).name == args[0].name:
            barrier.wait(timeout=10)
        return original(source, target)
    monkeypatch.setattr(mod.os, 'link', simultaneous)
    def run():
        try:
            return mod.publish_pair(*args)['status']
        except FileExistsError:
            return 'REFUSED'
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        outcomes = list(pool.map(lambda _: run(), range(2)))
    assert sorted(outcomes) == ['COMMITTED', 'REFUSED']
    for source in args[:2]:
        assert (args[2] / source.name).read_bytes() == source.read_bytes()
    assert not list(args[2].glob('.verified-pair-*'))


def test_pair_cleanup_fault_does_not_erase_committed_receipt(tmp_path, monkeypatch, capsys):
    mod = module('publish_verified_pair')
    args = pair(tmp_path)
    def fail(path):
        raise OSError('synthetic private staging cleanup failure')
    monkeypatch.setattr(mod.shutil, 'rmtree', fail)
    rc = mod.main([str(arg) for arg in args])
    assert rc == 2
    captured = capsys.readouterr()
    record = json.loads(captured.out)
    assert record['status'] == 'COMMITTED_HOLD'
    assert set(record['committed']) == {str(args[2] / p.name) for p in args[:2]}
    assert all((args[2] / p.name).read_bytes() == p.read_bytes() for p in args[:2])


def test_replaced_final_archive_cannot_return_verified_success(tmp_path, monkeypatch):
    mod = module('publish_verified_pair')
    args = pair(tmp_path)
    original = mod.os.link
    def competing_replace(source, target):
        result = original(source, target)
        if Path(target).name == args[0].name:
            Path(target).unlink()
            Path(target).write_bytes(b'independent replacement')
        return result
    monkeypatch.setattr(mod.os, 'link', competing_replace)
    result = mod.publish_pair(*args)
    assert result['status'] == 'COMMITTED_HOLD'
    assert (args[2] / args[0].name).read_bytes() == b'independent replacement'


def test_changed_private_pair_member_cannot_publish_verified_success(tmp_path, monkeypatch):
    mod = module('publish_verified_pair')
    args = pair(tmp_path)
    original = mod.os.link
    def replace_staged_member(source, target):
        if Path(target).name == args[0].name:
            Path(source).unlink()
            Path(source).write_bytes(b'synthetic changed staged member')
        return original(source, target)
    monkeypatch.setattr(mod.os, 'link', replace_staged_member)
    result = mod.publish_pair(*args)
    assert result['status'] == 'COMMITTED_HOLD'
    assert (args[2] / args[0].name).read_bytes() != args[0].read_bytes()


def test_postcommit_fsync_failure_has_exact_committed_path_and_digest(tmp_path, monkeypatch, capsys):
    mod = module('finalize_public_archive')
    src, out = stage(tmp_path)
    original = mod.finalize_archive
    def fail(fd):
        raise OSError('synthetic durability failure')
    def with_failure(*args):
        return original(*args, postcommit_fsync=fail)
    monkeypatch.setattr(mod, 'finalize_archive', with_failure)
    rc = mod._main(['--stage-root', str(src), '--output-dir', str(out), '--archive-name', 'fixture.zip'])
    assert rc == 1
    record = json.loads(capsys.readouterr().out)
    target = out / 'fixture.zip'
    assert record['status'] == 'COMMITTED_HOLD' and record['committed'] is True
    assert record['archive_path'] == str(target)
    assert record['expected_sha256'] == hashlib.sha256(target.read_bytes()).hexdigest()


def test_finalizer_replaced_private_directory_is_not_cleaned(tmp_path, monkeypatch):
    mod = module('finalize_public_archive')
    src, out = stage(tmp_path)
    original = mod.commit_noreplace
    replacement = None
    def replace_private_directory(*args):
        nonlocal replacement
        result = original(*args)
        if args[-1] == 'fixture.zip':
            replacement = next(out.glob('.archtxn-*'))
            replacement.rename(out / 'displaced-owned-directory')
            replacement.mkdir()
            (replacement / 'other-owner').write_bytes(b'preserve independent directory')
        return result
    monkeypatch.setattr(mod, 'commit_noreplace', replace_private_directory)
    with pytest.raises(mod.ArchiveTransactionError) as error:
        mod.finalize_archive(src, out, 'fixture.zip')
    assert error.value.committed
    assert (replacement / 'other-owner').read_bytes() == b'preserve independent directory'
    assert (out / 'fixture.zip').is_file()


def test_pair_replaced_private_directory_is_not_cleaned(tmp_path, monkeypatch):
    mod = module('publish_verified_pair')
    args = pair(tmp_path)
    original = mod.os.link
    replacement = None
    def replace_private_directory(source, target):
        nonlocal replacement
        result = original(source, target)
        if str(target).endswith('.sha256'):
            replacement = Path(source).parent
            replacement.rename(args[2] / 'displaced-owned-directory')
            replacement.mkdir()
            (replacement / 'other-owner').write_bytes(b'preserve independent directory')
        return result
    monkeypatch.setattr(mod.os, 'link', replace_private_directory)
    result = mod.publish_pair(*args)
    assert result['status'] == 'COMMITTED_HOLD'
    assert (replacement / 'other-owner').read_bytes() == b'preserve independent directory'
    for source in args[:2]:
        assert (args[2] / source.name).read_bytes() == source.read_bytes()
