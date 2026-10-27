from pathlib import Path
import os
import json
import hashlib
import importlib.util
import zipfile
import pytest
ROOT=Path(os.environ.get('DELIVERY_REVIEW_BASE',Path(__file__).resolve().parents[1]))
spec=importlib.util.spec_from_file_location('delivery_preservation_review',ROOT/'tools/standalone_delivery_audit.py')
tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)
@pytest.fixture
def prepared(tmp_path):
    root=tmp_path/'delivery';root.mkdir();html=root/'index.html';html.write_bytes(b'<h1>Bound delivery</h1>')
    manifest=tmp_path/'manifest.json';manifest.write_text(json.dumps({'schema':tool.SCHEMA,'entrypoints':['index.html'],'files':[{'path':'index.html','bytes':html.stat().st_size,'sha256':hashlib.sha256(html.read_bytes()).hexdigest()}]}))
    return root,manifest,html,tmp_path/'receipt.json'
def invoke(args):
    try:return tool.main(args)
    except SystemExit as e:return e.code

@pytest.mark.parametrize('kind',['manifest','html','zip'])
def test_receipt_hardlink_cannot_modify_input(prepared,kind):
    root,manifest,html,out=prepared
    args=['--root',str(root),'--manifest',str(manifest),'--receipt',str(out)]
    protected=manifest if kind=='manifest' else html
    if kind=='zip':
        protected=root.parent/'delivery.zip'
        with zipfile.ZipFile(protected,'w') as z:z.write(html,'index.html')
        args=['--zip',str(protected),'--manifest',str(manifest),'--receipt',str(out)]
    original=protected.read_bytes();os.link(protected,out)
    rc=invoke(args)
    assert protected.read_bytes()==original,'AUDITED_INPUT_MODIFIED_BY_RECEIPT'
    assert out.read_bytes()==original and rc==2

def test_late_receipt_alias_is_refused(prepared,monkeypatch):
    root,manifest,html,out=prepared;original=manifest.read_bytes();audit=tool.audit
    def completed(*args,**kwargs):
        result=audit(*args,**kwargs);os.link(manifest,out);return result
    monkeypatch.setattr(tool,'audit',completed)
    rc=invoke(['--root',str(root),'--manifest',str(manifest),'--receipt',str(out)])
    assert manifest.read_bytes()==original,'AUDITED_INPUT_MODIFIED_BY_LATE_RECEIPT_ALIAS'
    assert out.read_bytes()==original and rc==2

def test_fresh_receipt_still_passes(prepared):
    root,manifest,html,out=prepared;before=(manifest.read_bytes(),html.read_bytes())
    assert tool.main(['--root',str(root),'--manifest',str(manifest),'--receipt',str(out)])==0
    assert json.loads(out.read_text())['status']=='PASS_STATIC_CONTRACT'
    assert (manifest.read_bytes(),html.read_bytes())==before
