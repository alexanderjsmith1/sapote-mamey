"""Deterministic late edits must never change the bytes consumed by completed-packet QA."""
from pathlib import Path
import builtins,hashlib,json
import pytest
from tests.test_completed_render_packet import qc,packet,sha

@pytest.mark.parametrize('phase',['ocr_init','after_content','before_writer'])
@pytest.mark.parametrize('member',['caption','SVG','PNG','receipt','unconsumed'])
def test_late_generation_change_refuses_without_reports(tmp_path,monkeypatch,phase,member):
    folder,png,receipt,payload=packet(tmp_path);pin=sha(receipt);original_caption=(folder/'PAGE_CAPTION.md').read_text();observed=[]
    def mutate():
        if member=='caption':(folder/'PAGE_CAPTION.md').write_text('Late different generation. Three observations.\n')
        elif member=='SVG':
            target=tmp_path/'foreign_fixture.svg';target.write_text('<svg xmlns="http://www.w3.org/2000/svg"><text>Late different SVG</text></svg>')
            (folder/'PAGE.svg').rename(folder/'SVG_RETAINED_ORIGINAL.svg');(folder/'PAGE.svg').symlink_to(target)
        elif member=='PNG':(folder/'PAGE.png').write_bytes(b'late bytes no valid image')
        elif member=='receipt':receipt.write_text(receipt.read_text()+'\n')
        else:(folder/'page.json').write_text('{"changed":true}')
    real_Ocr=qc.Ocr
    class MutatingOcr(real_Ocr):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            if phase=='ocr_init':mutate()
    monkeypatch.setattr(qc,'Ocr',MutatingOcr)
    real_caption=qc.check_caption
    def read_caption(text,**kwargs):observed.append(text);return real_caption(text,**kwargs)
    monkeypatch.setattr(qc,'check_caption',read_caption)
    real_files=qc.check_files
    def after_content(*args,**kwargs):
        flags=real_files(*args,**kwargs)
        if phase=='after_content':mutate()
        return flags
    monkeypatch.setattr(qc,'check_files',after_content)
    real_writer=qc.write_reports
    def before_writer(*args,**kwargs):
        if phase=='before_writer':mutate()
        return real_writer(*args,**kwargs)
    monkeypatch.setattr(qc,'write_reports',before_writer)
    out=tmp_path/'qa';assert qc.main([str(folder),'--out',str(out),'--ocr','off','--render-receipt-sha256',pin,'--warn-only'])==2
    assert not (out/'RENDER_QC.md').exists() and not (out/'RENDER_QC.tsv').exists()
    assert observed[-1]==original_caption
    assert not any('Late different' in text for text in observed)

@pytest.mark.parametrize('role',['caption','SVG'])
def test_new_unbound_companion_cannot_appear_after_admission(tmp_path,monkeypatch,role):
    folder,png,receipt,payload=packet(tmp_path)
    name='PAGE_CAPTION.md' if role=='caption' else 'PAGE.svg';(folder/name).rename(folder/('RETAINED_'+name));payload['outputs']=[r for r in payload['outputs'] if Path(r['path']).name!=name];receipt.write_text(json.dumps(payload));pin=sha(receipt)
    real=qc.Ocr
    class Insert(real):
        def __init__(self,*a,**kw):super().__init__(*a,**kw);(folder/name).write_text('New unbound companion.\n')
    monkeypatch.setattr(qc,'Ocr',Insert)
    assert qc.main([str(folder),'--out',str(tmp_path/'qa'),'--ocr','off','--render-receipt-sha256',pin])==2
    assert not (tmp_path/'qa/RENDER_QC.md').exists()

def test_bound_PNG_without_SVG_OCR_reads_admitted_snapshot(tmp_path,monkeypatch):
    folder,png,receipt,payload=packet(tmp_path);svg=folder/'PAGE.svg';svg.rename(folder/'RETAINED_SVG.svg');payload['outputs']=[r for r in payload['outputs'] if Path(r['path']).name!='PAGE.svg'];receipt.write_text(json.dumps(payload))
    cache=tmp_path/'cache';cache.mkdir();ocr=qc.Ocr.__new__(qc.Ocr);ocr.bin=tmp_path/'fake_ocr';ocr.cache_file=cache/'ocr.tsv';ocr.cache={};ocr.reason='';raw=png.read_bytes();calls=[]
    def execute(command,**kw):
        path=Path(command[1]);calls.append(path);assert path!=png and path.read_bytes()==raw
        return qc.subprocess.CompletedProcess(command,0,str(path)+'\tBound synthetic image\n','')
    monkeypatch.setattr(qc.subprocess,'run',execute)
    assert ocr.read({png:sha(png)},admitted_bytes={png:raw})[png]==['Bound synthetic image']
    assert len(calls)==1 and calls[0].name==sha(png)+'.png'

def test_preexisting_snapshot_symlink_is_never_opened(tmp_path,monkeypatch):
    cache=tmp_path/'cache';cache.mkdir();snap=cache/'admitted_pngs';snap.mkdir();image=tmp_path/'image.png';image.write_bytes(b'synthetic bound PNG bytes');raw=image.read_bytes();target=tmp_path/'foreign.txt';target.write_text('Foreign evidence.\n');(snap/(sha(image)+'.png')).symlink_to(target)
    ocr=qc.Ocr.__new__(qc.Ocr);ocr.bin=tmp_path/'fake';ocr.cache_file=cache/'ocr.tsv';ocr.cache={};ocr.reason=''
    monkeypatch.setattr(qc.subprocess,'run',lambda *a,**kw:pytest.fail('OCR must not run on symlink snapshot'))
    with pytest.raises(qc.RenderPacketAdmissionRefusal,match='snapshot refused'):ocr.read({image:sha(image)},admitted_bytes={image:raw})
    assert target.read_text()=='Foreign evidence.\n'

def test_nested_packet_member_parent_symlink_refuses_before_read(tmp_path):
    root=tmp_path/'root';root.mkdir();foreign=tmp_path/'foreign';foreign.mkdir();(foreign/'opaque').write_text('Foreign fixture.\n');(root/'nested').symlink_to(foreign,target_is_directory=True)
    with pytest.raises(OSError):qc._packet_read(root,Path('nested/opaque'))
