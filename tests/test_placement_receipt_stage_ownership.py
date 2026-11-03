"""Recovery receipt writer only; no Newick, metadata or figures."""
import importlib.util
import json
import os
from pathlib import Path
import pytest
TARGET=Path(__file__).resolve().parents[1]/'tools/build_placement_ggtree_inputs.py'
spec=importlib.util.spec_from_file_location('receipt_ownership_candidate',TARGET);tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)

def fixture(tmp_path):
    source=tmp_path/'source.bin';source.write_bytes(b'retained source')
    output=tmp_path/'receipt.json';output.write_bytes(b'previous receipt')
    return source,output,Path(str(output)+'.tmp')

def stage(path,source,kind):
    if kind=='ordinary':path.write_bytes(b'foreign stage')
    elif kind=='symlink':path.symlink_to(source)
    else:os.link(source,path)

@pytest.mark.parametrize('kind',['ordinary','symlink','hardlink'])
def test_lost_exclusive_creation_never_deletes_foreign_stage(tmp_path,monkeypatch,kind):
    source,output,tmp=fixture(tmp_path);real_open=open;inode=[]
    def racing_open(path,*a,**kw):
        if str(path)==str(tmp):
            stage(tmp,source,kind);inode.append(tmp.lstat().st_ino)
        return real_open(path,*a,**kw)
    monkeypatch.setattr(tool,'open',racing_open,raising=False)
    with pytest.raises(FileExistsError):tool._write_recovery_receipt(str(output),{'software':True})
    assert tmp.is_symlink() or tmp.exists()
    assert tmp.lstat().st_ino==inode[0]
    assert tmp.read_bytes()==(b'foreign stage' if kind=='ordinary' else b'retained source')
    assert output.read_bytes()==b'previous receipt' and source.read_bytes()==b'retained source'

@pytest.mark.parametrize('kind',['ordinary','symlink','hardlink'])
def test_preexisting_stage_refused_without_changes(tmp_path,kind):
    source,output,tmp=fixture(tmp_path);stage(tmp,source,kind);inode=tmp.lstat().st_ino;before=tmp.read_bytes()
    with pytest.raises(OSError,match='stale recovery'):tool._write_recovery_receipt(str(output),{})
    assert tmp.lstat().st_ino==inode and tmp.read_bytes()==before
    assert output.read_bytes()==b'previous receipt' and source.read_bytes()==b'retained source'

def test_dangling_stage_symlink_preserved(tmp_path):
    source,output,tmp=fixture(tmp_path);target=tmp_path/'missing';tmp.symlink_to(target)
    with pytest.raises(FileExistsError):tool._write_recovery_receipt(str(output),{})
    assert tmp.is_symlink() and not target.exists()
    assert source.read_bytes()==b'retained source' and output.read_bytes()==b'previous receipt'

@pytest.mark.parametrize('failure',['write','commit'])
def test_owned_stage_failure_cleanup_preserves_prior_output(tmp_path,monkeypatch,failure):
    source,output,tmp=fixture(tmp_path)
    if failure=='write':
        def broken(value,handle,**kw):handle.write('partial');raise RuntimeError('synthetic write refusal')
        monkeypatch.setattr(tool.json,'dump',broken)
    else:
        def broken(*a,**kw):raise RuntimeError('synthetic commit refusal')
        monkeypatch.setattr(tool.os,'replace',broken)
    with pytest.raises(RuntimeError):tool._write_recovery_receipt(str(output),{})
    assert not tmp.exists()
    assert source.read_bytes()==b'retained source' and output.read_bytes()==b'previous receipt'

@pytest.mark.parametrize('kind',['ordinary','symlink','hardlink'])
def test_success_keeps_final_alias_counterpart_and_json_contract(tmp_path,kind):
    source,output,tmp=fixture(tmp_path)
    if kind!='ordinary':output.unlink();stage(output,source,kind)
    payload={'software':'café','value':1};tool._write_recovery_receipt(str(output),payload)
    assert output.read_bytes()==(json.dumps(payload,indent=2,sort_keys=True)+'\n').encode()
    assert source.read_bytes()==b'retained source' and not tmp.exists() and not output.is_symlink()
