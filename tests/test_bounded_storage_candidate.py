import importlib
import io
import json
import zipfile
import pytest
from mamey import antismash_evidence as ae
from mamey.json_evidence_state import project, read_package_state, describe
from mamey.validate import _json_evidence_visibility

@pytest.fixture(autouse=True, params=['selected','python'])
def backend(request,monkeypatch):
    assert ae._HAVE_IJSON
    if request.param=='python':monkeypatch.setattr(ae,'ijson',importlib.import_module('ijson.backends.python'))

def modules(score,region='1'):
    return {'cluster_compare':{'by_region':{region:{'RegionToRegion_RiQ':{'scores_by_region':{'ref':score}}}}}}

def record(rid,score):
    return {'clusterblast':{'a':'one','b':'two'},'modules':modules(score),'id':rid}

def parse(doc):
    data=doc if isinstance(doc,str) else json.dumps(doc)
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as z:z.writestr('evidence.json',data)
    stream.seek(0);ev={'by_region':{},'loose_hits':[],'json_files':['evidence.json'],'json_mode':'bounded','json_mode_requested':'bounded'}
    with zipfile.ZipFile(stream) as z:ae._parse_json_bounded(z,'evidence.json',ev)
    return ev

def scores(ev):return {k:max(r['riq_score'] for r in v if 'riq_score' in r) for k,v in ev['by_region'].items()}
def channels(ev):return {r['channel']:r for r in project(ev)['channels']}

def test_cap_then_late_id_and_later_record(monkeypatch):
    monkeypatch.setattr(ae,'BOUNDED_MAX_RECORDS_STREAMING',1)
    ev=parse({'records':[record('NODE_A_full',.9),record('NODE_B_full',.4)]})
    assert scores(ev)=={'NODE_A_full_c1':.9,'NODE_B_full_c1':.4}
    w=ev['json_bounded_walks'][0]
    assert w['auxiliary_leaves_kept']==1 and w['auxiliary_truncated'] and w['records_closed']==2
    assert w['riq_observations_seen']==w['riq_observations_mapped']==2
    assert channels(ev)['Main JSON auxiliary']['state']=='TRUNCATED'
    assert channels(ev)['RiQ']['state']=='READ_COMPLETE_FOR_SELECTED_SCORES'

def test_malformed_record_after_exhausted_auxiliary_store_stays_unassigned(monkeypatch):
    monkeypatch.setattr(ae,'BOUNDED_MAX_RECORDS_STREAMING',1)
    ev=parse('{"records":['+json.dumps(record('NODE_A',.2))+','+json.dumps(record('NODE_B',.99))[:-1])
    assert scores(ev)=={'NODE_A_c1':.2}
    assert ev['json_bounded_walks'][0]['walk_complete'] is False
    assert ev['riq_unmapped_count']==1 and ev['loose_hits'][-1]['riq_identity_status']=='UNMAPPED_INCOMPLETE_RECORD'
    assert channels(ev)['RiQ']['state']=='PARSE_HELD'

@pytest.mark.parametrize('duplicate',['"NODE_A"','"NODE_B"','null','{}'])
def test_duplicate_id_after_cap_never_assigns(monkeypatch,duplicate):
    monkeypatch.setattr(ae,'BOUNDED_MAX_RECORDS_STREAMING',1)
    raw='{"records":[{"id":"NODE_A","clusterblast":{"a":"one","b":"two"},"modules":'+json.dumps(modules(.9))+',"id":'+duplicate+'}]}'
    ev=parse(raw)
    assert not scores(ev) and ev['riq_unmapped_count']==1
    assert channels(ev)['RiQ']['state']=='IDENTITY_HELD'

def test_missing_identity_after_cap_does_not_inherit(monkeypatch):
    monkeypatch.setattr(ae,'BOUNDED_MAX_RECORDS_STREAMING',1)
    ev=parse({'records':[record('NODE_A',.1),{'modules':modules(.99)},record('NODE_C',.4)]})
    assert scores(ev)=={'NODE_A_c1':.1,'NODE_C_c1':.4} and ev['riq_unmapped_count']==1
    assert channels(ev)['RiQ']['state']=='IDENTITY_HELD'

