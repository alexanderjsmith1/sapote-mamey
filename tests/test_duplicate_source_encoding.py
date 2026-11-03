"""Incremental source-byte admission on top of the literal-None candidate."""
import ast
import importlib.util
import json
import os
from pathlib import Path
import sys
import pytest
TARGET=Path(__file__).resolve().parents[1]/'tools/check_duplicate_dict_keys.py'
spec=importlib.util.spec_from_file_location('duplicate_encoding_gate',TARGET);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
BAD=[b'VALUE="\xff"\n',b'#\xff\n',b'# coding: missing_codec\nVALUE=1\n',b'\xef\xbb\xbf# coding: latin-1\nVALUE=1\n']


@pytest.mark.parametrize('payload',BAD)
@pytest.mark.parametrize('mixed',[False,True])
def test_bad_source_bytes_keep_existing_unparsed_exit2(tmp_path,capsys,payload,mixed):
    path=tmp_path/'invalid.py';path.write_bytes(payload)
    if mixed:(tmp_path/'valid.py').write_text('VALUE=1\n')
    assert mod.main(['--root',str(tmp_path),'--json'])==2
    streams=capsys.readouterr()
    assert streams.out==''
    assert 'could not be parsed' in streams.err and 'invalid.py' in streams.err
    assert path.read_bytes()==payload


@pytest.mark.parametrize('encoding,header',[('utf-8',''),('utf-8','# coding: utf-8\n'),('latin-1','# coding: latin-1\n'),('cp1252','# coding: cp1252\n'),('utf-8-sig','')])
def test_valid_encoding_duplicate_key_text_is_exact(tmp_path,encoding,header):
    path=tmp_path/'valid.py';payload=(header+'VALUE={"café":1,"café":2}\n').encode(encoding);path.write_bytes(payload)
    records=list(mod.scan_file(path))
    assert records[0]['duplicate_keys']==['café']
    assert records[0]['entries_lost']==1
    assert path.read_bytes()==payload


@pytest.mark.parametrize('encoding,header,keys',[('latin-1','# coding: latin-1\n',('café','cafï')),('cp1252','# coding: cp1252\n',('€','£')),('utf-8-sig','',('café','cafï'))])
def test_distinct_declared_keys_are_not_lossily_merged(tmp_path,capsys,encoding,header,keys):
    path=tmp_path/'valid.py';path.write_bytes((header+f'VALUE={{{keys[0]!r}:1,{keys[1]!r}:2}}\n').encode(encoding))
    assert list(mod.scan_file(path))==[]
    assert mod.main(['--root',str(path),'--json'])==0
    result=json.loads(capsys.readouterr().out)
    assert result['new']==[] and result['files_scanned']==1


def test_collection_counts_only_parsed_files(tmp_path):
    (tmp_path/'invalid.py').write_bytes(b'VALUE="\xff"\n');(tmp_path/'valid.py').write_text('VALUE=1\n')
    stats={'files':0};unparsed=[]
    assert list(mod.collect([str(tmp_path)],stats,[],unparsed))==[]
    assert stats['files']==1
    assert len(unparsed)==1 and 'invalid.py' in unparsed[0]


def test_card29_none_collision_stays_detected(tmp_path):
    path=tmp_path/'valid.py';path.write_text('VALUE={None:1,None:2}\n')
    assert list(mod.scan_file(path))[0]['duplicate_keys']==['None']


def test_direct_unreadable_file_behavior_unchanged(tmp_path,monkeypatch):
    path=tmp_path/'unreadable.py';path.write_text('VALUE=1\n');original=Path.open
    def deny(selected,*args,**kwargs):
        if selected==path:raise PermissionError('synthetic read refusal')
        return original(selected,*args,**kwargs)
    monkeypatch.setattr(Path,'open',deny)
    with pytest.raises(PermissionError):list(mod.scan_file(path))
