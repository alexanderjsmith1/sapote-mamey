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

@pytest.mark.parametrize('value',[None,[], 'not an object',0,True])
def test_nonobject_manifest_has_typed_input_receipt(prepared,value):
    root,manifest,html,out=prepared;manifest.write_text(json.dumps(value))
    assert tool.main(['--root',str(root),'--manifest',str(manifest),'--receipt',str(out)])==1
    receipt=json.loads(out.read_text());assert receipt['status']=='FAIL_INPUT_CONTRACT'
    assert receipt['errors'][0]['code']=='INPUT_CONTRACT_ERROR'

@pytest.mark.parametrize('reason',[42,None])
def test_nonstr_reason_has_typed_input_receipt(prepared,reason):
    root,manifest,html,out=prepared;value=json.loads(manifest.read_text());value['optional_provenance']=[{'from':'index.html','url':'https://example.org/source','reason':reason}];manifest.write_text(json.dumps(value))
    assert tool.main(['--root',str(root),'--manifest',str(manifest),'--receipt',str(out)])==1
    assert json.loads(out.read_text())['status']=='FAIL_INPUT_CONTRACT'
