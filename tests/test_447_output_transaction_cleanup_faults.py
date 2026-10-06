"""Publication faults and observable ownership-safe rollback on tiny byte fixtures."""
from pathlib import Path

import pytest

from mamey import output_transaction as tool


@pytest.mark.parametrize('condition',['ordinary','missing','replaced','cleanup_oserror','cleanup_runtimeerror'])
def test_fresh_set_preserves_primary_and_owned_cleanup(tmp_path,monkeypatch,condition):
    root=tmp_path/'outputs'; first=root/'nested'/'first.txt'; second=root/'nested'/'second.txt'
    primary=OSError('synthetic late publish fault')
    original_link=tool.os.link; original_unlink=Path.unlink
    def late_fault(source,target):
        if Path(target)==second:
            if condition=='missing':first.unlink()
            if condition=='replaced':
                displaced=tmp_path/'displaced-owner'; first.rename(displaced)
                first.write_bytes(b'independent claimant')
            raise primary
        return original_link(source,target)
    def cleanup_failure(path,*args,**kwargs):
        if path==first and condition.startswith('cleanup_'):
            fault = PermissionError if condition=='cleanup_oserror' else RuntimeError
            raise fault('synthetic cleanup fault')
        return original_unlink(path,*args,**kwargs)
    monkeypatch.setattr(tool.os,'link',late_fault)
    monkeypatch.setattr(Path,'unlink',cleanup_failure)
    with pytest.raises(OSError) as caught:
        with tool.fresh_output_set(root,['nested/first.txt','nested/second.txt']) as stage:
            (stage/'nested').mkdir();(stage/'nested/first.txt').write_bytes(b'first');(stage/'nested/second.txt').write_bytes(b'second')
    assert caught.value is primary
    rows=primary.rollback_cleanup_diagnostics
    own=next(row for row in rows if row['path']==str(first))
    status={'ordinary':'REMOVED','missing':'MISSING','replaced':'OWNERSHIP_CHANGED','cleanup_oserror':'CLEANUP_FAILED','cleanup_runtimeerror':'CLEANUP_FAILED'}[condition]
    assert own['status']==status
    assert not second.exists()
    if condition in {'ordinary','missing'}:assert not root.exists()
    if condition=='replaced':assert first.read_bytes()==b'independent claimant'
    if condition.startswith('cleanup_'):assert first.read_bytes()==b'first'
    if condition!='ordinary':assert any(status in note for note in primary.__notes__)
    if condition in {'replaced','cleanup_oserror','cleanup_runtimeerror'}:
        assert any(row['action']=='rmdir' and row['status']=='CLEANUP_FAILED' for row in rows)


@pytest.mark.parametrize('condition',['ordinary','missing','replaced','cleanup_oserror','cleanup_runtimeerror'])
def test_payload_fsync_failure_preserves_primary_and_cleanup(tmp_path,monkeypatch,condition):
    first=tmp_path/'first.txt';second=tmp_path/'second.txt';primary=OSError('synthetic second fsync fault')
    original_fsync=tool.os.fsync;original_unlink=Path.unlink;calls=[]
    def late_fault(fd):
        calls.append(fd)
        if len(calls)==2:
            if condition=='missing':first.unlink()
            if condition=='replaced':
                first.rename(tmp_path/'displaced-owner');first.write_bytes(b'independent claimant')
            raise primary
        return original_fsync(fd)
    def cleanup_failure(path,*args,**kwargs):
        if path==first and condition.startswith('cleanup_'):
            fault = PermissionError if condition=='cleanup_oserror' else RuntimeError
            raise fault('synthetic cleanup fault')
        return original_unlink(path,*args,**kwargs)
    monkeypatch.setattr(tool.os,'fsync',late_fault);monkeypatch.setattr(Path,'unlink',cleanup_failure)
    with pytest.raises(OSError) as caught:tool.publish_payloads({first:b'first',second:b'second'})
    assert caught.value is primary
    rows=primary.rollback_cleanup_diagnostics
    own=next(row for row in rows if row['path']==str(first))
    status={'ordinary':'REMOVED','missing':'MISSING','replaced':'OWNERSHIP_CHANGED','cleanup_oserror':'CLEANUP_FAILED','cleanup_runtimeerror':'CLEANUP_FAILED'}[condition]
    assert own['status']==status
    assert not second.exists()
    if condition in {'ordinary','missing'}:assert not first.exists()
    if condition=='replaced':assert first.read_bytes()==b'independent claimant'
    if condition.startswith('cleanup_'):assert first.read_bytes()==b'first'
    if condition!='ordinary':assert any(status in note for note in primary.__notes__)


