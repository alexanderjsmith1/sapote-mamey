"""No packet refusal or report collision may alter existing QA evidence."""
import builtins,json,hashlib
from pathlib import Path
import pytest
from tests.test_completed_render_packet import qc,packet,sha

@pytest.mark.parametrize('receipt_state',['bad_pin','malformed','missing','incomplete'])
@pytest.mark.parametrize('destination',['default','explicit','fresh'])
def test_receipt_refusal_preserves_packet_before_OCR(tmp_path,monkeypatch,receipt_state,destination):
    folder,png,receipt,payload=packet(tmp_path)
    # Bind original QA evidence, exactly the parent reproduction shape.
    (folder/'RENDER_QC.md').write_text('Original bound QA evidence.\n')
    payload['outputs'].append(dict(path=str(folder/'RENDER_QC.md'),bytes=(folder/'RENDER_QC.md').stat().st_size,sha256=sha(folder/'RENDER_QC.md')))
    receipt.write_text(json.dumps(payload));pin=sha(receipt)
    if receipt_state=='bad_pin':pin='0'*64
    elif receipt_state=='malformed':receipt.write_text('{ malformed')
    elif receipt_state=='missing':receipt.rename(folder/'receipt_RETAINED.json')
    else:payload['completion_state']='INCOMPLETE';receipt.write_text(json.dumps(payload))
    before={p.name:sha(p) for p in folder.iterdir()}
    def forbidden(*a,**kw):raise AssertionError('OCR/content QA must not run after admission refusal')
    monkeypatch.setattr(qc,'Ocr',forbidden)
    argv=[str(folder),'--ocr','require','--render-receipt-sha256',pin]
    out=folder if destination!='fresh' else tmp_path/'fresh_qa'
    if destination!='default':argv += ['--out',str(out)]
    assert qc.main(argv)==2
    assert {p.name:sha(p) for p in folder.iterdir()}==before
    if destination=='fresh':assert not out.exists()

@pytest.mark.parametrize('name',['RENDER_QC.md','RENDER_QC.tsv'])
@pytest.mark.parametrize('symlink',[False,True])
def test_existing_report_protected_without_any_receipt(tmp_path,monkeypatch,name,symlink):
    folder,png,receipt,payload=packet(tmp_path);receipt.rename(folder/'receipt_RETAINED.json')
    target=folder/'original_evidence.txt';target.write_text('Keep original.\n')
    report=folder/name
    if symlink:report.symlink_to(target)
    else:report.write_text('Keep original report.\n')
    before={p.name:sha(p) for p in folder.iterdir()}
    monkeypatch.setattr(qc,'completed_packet_flags',lambda *a:pytest.fail('report protection must precede receipt parsing'))
    assert qc.main([str(folder),'--ocr','off'])==2
    assert {p.name:sha(p) for p in folder.iterdir()}==before
    assert report.is_symlink()==symlink

@pytest.mark.parametrize('location',['child','sibling'])
def test_valid_transferred_packet_can_write_fresh_QA(tmp_path,location):
    folder,png,receipt,payload=packet(tmp_path,transferred=True,modern=True)
    before={p.name:sha(p) for p in folder.iterdir()};out=(folder/'fresh_qa') if location=='child' else tmp_path/'fresh_qa'
    assert qc.main([str(folder),'--out',str(out),'--ocr','off','--render-receipt-sha256',sha(receipt)])==0
    assert (out/'RENDER_QC.md').is_file() and (out/'RENDER_QC.tsv').is_file()
    assert {name:sha(folder/name) for name in before}==before
    original={name:sha(out/name) for name in ['RENDER_QC.md','RENDER_QC.tsv']}
    assert qc.main([str(folder),'--out',str(out),'--ocr','off'])==2
    assert {name:sha(out/name) for name in original}==original

def test_exclusive_writer_survives_destination_appearing_after_admission(tmp_path,monkeypatch):
    out=tmp_path/'qa';out.mkdir();real_open=builtins.open
    def raced(path,*args,**kw):
        if Path(path).name=='RENDER_QC.md':Path(path).write_text('Concurrent evidence.\n')
        return real_open(path,*args,**kw)
    monkeypatch.setattr(builtins,'open',raced)
    with pytest.raises(qc.RenderPacketWriteConflict,match='appeared'):
        qc.write_reports([],out,[])
    assert (out/'RENDER_QC.md').read_text()=='Concurrent evidence.\n'
    assert (out/'RENDER_QC.tsv').read_bytes()==b''
