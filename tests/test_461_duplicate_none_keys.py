"""Synthetic static-source controls; no execution of scanned code."""
import ast
import importlib.util
import json
import os
from pathlib import Path
import sys
import pytest
TARGET=Path(__file__).resolve().parents[1]/'tools/check_duplicate_dict_keys.py'
spec=importlib.util.spec_from_file_location('duplicate_under_test',TARGET);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)


def scan(tmp_path,text):
    path=tmp_path/'synthetic.py';path.write_text(text+'\n');return path,list(mod.scan_file(path))


@pytest.mark.parametrize('literal,entries,lost',[('{None:1,None:2}',2,1),('{None:1,None:2,None:3}',3,2),('{"other":0,None:1,None:2}',3,1),('{"nested":{None:1,None:2}}',2,1)])
def test_none_literal_collision_detected(tmp_path,literal,entries,lost):
    _,records=scan(tmp_path,'VALUE='+literal)
    assert len(records)==1
    assert records[0]['duplicate_keys']==['None']
    assert records[0]['entries_written']==entries
    assert records[0]['entries_lost']==lost


@pytest.mark.parametrize('literal',['{None:1}','{None:1,**mapping}','{None:1,computed:2}','{compute():1,compute():2}','{**mapping,**mapping}','{[1]:1,[1]:2}'])
def test_unknown_expansion_and_unsupported_keys_not_guessed(tmp_path,literal):
    _,records=scan(tmp_path,'VALUE='+literal)
    assert records==[]


@pytest.mark.parametrize('literal,key',[('{1:1,True:2,1.0:3}','1'),('{False:1,0:2,0.0:3}','False'),('{(None,):1,(None,):2}','(None,)')])
def test_existing_python_key_equality_preserved(tmp_path,literal,key):
    _,records=scan(tmp_path,'VALUE='+literal)
    assert len(records)==1
    assert records[0]['duplicate_keys']==[key]


def test_ast_expansion_is_missing_node_but_literal_none_is_constant():
    tree=ast.parse('VALUE={None:1,**mapping}');keys=tree.body[0].value.keys
    assert isinstance(keys[0],ast.Constant) and keys[0].value is None
    assert keys[1] is None


def test_public_gate_reports_collision_not_pass(tmp_path,capsys):
    path,_=scan(tmp_path,'VALUE={None:1,None:2}')
    assert mod.main(['--root',str(path),'--json'])==1
    captured=capsys.readouterr();result=json.loads(captured.out)
    assert result['new'][0]['duplicate_keys']==['None']
    assert result['files_scanned']==1


def test_allowlist_and_strict_mode_stay_distinct(tmp_path,monkeypatch,capsys):
    path,_=scan(tmp_path,'VALUE={None:1,None:2}')
    monkeypatch.setattr(mod,'ALLOWLIST',{path.as_posix():'synthetic intentional collision'})
    assert mod.main(['--root',str(path),'--json'])==0
    result=json.loads(capsys.readouterr().out)
    assert len(result['allowlisted'])==1 and not result['new']
    assert mod.main(['--root',str(path),'--strict','--json'])==1