def test_missing_or_replaced_owned_directories_are_reported(tmp_path):
    primary=ValueError('synthetic primary fault');missing=tmp_path/'missing';missing.mkdir();owned_missing=missing.stat();missing.rmdir()
    changed=tmp_path/'changed';changed.mkdir();owned_changed=changed.stat();changed.rename(tmp_path/'old-directory');changed.mkdir()
    (changed/'claimant.txt').write_bytes(b'preserve')
    tool._rollback_owned(primary,[(missing,owned_missing),(changed,owned_changed)],directories=True)
    assert [r['status'] for r in primary.rollback_cleanup_diagnostics]==['OWNERSHIP_CHANGED','MISSING']
    assert (changed/'claimant.txt').read_bytes()==b'preserve'
    assert len(primary.__notes__)==2


@pytest.mark.parametrize('primary_failure',[True,False])
@pytest.mark.parametrize('cleanup_type',[PermissionError,FileNotFoundError])
def test_staging_teardown_fault_preserves_primary_or_reports_published_outputs(tmp_path,monkeypatch,primary_failure,cleanup_type):
    root=tmp_path/'outputs';primary=ValueError('synthetic producer failure');cleanup=cleanup_type('synthetic staging teardown failure')
    original=tool.shutil.rmtree
    def fail(stage,*args,**kwargs):
        if Path(stage).name.startswith('.mamey-output-'):raise cleanup
        return original(stage,*args,**kwargs)
    monkeypatch.setattr(tool.shutil,'rmtree',fail)
    with pytest.raises(Exception) as caught:
        with tool.fresh_output_set(root,['record.txt']) as stage:
            (stage/'record.txt').write_bytes(b'fixture')
            if primary_failure:raise primary
    assert caught.value is (primary if primary_failure else cleanup)
    row=caught.value.rollback_cleanup_diagnostics[-1]
    assert row['action']=='staging_rmtree' and row['status']=='CLEANUP_FAILED'
    assert any('staging teardown failure' in note for note in caught.value.__notes__)
    if primary_failure:assert not root.exists()
    else:
        assert caught.value.output_transaction_published_paths==[str(root/'record.txt')]
        assert (root/'record.txt').read_bytes()==b'fixture'
        assert any('published and retained' in note for note in caught.value.__notes__)


def test_replaced_staging_directory_preserved_on_cleanup_only_failure(tmp_path,monkeypatch):
    root=tmp_path/'outputs';original=tool.os.link;stage_path=None
    def replace_stage(source,target):
        nonlocal stage_path
        result=original(source,target)
        stage_path=Path(source).parent
        stage_path.rename(tmp_path/'displaced-private-stage');stage_path.mkdir()
        (stage_path/'independent-claimant').write_bytes(b'preserve')
        return result
    monkeypatch.setattr(tool.os,'link',replace_stage)
    # Cache the source identity before linking; the publication journal must not
    # inspect the now-replaced source path to determine target ownership.
    with pytest.raises(Exception) as caught:
        with tool.fresh_output_set(root,['record.txt']) as stage:
            (stage/'record.txt').write_bytes(b'fixture')
    assert isinstance(caught.value,RuntimeError)
    assert caught.value.output_transaction_published_paths==[str(root/'record.txt')]
    assert (root/'record.txt').read_bytes()==b'fixture'
    assert (stage_path/'independent-claimant').read_bytes()==b'preserve'
    assert any(row['status']=='OWNERSHIP_CHANGED' for row in caught.value.rollback_cleanup_diagnostics)


def test_missing_stage_recorded_without_masking_producer_failure(tmp_path):
    primary=ValueError('synthetic producer failure')
    with pytest.raises(ValueError) as caught:
        with tool.fresh_output_set(tmp_path/'outputs',['record.txt']) as stage:
            stage.rmdir()
            raise primary
    assert caught.value is primary
    assert primary.rollback_cleanup_diagnostics[-1]['status']=='MISSING'
    assert any('staging_rmtree: MISSING' in note for note in primary.__notes__)
