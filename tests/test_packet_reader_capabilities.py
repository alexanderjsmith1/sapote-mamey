"""Capability failures refuse completed packets without changing integrity or opening members."""
from pathlib import Path
from types import SimpleNamespace
import os,sys,importlib.util
import pytest
SOURCE=Path(os.environ.get('LANE06_PACKET_QC',Path(__file__).resolve().parents[1]/'tools/figure_render_qc.py'))
spec=importlib.util.spec_from_file_location('packet_capability_qc',SOURCE);qc=importlib.util.module_from_spec(spec);spec.loader.exec_module(qc)
from tests.test_completed_render_packet import packet,sha

def proxy():return SimpleNamespace(**{name:getattr(os,name) for name in dir(os)})

@pytest.mark.parametrize('missing',['O_DIRECTORY','O_NOFOLLOW','O_NONBLOCK','supports_dir_fd'])
def test_missing_required_capability_refuses_before_member_open(tmp_path,monkeypatch,missing):
    folder,png,receipt,payload=packet(tmp_path);fake=proxy();delattr(fake,missing);opened=[]
    def forbidden(*args,**kwargs):opened.append(args);raise AssertionError('Unsupported capability must refuse before any file open')
    fake.open=forbidden;fake.supports_dir_fd={forbidden} if missing!='supports_dir_fd' else set()
    monkeypatch.setattr(qc,'_os',fake)
    assert qc.main([str(folder),'--out',str(tmp_path/'qa'),'--ocr','off'])==2
    assert not opened and not (tmp_path/'qa').exists()

@pytest.mark.parametrize('error',[NotImplementedError,TypeError])
def test_runtime_rejection_of_dirfd_is_typed_refusal_and_closes_handles(tmp_path,monkeypatch,error):
    folder,png,receipt,payload=packet(tmp_path);fake=proxy();opened=[];closed=[]
    def unsupported(path,flags,**kwargs):
        if 'dir_fd' in kwargs:raise error('Synthetic runtime lacks openat support')
        fd=os.open(path,flags);opened.append(fd);return fd
    def close(fd):closed.append(fd);return os.close(fd)
    fake.open=unsupported;fake.close=close;fake.supports_dir_fd={unsupported};monkeypatch.setattr(qc,'_os',fake)
    assert qc.main([str(folder),'--out',str(tmp_path/'qa'),'--ocr','off'])==2
    assert opened==closed and not (tmp_path/'qa').exists()

def test_advertised_missing_dirfd_support_refuses_before_open(tmp_path,monkeypatch):
    folder,png,receipt,payload=packet(tmp_path);fake=proxy();fake.supports_dir_fd=set();monkeypatch.setattr(qc,'_os',fake)
    assert qc.main([str(folder),'--out',str(tmp_path/'qa'),'--ocr','off'])==2
    assert not (tmp_path/'qa').exists()

def test_supported_local_reader_preserves_bindings(tmp_path):
    folder,png,receipt,payload=packet(tmp_path,transferred=True,modern=True)
    before={p.name:sha(p) for p in folder.iterdir()};assert qc.main([str(folder),'--out',str(tmp_path/'qa'),'--ocr','off','--render-receipt-sha256',sha(receipt)])==0
    assert before=={p.name:sha(p) for p in folder.iterdir()}

def test_unreceipted_QA_does_not_claim_or_require_packet_capabilities(tmp_path,monkeypatch):
    folder,png,receipt,payload=packet(tmp_path);receipt.rename(folder/'RECEIPT_RETAINED.json');fake=proxy();delattr(fake,'O_NOFOLLOW');monkeypatch.setattr(qc,'_os',fake)
    assert qc.main([str(folder),'--out',str(tmp_path/'qa'),'--ocr','off'])==0
    assert 'admitted output bindings verified' not in (tmp_path/'qa/RENDER_QC.md').read_text()
