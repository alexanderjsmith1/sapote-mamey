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

@pytest.mark.parametrize('mode',['sent','returned','both'])
def test_hex_case_does_not_create_false_byte_hold(tmp_path,mode):
    root,sent,back,row=prepared(tmp_path)
    if mode in {'sent','both'}:table(sent,[{'member':'item','sha256':'A'*64}])
    if mode in {'returned','both'}:row['returned_sha256']=row['returned_sha256'].upper()
    table(back,[row]);out=tool.reconcile(sent,back,root)
    assert out['status']=='BYTE_BINDINGS_CHECKED'
    assert out['rows'][0]['acceptance']=='NOT_ESTABLISHED'
