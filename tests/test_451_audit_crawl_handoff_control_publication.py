"""Offline regressions for residual card-8 pack/return writer alias scope."""
import importlib.util
import os
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
import pytest

SRC = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get('W1_HANDOFF_SOURCE', str(SRC/'tools/blastp_crawl/crawl_handoff.py')))

def load(monkeypatch):
    sys.path.insert(0,str(SRC))
    spec=importlib.util.spec_from_file_location('w1_handoff_test',SOURCE)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    monkeypatch.setattr(mod,'CODE_ROOT',SRC)
    monkeypatch.setattr(mod,'runners_live',lambda:False)
    return mod

def lane(br, n):
    home=br/f'_STRAINGAP_SINGLE_CLNR_GAP_AS{n}';home.mkdir(parents=True)
    q=br/f'_QUERIES_GAP_AS-{n}_K';q.mkdir()
    (q/'synthetic.faa').write_text('>synthetic\nMKKLL\n')
    (home/'_ledger.csv').write_text('file,status\nsynthetic.faa,expired\n')
    return home

@pytest.mark.parametrize('alias',['symlink','hardlink','lane_symlink','directory'])
def test_pack_rejects_late_lane_marker_alias_before_any_publication(tmp_path,monkeypatch,alias):
    mod=load(monkeypatch);br=tmp_path/'ws'/'Blastp RESULTS'
    first=lane(br,970);last=lane(br,971)
    protected=tmp_path/'source_evidence';protected.write_bytes(b'IRREPLACEABLE EVIDENCE\n')
    marker=last/'_HANDOFF_OUT.txt'
    if alias=='symlink':marker.symlink_to(protected)
    elif alias=='hardlink':os.link(protected,marker)
    elif alias=='directory':marker.mkdir()
    else:
        renamed=br/'ordinary_lane';last.rename(renamed);last.symlink_to(renamed,target_is_directory=True)
    monkeypatch.setattr(mod,'workspace',lambda:br.parent)
    before=(first/'_ledger.csv').read_bytes()
    with pytest.raises(ValueError):
        mod.cmd_pack(SimpleNamespace(out=str(tmp_path/'handoffs'),allow_live=False,lanes='',name='H',max_lanes=4))
    assert protected.read_bytes()==b'IRREPLACEABLE EVIDENCE\n'
    assert (first/'_ledger.csv').read_bytes()==before
    assert not (first/'_HANDOFF_OUT.txt').exists()
    assert not (tmp_path/'handoffs/H').exists()
    assert not (tmp_path/'handoffs/H.zip').exists()

@pytest.mark.parametrize('kind',['regular','symlink','hardlink','dangling_symlink'])
def test_return_existing_destination_is_no_clobber(tmp_path,monkeypatch,kind):
    mod=load(monkeypatch)
    root=tmp_path/'handoff';root.mkdir();(root/mod.MANIFEST).write_text('lane\tledger_sha256_at_handoff\n')
    out=tmp_path/'returns';out.mkdir()
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls):return cls(2026,10,15,1,0,0)
    monkeypatch.setattr(mod.dt,'datetime',FrozenDatetime);monkeypatch.chdir(root)
    existing=out/'BLASTP_RETURN_2026-10-15_0100.zip'
    protected=tmp_path/'protected';protected.write_bytes(b'EXISTING ARCHIVE OR SOURCE\n')
    if kind=='regular':existing.write_bytes(b'EXISTING ARCHIVE OR SOURCE\n')
    elif kind=='symlink':existing.symlink_to(protected)
    elif kind=='hardlink':os.link(protected,existing)
    else:existing.symlink_to(tmp_path/'not_created')
    with pytest.raises(FileExistsError):mod.cmd_return(SimpleNamespace(out=str(out)))
    assert protected.read_bytes()==b'EXISTING ARCHIVE OR SOURCE\n'
    if kind=='dangling_symlink':assert not (tmp_path/'not_created').exists()
    else:assert existing.read_bytes()==b'EXISTING ARCHIVE OR SOURCE\n'

