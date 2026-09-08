import json
import zipfile
import pytest
from mamey.validate import _json_evidence_visibility, validate_package
from mamey import antismash_evidence as ae
from mamey import cli

def show(tmp_path, ev):
    p=tmp_path/'TEST_AntiSMASH_Evidence_Parse.json';p.write_text(json.dumps(ev))
    return _json_evidence_visibility(tmp_path,[p])

def test_historical_fields_unknown(tmp_path):
    r=show(tmp_path,{})['sources'][0]
    assert r['json_mode_requested']==r['json_mode_effective']==r['json_bounded_truncated']=='UNKNOWN'
    assert r['record_extras']['completeness']==r['tigrfam']['completeness']=='UNKNOWN'

def test_downgrade_advisory(tmp_path):
    r=show(tmp_path,{'json_mode_requested':'bounded','json_mode':'off'})
    assert 'JSON_MODE_DOWNGRADE' in r['findings']
    assert r['policy']=='ADVISORY_ONLY_NO_OVERALL_STATUS_CHANGE'

def test_leaf_cap_not_extras_completeness(tmp_path):
    r=show(tmp_path,{'json_mode_requested':'bounded','json_mode':'bounded','json_bounded_truncated':True,'record_extras_requested':True,'tigrfam_requested':True})['sources'][0]
    assert r['main_walker']['completeness']=='TRUNCATED'
    assert r['record_extras']['completeness']==r['tigrfam']['completeness']=='UNKNOWN'

def test_explicit_false_preserved_not_completion(tmp_path):
    r=show(tmp_path,{'json_mode':'bounded','json_bounded_truncated':False})['sources'][0]
    assert r['json_bounded_truncated'] is False
    assert r['main_walker']['completeness']=='UNKNOWN'

def test_bad_flag_not_coerced(tmp_path):
    assert show(tmp_path,{'json_bounded_truncated':'false'})['sources'][0]['json_bounded_truncated']=='UNKNOWN'

def test_multiple_receipts_not_first_selected(tmp_path):
    paths=[]
    for n in ('A','B'):
        p=tmp_path/(n+'_AntiSMASH_Evidence_Parse.json');p.write_text('{}');paths.append(p)
    r=_json_evidence_visibility(tmp_path,paths)
    assert 'EVIDENCE_RECEIPT_AMBIGUOUS' in r['findings'] and len(r['sources'])==2

def test_malformed(tmp_path):
    p=tmp_path/'A_AntiSMASH_Evidence_Parse.json';p.write_text('{')
    assert _json_evidence_visibility(tmp_path,[p])['sources'][0]['read_state']=='PARSE_FAILED'

def test_effective_mode_conflict(tmp_path):
    assert 'JSON_EFFECTIVE_MODE_CONFLICT' in show(tmp_path,{'json_mode':'off','json_mode_effective':'bounded'})['findings']

def test_parse_held(tmp_path):
    assert show(tmp_path,{'json_mode':'full','json_skipped':['too large']})['sources'][0]['main_walker']['completeness']=='PARSE_HELD'

def test_real_parser_off_override(tmp_path):
    p=tmp_path/'tiny.zip'
    with zipfile.ZipFile(p,'w') as z:z.writestr('tiny.json',json.dumps({'records':[]}))
    ev=ae.parse_antismash_evidence(p,json_mode='off',include_structured=True,want_tigrfam=True)
    r=show(tmp_path,ev)['sources'][0]
    assert r['main_walker']['completeness']=='NOT_RUN'
    assert r['record_extras']['requested'] is True and r['tigrfam']['requested'] is True
    assert r['record_extras']['completeness']=='UNKNOWN'

def test_timeout_preserves_original_request(monkeypatch,tmp_path):
    def timeout(*a,**kw):raise cli._BoundedTimeout()
    monkeypatch.setattr(cli,'_with_timeout',timeout)
    monkeypatch.setattr(cli,'parse_antismash_evidence_status',lambda *a,**kw:{'json_mode':kw['json_mode'],'json_mode_requested':kw['json_mode']})
    ev,mode=cli._parse_evidence_with_budget('unused','bounded',3,lambda x:None)
    assert mode=='off' and ev['json_mode_requested']=='bounded'
    assert ev['json_parse_budget']['state']=='EXCEEDED_FALLBACK_OFF'
    gate=show(tmp_path,ev)
    assert 'JSON_MODE_DOWNGRADE' in gate['findings']
    assert 'Final returned parser receipt' in gate['sources'][0]['attempt_scope']

def test_budget_unavailable(monkeypatch):
    monkeypatch.delattr(cli._signal,'SIGALRM')
    monkeypatch.setattr(cli,'parse_antismash_evidence_status',lambda *a,**kw:{'json_mode':'bounded'})
    ev,_=cli._parse_evidence_with_budget('unused','bounded',3,lambda x:None)
    assert ev['json_parse_budget']['state']=='RETURNED_GUARD_UNAVAILABLE'

def test_budget_disabled(monkeypatch):
    monkeypatch.setattr(cli,'parse_antismash_evidence_status',lambda *a,**kw:{'json_mode':'bounded'})
    ev,_=cli._parse_evidence_with_budget('unused','bounded',0,lambda x:None)
    assert ev['json_parse_budget']['state']=='DISABLED'

def test_existing_validator_status_unchanged(tmp_path):
    before=validate_package(tmp_path,write_status_receipt=False)
    show(tmp_path,{'json_mode_requested':'bounded','json_mode':'off'})
    after=validate_package(tmp_path,write_status_receipt=False)
    assert before['status']==after['status']=='FAIL'
    assert 'JSON_MODE_DOWNGRADE' in after['json_evidence_visibility']['findings']

def test_real_leaf_cap_retains_independent_extras(tmp_path,monkeypatch):
    monkeypatch.setattr(ae,'BOUNDED_MAX_RECORDS_STREAMING',1)
    monkeypatch.setattr(ae,'BOUNDED_MAX_RECORDS',1)
    p=tmp_path/'tiny-cap.zip'
    rec={'id':'contig_test','modules':{'clusterblast':{'one':'first','two':'second'},'antismash.modules.nrps_pks':{'consensus':{'gene_test':'ala'}}}}
    with zipfile.ZipFile(p,'w') as z:z.writestr('tiny.json',json.dumps({'records':[rec]}))
    ev=ae.parse_antismash_evidence(p,json_mode='bounded')
    assert ev['json_bounded_truncated'] is True
    assert ev['nrps_pks_consensus'][0]['consensus_substrate']=='ala'
    gate=show(tmp_path,ev)['sources'][0]
    assert gate['main_walker']['completeness']=='TRUNCATED'
    assert gate['record_extras']['completeness']=='UNKNOWN'

def test_missing_receipt_visible(tmp_path):
    assert _json_evidence_visibility(tmp_path,[])['findings']==['EVIDENCE_RECEIPT_MISSING']
