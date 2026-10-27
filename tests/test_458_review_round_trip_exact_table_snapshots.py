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

def mutate_after_first_read(monkeypatch,target,replacement):
    original=Path.open;seen=[]
    def opening(path,*args,**kwargs):
        raw=original(path,*args,**kwargs)
        if path!=target or seen:return raw
        seen.append(True)
        class Captured:
            def __enter__(self):return raw.__enter__()
            def __exit__(self,*exc):
                value=raw.__exit__(*exc)
                with original(target,'wb') as writer:writer.write(replacement)
                return value
        return Captured()
    monkeypatch.setattr(Path,'open',opening)

def test_inbox_pin_binds_parsed_version(tmp_path,monkeypatch):
    folder=tmp_path/'00 Inbox';folder.mkdir();(folder/'item').mkdir();ledger=folder/'INBOX_LEDGER.tsv'
    row={'id':'item','status':'SUBMITTED','submitted':'2026-10-25 09:00','verified':''};table(ledger,[row]);before=ledger.read_bytes()
    mutate_after_first_read(monkeypatch,ledger,before.replace(b'SUBMITTED',b'APPLIED'))
    out=tool.inbox(tmp_path,tool.dt.datetime(2026,10,26,10,tzinfo=tool.ZONE))
    assert out['waiting'][0]['state']=='SUBMITTED'
    assert out['source']['sha256']==hashlib.sha256(before).hexdigest(),'PIN_DESCRIBES_DIFFERENT_TABLE_VERSION'
    assert out['source']['bytes']==len(before)

@pytest.mark.parametrize('which',['sent','returned'])
def test_reconcile_pin_binds_parsed_version(tmp_path,monkeypatch,which):
    root,sent,back,row=prepared(tmp_path);target=sent if which=='sent' else back;before=target.read_bytes()
    mutate_after_first_read(monkeypatch,target,before.replace(b'item',b'other'))
    out=tool.reconcile(sent,back,root)
    assert out['status']=='BYTE_BINDINGS_CHECKED'
    binding=out['sources'][0 if which=='sent' else 1]
    assert binding['sha256']==hashlib.sha256(before).hexdigest(),'PIN_DESCRIBES_DIFFERENT_TABLE_VERSION'
    assert binding['bytes']==len(before)