def test_return_normal_then_rerun_retains_first_archive(tmp_path,monkeypatch):
    mod=load(monkeypatch);root=tmp_path/'handoff';root.mkdir()
    (root/mod.MANIFEST).write_text('lane\tledger_sha256_at_handoff\n')
    out=tmp_path/'returns';out.mkdir();monkeypatch.chdir(root)
    assert mod.cmd_return(SimpleNamespace(out=str(out)))==0
    archive=next(out.glob('*.zip'));before=archive.read_bytes()
    with pytest.raises(FileExistsError):mod.cmd_return(SimpleNamespace(out=str(out)))
    assert archive.read_bytes()==before

@pytest.mark.parametrize('alias',['symlink','dangling_symlink','hardlink','regular'])
def test_pack_existing_archive_refuses_before_home_marker_write(tmp_path,monkeypatch,alias):
    mod=load(monkeypatch);br=tmp_path/'ws'/'Blastp RESULTS';home=lane(br,971)
    out=tmp_path/'handoffs';out.mkdir();archive=out/'H.zip'
    protected=tmp_path/'protected';protected.write_bytes(b'OLD EVIDENCE\n')
    if alias=='symlink':archive.symlink_to(protected)
    elif alias=='dangling_symlink':archive.symlink_to(tmp_path/'not_created')
    elif alias=='hardlink':os.link(protected,archive)
    else:archive.write_bytes(b'OLD EVIDENCE\n')
    monkeypatch.setattr(mod,'workspace',lambda:br.parent)
    with pytest.raises(SystemExit):mod.cmd_pack(SimpleNamespace(out=str(out),allow_live=False,lanes='',name='H',max_lanes=4))
    assert not (home/'_HANDOFF_OUT.txt').exists()
    assert protected.read_bytes()==b'OLD EVIDENCE\n'
    assert not (out/'H').exists()
    if alias=='dangling_symlink':assert not (tmp_path/'not_created').exists()

def test_ordinary_pack_return_merge_and_merge_rerun(tmp_path,monkeypatch):
    mod=load(monkeypatch);br=tmp_path/'ws'/'Blastp RESULTS';home=lane(br,971)
    monkeypatch.setattr(mod,'workspace',lambda:br.parent)
    out=tmp_path/'handoffs'
    assert mod.cmd_pack(SimpleNamespace(out=str(out),allow_live=False,lanes='',name='H',max_lanes=4))==0
    marker=home/'_HANDOFF_OUT.txt';assert marker.exists()
    packed=out/'H';remote=packed/'Blastp RESULTS'/home.name
    remote.joinpath('_ledger.csv').write_text('file,status\nsynthetic.faa,submitted\n')
    remote.joinpath('returned_evidence.txt').write_text('SYNTHETIC RETURN BYTES\n')
    back=tmp_path/'returns';back.mkdir();monkeypatch.chdir(packed)
    assert mod.cmd_return(SimpleNamespace(out=str(back)))==0
    archive=next(back.glob('*.zip'));before=home.joinpath('_ledger.csv').read_bytes()
    assert mod.cmd_merge(SimpleNamespace(zip=str(archive),execute=False))==0
    assert home.joinpath('_ledger.csv').read_bytes()==before and marker.exists()
    assert mod.cmd_merge(SimpleNamespace(zip=str(archive),execute=True))==0
    assert home.joinpath('returned_evidence.txt').read_text()=='SYNTHETIC RETURN BYTES\n'
    assert not marker.exists()
    # A completed merge changes the ledger binding; rerun holds it rather than overwriting.
    after=home.joinpath('_ledger.csv').read_bytes()
    assert mod.cmd_merge(SimpleNamespace(zip=str(archive),execute=True))==1
    assert home.joinpath('_ledger.csv').read_bytes()==after
