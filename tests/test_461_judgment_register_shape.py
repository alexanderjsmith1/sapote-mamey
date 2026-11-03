"""Synthetic register-container tests; no card/scientific acceptance decisions."""
import importlib.util
import json
import os
from pathlib import Path
import pytest
TARGET=Path(__file__).resolve().parents[1]/'mamey/judgment_store.py'
spec=importlib.util.spec_from_file_location('judgment_under_test',TARGET)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
BAD=[[],None,'invalid',1,True,{'SOFTWARE-ROW':None},{'SOFTWARE-ROW':[]},{'SOFTWARE-ROW':'invalid'},{'SOFTWARE-ROW':1},{'SOFTWARE-ROW':True}]
GOOD={'strain_id':'SYNTHETIC','judgment_status':'PENDING','total_bgcs':1,'complete_bgcs':0,'bgcs':{'SOFTWARE-ROW':{'status':'PENDING'}}}


def package(tmp_path):
    p=tmp_path/'SYNTHETIC';p.mkdir();(p/'manifest.json').write_text(json.dumps({'strain_id':'SYNTHETIC'}));return p,p/'SYNTHETIC_judgment_register.json'


@pytest.mark.parametrize('entries',BAD)
def test_bad_primary_shape_is_corrupt_and_preserved(tmp_path,entries):
    p,path=package(tmp_path);path.write_text(json.dumps({'bgcs':entries}));before=path.read_bytes()
    result=mod.read_register(p)
    assert result['judgment_status']=='CORRUPT'
    assert result['load_errors'][0]['stage']=='load_primary_register'
    assert result['load_errors'][0]['error_type']=='ValueError'
    assert path.read_bytes()==before
    assert any(f.read_bytes()==before for f in p.glob('*.corrupt-*'))


@pytest.mark.parametrize('entries',BAD)
def test_bad_primary_recovers_only_structurally_valid_last_good(tmp_path,entries):
    p,path=package(tmp_path);path.write_text(json.dumps({'bgcs':entries}));before=path.read_bytes()
    last=Path(str(path)+'.last-good');last.write_text(json.dumps(GOOD));last_before=last.read_bytes()
    result=mod.read_register(p)
    assert result['bgcs']==GOOD['bgcs']
    assert result['register_recovery']['status']=='RECOVERED_FROM_LAST_GOOD'
    assert result['register_recovery']['load_errors'][0]['error_type']=='ValueError'
    assert path.read_bytes()==before and last.read_bytes()==last_before


@pytest.mark.parametrize('entries',BAD)
def test_bad_last_good_shape_stays_corrupt(tmp_path,entries):
    p,path=package(tmp_path);path.write_text('{truncated');last=Path(str(path)+'.last-good');last.write_text(json.dumps({'bgcs':entries}));before=last.read_bytes()
    result=mod.read_register(p)
    assert result['judgment_status']=='CORRUPT'
    assert any(e['stage']=='load_last_good' and e['error_type']=='ValueError' for e in result['load_errors'])
    assert last.read_bytes()==before
    assert mod.compile_ready(p)[0] is False


@pytest.mark.parametrize('payload',[{}, {'bgcs':{}}, GOOD, {'bgcs':{'SOFTWARE-ROW':{}}}])
def test_existing_object_forms_preserved(tmp_path,payload):
    p,path=package(tmp_path);path.write_text(json.dumps(payload))
    assert mod.read_register(p)==payload
    assert not list(p.glob('*.corrupt-*'))


def test_reader_helpers_do_not_crash_on_bad_entry_shape(tmp_path):
    p,path=package(tmp_path);path.write_text(json.dumps({'bgcs':{'SOFTWARE-ROW':None}}))
    assert mod.list_complete_bgcs(p)==[]
    assert mod.pending_bgcs(p)==[]
    assert mod.batch_status(p)['compile_ready'] is False
    assert mod.compile_ready(p)[0] is False
    assert mod.read_register(p)['judgment_status']=='CORRUPT'


def test_initializer_refuses_to_overwrite_malformed_history(tmp_path):
    p,path=package(tmp_path);path.write_text(json.dumps({'bgcs':{'SOFTWARE-ROW':None}}));before=path.read_bytes()
    with pytest.raises(ValueError,match='initialisation refused'):
        mod.init_register(p,'SYNTHETIC',['SOFTWARE-ROW'])
    assert path.read_bytes()==before
