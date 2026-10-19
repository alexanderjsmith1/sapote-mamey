from pathlib import Path
import os,json,hashlib,importlib.util
import pytest
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path(os.environ.get('LANE06_PACKET_QC',ROOT/'tools/figure_render_qc.py'))
spec=importlib.util.spec_from_file_location('completed_packet_qc',SOURCE);qc=importlib.util.module_from_spec(spec);spec.loader.exec_module(qc)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def packet(tmp_path,transferred=False,modern=False):
    folder=tmp_path/'packet';folder.mkdir();png=folder/'PAGE.png'
    image=Image.new('RGB',(600,400),'white');ImageDraw.Draw(image).rectangle((30,30,540,350),fill='navy');image.save(png,dpi=(300,300));image.save(folder/'PAGE_plot_only.png',dpi=(300,300))
    (folder/'PAGE.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"><text>Synthetic software control</text></svg>')
    (folder/'PAGE.pdf').write_bytes(b'%PDF-self-authored-existence-fixture-only')
    (folder/'PAGE_CAPTION.md').write_text('Synthetic control caption. Two observations.\n');(folder/'page.json').write_text('{"synthetic_n":2}\n')
    origin=Path('/unopened/synthetic_transfer_origin') if transferred else folder
    payload=dict(completion_state='COMPLETE',args=dict(out=str(origin)),outputs=[dict(path=str(origin/p.name),state='PRESENT',bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(folder.iterdir())])
    if modern:
        payload['artifact_root']=str(origin);payload['args']['out']='relative_original_cli_out'
        for rec in payload['outputs']:rec['relative_path']=Path(rec['path']).name
    receipt=folder/'render_receipt.json';receipt.write_text(json.dumps(payload));return folder,png,receipt,payload

def errors(flags):return [text for level,text in flags if level=='error']

@pytest.mark.parametrize('member',['PAGE_CAPTION.md','PAGE.png','page.json'])
def test_old_COMPLETE_does_not_admit_edited_member(tmp_path,member):
    folder,png,receipt,payload=packet(tmp_path)
    if member.endswith('.png'):
        image=Image.open(folder/member);ImageDraw.Draw(image).rectangle((60,60,200,200),fill='red');image.save(folder/member,dpi=(300,300))
    else:(folder/member).write_text('Edited synthetic member.\n')
    assert json.loads(receipt.read_text())['completion_state']=='COMPLETE'
    with pytest.raises(qc.RenderPacketAdmissionRefusal, match='completed output changed or missing'):
        qc.run([folder],tmp_path/'fresh_qa',ocr_mode='off')
    assert not (tmp_path/'fresh_qa').exists()

@pytest.mark.parametrize('transferred',[False,True])
@pytest.mark.parametrize('modern',[False,True])
def test_clean_packet_and_lexical_transfer_are_bound(tmp_path,transferred,modern):
    folder,png,receipt,payload=packet(tmp_path,transferred,modern)
    flags=qc.completed_packet_flags(png,sha(receipt));assert not errors(flags)
    assert any('admitted output bindings verified' in text for _,text in flags)
    result=qc.run([folder],tmp_path/'fresh_qa',ocr_mode='off',expected_render_receipt_sha256=sha(receipt));assert not any(errors(flags) for _,flags in result)
    assert not any(level=='not_checked' for _,flags in result for level,_ in flags),'Valid info findings must not disable bound SVG text'

def test_missing_member_is_detected_without_deleting_control(tmp_path):
    folder,png,receipt,payload=packet(tmp_path);(folder/'page.json').rename(folder/'page_RETAINED_MISSING_CONTROL.json')
    assert errors(qc.completed_packet_flags(png))

def test_foreign_origin_locator_is_refused_before_open(tmp_path):
    folder,png,receipt,payload=packet(tmp_path);payload['outputs'][0]['path']='/unopened/outside_root/private.json';receipt.write_text(json.dumps(payload))
    assert any('outside the original artifact root' in text for text in errors(qc.completed_packet_flags(png)))

def test_duplicate_output_locator_is_refused(tmp_path):
    folder,png,receipt,payload=packet(tmp_path);payload['outputs'].append(payload['outputs'][0]);receipt.write_text(json.dumps(payload))
    assert any('duplicate output locator' in text for text in errors(qc.completed_packet_flags(png)))

def test_symlink_member_is_refused(tmp_path):
    folder,png,receipt,payload=packet(tmp_path);p=folder/'page.json';p.rename(folder/'page_RETAINED_SYMLINK_CONTROL.json');p.symlink_to(folder/'page_RETAINED_SYMLINK_CONTROL.json')
    assert any('symlink' in text for text in errors(qc.completed_packet_flags(png)))

def test_incomplete_marker_is_refused(tmp_path):
    folder,png,receipt,payload=packet(tmp_path);payload['completion_state']='INCOMPLETE';receipt.write_text(json.dumps(payload))
    assert errors(qc.completed_packet_flags(png))

def test_external_receipt_hash_detects_receipt_edit(tmp_path):
    folder,png,receipt,payload=packet(tmp_path);admitted=sha(receipt);payload['note']='edited receipt';receipt.write_text(json.dumps(payload))
    assert any('admitted transfer binding' in text for text in errors(qc.completed_packet_flags(png,admitted)))

@pytest.mark.parametrize('unbound',['PAGE_CAPTION.md','PAGE.svg'])
def test_consumed_caption_or_SVG_must_be_in_roster(tmp_path,unbound):
    folder,png,receipt,payload=packet(tmp_path);payload['outputs']=[r for r in payload['outputs'] if Path(r['path']).name!=unbound];receipt.write_text(json.dumps(payload))
    assert any('outside the completed roster' in text for text in errors(qc.completed_packet_flags(png)))

def test_QA_write_collision_refuses_before_changing_packet(tmp_path):
    folder,png,receipt,payload=packet(tmp_path);before={p.name:sha(p) for p in folder.iterdir()}
    with pytest.raises(qc.RenderPacketWriteConflict):qc.run([folder],folder,ocr_mode='off')
    assert qc.main([str(folder),'--out',str(folder),'--ocr','off'])==2
    assert {p.name:sha(p) for p in folder.iterdir()}==before

def test_duplicate_JSON_marker_is_refused(tmp_path):
    folder,png,receipt,payload=packet(tmp_path);text=receipt.read_text();receipt.write_text(text.replace('"completion_state": "COMPLETE"','"completion_state": "INCOMPLETE", "completion_state": "COMPLETE"'))
    assert any('duplicate JSON key' in text for text in errors(qc.completed_packet_flags(png)))

def test_relative_locator_must_match_original_binding(tmp_path):
    folder,png,receipt,payload=packet(tmp_path,modern=True);payload['outputs'][0]['relative_path']='different.json';receipt.write_text(json.dumps(payload))
    assert any('locators disagree' in text for text in errors(qc.completed_packet_flags(png)))