def test_independent_group_budget_preserves_maximum_and_counts(monkeypatch):
    monkeypatch.setattr(ae,'BOUNDED_MAX_RIQ_GROUPS',1)
    first=record('NODE_A',.1)
    first['modules']['cluster_compare']['by_region']['1']['RegionToRegion_RiQ']['scores_by_region']['ref2']=.9
    ev=parse({'records':[first,record('NODE_B',.8)]})
    assert scores(ev)=={'NODE_A_c1':.9}
    w=ev['json_bounded_walks'][0]
    assert w['riq_groups_kept']==1 and w['riq_observations_seen']==3 and w['riq_observations_mapped']==2 and w['riq_observations_held']==1
    assert channels(ev)['RiQ']['state']=='STORAGE_HELD' and ev['json_bounded_truncated'] is True

def test_outside_record_storage_is_bounded(monkeypatch):
    monkeypatch.setattr(ae,'BOUNDED_MAX_RIQ_GROUPS',2)
    ev=parse({'other':{'cluster_compare':{'by_region':{'1':{
        'RegionToRegion_RiQ':{'scores_by_region':{str(n):.5 for n in range(100)}}}}}}})
    w=ev['json_bounded_walks'][0]
    assert len(ev['loose_hits'])==2 and w['riq_observations_unassigned']==2 and w['riq_observations_held']==98
    assert w['riq_observations_seen']==100 and channels(ev)['RiQ']['state']=='STORAGE_HELD'

def test_bad_receipt_arithmetic_is_conflict():
    ev=parse({'records':[record('NODE_A',.1)]})
    ev['json_bounded_walks'][0]['riq_observations_seen']=7
    assert channels(ev)['RiQ']['state']=='RECEIPT_CONFLICT'

def test_missing_receipt_is_not_complete():
    ev={'json_mode':'bounded','json_bounded_truncated':False}
    assert channels(ev)['RiQ']['state']=='UNKNOWN'

def test_byte_cap_is_separate_from_record_pass(monkeypatch,tmp_path):
    monkeypatch.setattr(ae,'BOUNDED_MAX_JSON_BYTES_STREAMING',10)
    p=tmp_path/'tiny.zip'
    with zipfile.ZipFile(p,'w') as z:z.writestr('evidence.json',json.dumps({'records':[record('NODE_A',.1)]}))
    ev=ae.parse_antismash_evidence(p,json_mode='bounded')
    assert channels(ev)['RiQ']['state']=='PARSE_HELD'
    assert channels(ev)['Record extras']['state']=='READ_COMPLETE_FOR_SELECTED_RECORDS'
    assert 'exceeds bounded cap' in describe(project(ev))

def test_record_handler_error_is_channel_specific(tmp_path):
    p=tmp_path/'bad-handler.zip'
    rec=record('NODE_A',.1)
    rec['modules']['antismash.modules.nrps_pks']={'domain_predictions':None,'consensus':{'domain':'ala'}}
    with zipfile.ZipFile(p,'w') as z:z.writestr('evidence.json',json.dumps({'records':[rec]}))
    ev=ae.parse_antismash_evidence(p,json_mode='bounded',want_tigrfam=True)
    assert channels(ev)['Record extras']['state']=='HANDLER_FAILED'
    assert channels(ev)['TIGRFAM record parse']['state']=='READ_COMPLETE_FOR_SELECTED_RECORDS'

def test_readers_surface_cap_and_bound_receipt(tmp_path,monkeypatch):
    monkeypatch.setattr(ae,'BOUNDED_MAX_RECORDS_STREAMING',1)
    ev=parse({'records':[record('NODE_A',.1)]})
    p=tmp_path/'TEST_AntiSMASH_Evidence_Parse.json';p.write_text(json.dumps(ev))
    state=read_package_state(tmp_path,'TEST');text=describe(state)
    assert 'Main JSON auxiliary=TRUNCATED' in text and 'RiQ=READ_COMPLETE_FOR_SELECTED_SCORES' in text and state['source_receipt_sha256'] in text
    gate=_json_evidence_visibility(tmp_path,[p])['sources'][0]
    assert gate['riq']['state']=='READ_COMPLETE_FOR_SELECTED_SCORES'
    from mamey.compile_report import _rrefinder_evidence_note
    assert text in _rrefinder_evidence_note(tmp_path,'TEST')

def test_symlink_receipt_is_not_admitted(tmp_path):
    outside=tmp_path/'other.json';outside.write_text(json.dumps(parse({'records':[record('NODE_A',.1)]})))
    (tmp_path/'TEST_AntiSMASH_Evidence_Parse.json').symlink_to(outside)
    state=read_package_state(tmp_path,'TEST')
    assert state['read_error']=='ValueError' and state['channels'][1]['state']=='UNKNOWN'
