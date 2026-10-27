from pathlib import Path
import csv
import io
import json
import hashlib
import importlib.util
import os
import sys
import pytest
ROOT=Path(os.environ.get('ROUND_TRIP_REVIEW_BASE',Path(__file__).resolve().parents[1]))
spec=importlib.util.spec_from_file_location('round_trip_binding_review',ROOT/'tools/round_trip_checkpoint.py')
tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)
def table(path,rows):
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter='\t');writer.writeheader();writer.writerows(rows)
def prepared(tmp_path):
    root=tmp_path/'returns';root.mkdir();item=root/'item.txt';item.write_text('returned bytes')
    sent=tmp_path/'sent.tsv';back=tmp_path/'back.tsv'
    table(sent,[{'member':'item','sha256':'a'*64}])
    row={'item_id':'item','sent_sha256':'a'*64,'returned_path':'item.txt','returned_sha256':hashlib.sha256(item.read_bytes()).hexdigest(),'decision':'PENDING'}
    table(back,[row]);return root,sent,back,row

def run_cli(monkeypatch,root,sent,back,out):
    monkeypatch.setattr(sys,'argv',['round_trip_checkpoint','reconcile','--sent-manifest',str(sent),'--returned',str(back),'--root',str(root),'--out',str(out)])
    try:tool.main();return 0
    except SystemExit as error:return error.code

def test_late_hardlink_cannot_overwrite_manifest(tmp_path,monkeypatch):
    root,sent,back,row=prepared(tmp_path);out=tmp_path/'receipt.json';before=sent.read_bytes();original=Path.is_relative_to;created=[]
    def inside(path,*args):
        answer=original(path,*args)
        if path==out and not created:created.append(True);os.link(sent,out)
        return answer
    monkeypatch.setattr(Path,'is_relative_to',inside)
    rc=run_cli(monkeypatch,root,sent,back,out)
    assert sent.read_bytes()==before,'SENT_MANIFEST_OVERWRITTEN_BY_LATE_RECEIPT'
    assert out.read_bytes()==before and rc==2

def test_dangling_receipt_symlink_is_refused(tmp_path,monkeypatch):
    root,sent,back,row=prepared(tmp_path);out=tmp_path/'receipt.json';target=tmp_path/'target.json';out.symlink_to(target)
    rc=run_cli(monkeypatch,root,sent,back,out)
    assert out.is_symlink() and not target.exists() and rc==2

def test_new_external_receipt_remains_available(tmp_path,monkeypatch):
    root,sent,back,row=prepared(tmp_path);out=tmp_path/'receipt.json'
    assert run_cli(monkeypatch,root,sent,back,out)==0
    assert json.loads(out.read_text())['status']=='BYTE_BINDINGS_CHECKED'

def test_symlink_created_during_resolution_is_refused(tmp_path,monkeypatch):
    root,sent,back,row=prepared(tmp_path);out=tmp_path/'receipt.json';target=tmp_path/'late-target.json';original=Path.resolve;created=[]
    def resolving(path,*args,**kwargs):
        if path==out and not created:
            created.append(True);out.symlink_to(target)
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'resolve',resolving)
    rc=run_cli(monkeypatch,root,sent,back,out)
    assert out.is_symlink() and not target.exists() and rc==2
