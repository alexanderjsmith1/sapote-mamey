"""Synthetic JSON record admission only; no real dataset or chemistry operations."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import pytest
import mamey
BUNDLE=Path(mamey.__file__).resolve().parent.parent
TARGET=Path(__file__).resolve().parents[1]/'mamey/npatlas_provision.py'
spec=importlib.util.spec_from_file_location('mamey._npatlas_record_shape_candidate',TARGET)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)

@pytest.fixture(autouse=True)
def scoped_frontdoor_binding(monkeypatch):
    monkeypatch.setitem(sys.modules, 'mamey.npatlas_provision', mod)
    monkeypatch.setattr(mamey, 'npatlas_provision', mod, raising=False)
GOOD={'synthetic_id':'software-1','nested_metadata':{'array':[None,1,True]},'tags':['a','b']}


@pytest.mark.parametrize('bad',[None,False,7,'metadata',[]])
@pytest.mark.parametrize('wrapped',[False,True])
@pytest.mark.parametrize('operation',['inspect','provision'])
def test_mixed_nonobject_record_refuses_preserves_sources_outputs(tmp_path,bad,wrapped,operation):
    records=[GOOD,bad,{'synthetic_id':'software-3'}]
    payload={'metadata':{'version':'synthetic','anything':[None,[]]},'compounds':records} if wrapped else records
    source=tmp_path/'source.json';source.write_text(json.dumps(payload));before=source.read_bytes()
    out=tmp_path/'retained_output.json';out.write_text('retained bytes')
    with pytest.raises(mod.NpatlasProvisionError,match='JSON record 2.*not an object'):
        if operation=='inspect':mod.inspect_source(str(source))
        else:mod.provision(str(source),str(out),[])
    assert source.read_bytes()==before
    assert out.read_text()=='retained bytes'
    assert sorted(p.name for p in tmp_path.iterdir())==['retained_output.json','source.json']


@pytest.mark.parametrize('normalize',[False,True])
def test_refusal_before_new_output_parent_creation(tmp_path,normalize):
    source=tmp_path/'source.json';source.write_text(json.dumps([GOOD,None]));out=tmp_path/'new/output.json'
    with pytest.raises(mod.NpatlasProvisionError):mod.provision(str(source),str(out),[],normalize=normalize)
    assert not out.parent.exists()


@pytest.mark.parametrize('wrapped',[False,True])
def test_valid_empty_array_remains_successful_zero(tmp_path,wrapped):
    source=tmp_path/'source.json';source.write_text(json.dumps({'compounds':[]} if wrapped else []))
    assert mod.inspect_source(str(source))['total_records']==0
    receipt=mod.provision(str(source),str(tmp_path/'output.json'),[])
    assert receipt.included_count==receipt.excluded_count==0


def test_nested_values_and_wrapper_metadata_preserved(tmp_path):
    source=tmp_path/'source.json';source.write_text(json.dumps({'metadata':['irrelevant',None,[]],'compounds':[GOOD]}))
    assert list(mod.iter_json_records(str(source)))==[GOOD]
    receipt=mod.provision(str(source),str(tmp_path/'output.json'),[])
    assert receipt.included_count==1
    assert json.loads((tmp_path/'output.json').read_text())['compounds']==[GOOD]


def test_explicit_nested_array_root_supported(tmp_path):
    source=tmp_path/'source.json';source.write_text(json.dumps({'groups':[[GOOD]]}))
    assert list(mod.iter_json_records(str(source),root_prefix='groups.item.item'))==[GOOD]
    assert mod.inspect_source(str(source),root_prefix='groups.item.item')['total_records']==1


def test_filter_counts_unchanged_for_valid_objects(tmp_path):
    source=tmp_path/'source.json';source.write_text(json.dumps([{'synthetic_id':'keep'},{'synthetic_id':'exclude'}]))
    receipt=mod.provision(str(source),str(tmp_path/'output.json'),[mod.FilterClause('synthetic_id','eq','keep')])
    assert receipt.included_count==receipt.excluded_count==1


@pytest.mark.parametrize('command',['inspect','provision'])
def test_operator_frontdoor_refuses_without_stdout_or_output_changes(tmp_path,capsys,command):
    spec=importlib.util.spec_from_file_location('npatlas_front_under_test',BUNDLE/'tools/npatlas_provision.py')
    front=importlib.util.module_from_spec(spec);spec.loader.exec_module(front)
    source=tmp_path/'source.json';source.write_text(json.dumps([GOOD,None]));output=tmp_path/'retained.json';output.write_text('retained')
    args=[command,'--source',str(source)]
    args+=['--out',str(output)] if command=='provision' else ['--out-json',str(output)]
    assert front.main(args)==1
    streams=capsys.readouterr()
    assert streams.out==''
    assert 'NPATLAS_PROVISION_REFUSAL' in streams.err
    assert output.read_text()=='retained'
