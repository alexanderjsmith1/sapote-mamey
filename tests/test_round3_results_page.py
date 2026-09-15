"""The entry page must not hide incomplete evidence behind a success badge."""
import json
import pytest
from mamey.package_addons import write_open_me_first

@pytest.mark.parametrize('status,gate_status,findings,label',[
    ('MAMEY_COMPLETE_WITH_ISSUES','MAMEY_COMPLETE',[],'EXTRACTION HAS ISSUES'),
    ('MAMEY_COMPLETE','MAMEY_COMPLETE',['MAIN_JSON_WALKER_TRUNCATED'],'EXTRACTION HAS ISSUES'),
    ('MAMEY_COMPLETE','FAIL',[],'VALIDATION OR PIPELINE FAILURE'),
    ('INCOMPLETE','UNKNOWN',[],'STATUS UNRESOLVED'),
])
def test_distinct_statuses(tmp_path,status,gate_status,findings,label):
    (tmp_path/'manifest.json').write_text(json.dumps({'strain_id':'DEMO','terminal_status':status}))
    (tmp_path/'manifest_short.json').write_text(json.dumps({'status':'MAMEY_COMPLETE'}))
    (tmp_path/'gate_validation.json').write_text(json.dumps({'status':gate_status,'gold_completeness':'JUDGMENT_PENDING','json_evidence_visibility':{'status':'ADVISORY_FINDINGS','findings':findings}}))
    text=write_open_me_first(tmp_path).read_text()
    assert label in text
    assert 'JUDGMENT_PENDING' in text
    assert gate_status in text and status in text
    assert 'your Claude session' not in text
    assert 'top chemistry' not in text
    for finding in findings: assert finding in text

@pytest.mark.parametrize('duplicate',[False,True])
def test_lead_identity_is_bound_to_one_full_source_record(tmp_path,duplicate):
    record={'bgc_id':'BGC001','contig':'NODE_FULL.1','antismash_region':'region003'}
    (tmp_path/'manifest.json').write_text(json.dumps({'strain_id':'DEMO','bgcs':[record]*(2 if duplicate else 1)}))
    (tmp_path/'manifest_short.json').write_text(json.dumps({'top_3_ab':[{'bgc_id':'BGC001','contig':'NODE_FULL.1','ab_score':40}]}))
    text=write_open_me_first(tmp_path).read_text()
    assert ('IDENTITY HOLD' if duplicate else 'DEMO / NODE_FULL.1 / region003 / BGC001') in text

def test_present_malformed_gate_is_not_hidden(tmp_path):
    (tmp_path/'gate_validation.json').write_text('{broken')
    with pytest.raises(ValueError,match='gate_validation.json'):
        write_open_me_first(tmp_path)
