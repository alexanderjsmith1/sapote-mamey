"""Cross-member source conflicts; tiny invented metadata, no biological payload."""
import importlib
import json
import zipfile
from itertools import permutations

import pytest

from mamey import antismash_evidence as ae
from mamey.json_evidence_state import project
from mamey.models import BGCRecord

CONTIG='SYNTHETIC_REFERENCE_CONTIG.1'


@pytest.fixture(autouse=True,params=['selected','python'])
def backend(request,monkeypatch):
    assert ae._HAVE_IJSON
    if request.param=='python':
        monkeypatch.setattr(ae,'ijson',importlib.import_module('ijson.backends.python'))


def record(score,*,contig=CONTIG,region='1'):
    return {'id':contig,'modules':{'cluster_compare':{'by_region':{region:{
        'RegionToRegion_RiQ':{'scores_by_region':{'SYNTHETIC_REFERENCE':score}}}}}}}


def parse(tmp_path,documents):
    path=tmp_path/'synthetic.zip'
    with zipfile.ZipFile(path,'w') as z:
        for name,document in documents:
            z.writestr(name,document if isinstance(document,str) else json.dumps(document))
    return ae.parse_antismash_evidence(path,json_mode='bounded')


def scores(ev):
    return {key:[r['riq_score'] for r in rows if r.get('riq_score') is not None]
            for key,rows in ev['by_region'].items()}


def channel(ev):
    return next(x for x in project(ev)['channels'] if x['channel']=='RiQ')


def bgc(contig=CONTIG,region=1):
    return BGCRecord('BGC001',contig,region,0,100,100)


@pytest.mark.parametrize('values',[(.2,.8),(.8,.2),(0,1)])
def test_distinct_member_maxima_hold_instead_of_first_last_max(tmp_path,values):
    ev=parse(tmp_path,[(f'producer{i}.json',{'records':[record(v)]}) for i,v in enumerate(values)])
    assert scores(ev)=={CONTIG+'_c1':[]}
    assert ev['riq_mapped_count']==0 and ev['riq_mapping_status']=='SOURCE_CONFLICT_HELD'
    assert 'riq_genome_summary' not in ev
    assert ev['riq_member_reconciliation']['conflicting_regions']==1
    assert {x['riq_score'] for x in ev['riq_source_conflicts'][0]['observations']}==set(values)
    assert channel(ev)['state']=='SOURCE_CONFLICT_HELD' and channel(ev)['count']==0
    b=bgc();b.riq_score=.99;b.riq_label='stale synthetic value'
    ae.apply_evidence_to_bgcs([b],ev)
    assert b.riq_score is None and b.riq_label=='SOURCE_CONFLICT_HELD'
    assert ev['riq_mapping_status']=='SOURCE_CONFLICT_HELD'


@pytest.mark.parametrize('value',[0,.4,1])
def test_equal_values_deduplicate_and_preserve_each_member(tmp_path,value):
    ev=parse(tmp_path,[('z.json',{'records':[record(value)]}),('a.json',{'records':[record(value)]})])
    row=ev['by_region'][CONTIG+'_c1'][0]
    assert row['riq_score']==value and row['riq_sources']==['a.json','z.json']
    assert row['riq_source_observations']==[{'source':'a.json','riq_score':value},{'source':'z.json','riq_score':value}]
    assert ev['riq_mapped_count']==1 and ev['riq_genome_summary']=={'regions_with_riq':1,'median':value,'max':value}
    assert ev['riq_member_reconciliation']['equal_repeat_observations']==1
    assert sum(w['riq_mapped_maxima'] for w in ev['json_bounded_walks'])==2
    assert channel(ev)['count']==1 and channel(ev)['state']=='READ_COMPLETE_FOR_SELECTED_SCORES'
    b=bgc();ae.apply_evidence_to_bgcs([b],ev);assert b.riq_score==value


def test_disjoint_member_regions_have_one_consistent_archive_summary(tmp_path):
    ev=parse(tmp_path,[('first.json',{'records':[record(.2)]}),
        ('second.json',{'records':[record(.8,region='2')]}),('empty.json',{'records':[]})])
    assert ev['riq_mapped_count']==2 and ev['riq_unmapped_count']==0
    assert ev['riq_genome_summary']=={'regions_with_riq':2,'median':.5,'max':.8}
    assert channel(ev)['count']==2


def test_conflict_holds_genome_summary_but_preserves_independent_region(tmp_path):
    ev=parse(tmp_path,[('one.json',{'records':[record(.2),record(.4,region='2')]}),
        ('two.json',{'records':[record(.8)]})])
    assert scores(ev)=={CONTIG+'_c1':[],CONTIG+'_c2':[.4]}
    assert ev['riq_mapped_count']==1 and 'riq_genome_summary' not in ev
    assert channel(ev)['state']=='SOURCE_CONFLICT_HELD' and channel(ev)['count']==1
    held,kept=bgc(),bgc(region=2);ae.apply_evidence_to_bgcs([held,kept],ev)
    assert held.riq_score is None and kept.riq_score==.4


def test_archive_member_order_cannot_change_selected_values_or_conflicts(tmp_path):
    docs=[('a.json',{'records':[record(.2),record(.4,region='2')]}),
          ('b.json',{'records':[record(.8)]}),('c.json',{'records':[record(.4,region='2')]})]
    results=[]
    for i,order in enumerate(permutations(docs)):
        root=tmp_path/str(i);root.mkdir();ev=parse(root,order)
        results.append((ev['by_region'],ev['riq_member_reconciliation'],ev['riq_source_conflicts'],
            ev['riq_mapped_count'],ev.get('riq_genome_summary')))
    assert all(result==results[0] for result in results)


def test_record_versions_and_region_numbers_are_exact_not_aliases(tmp_path):
    ev=parse(tmp_path,[('one.json',{'records':[record(.2)]}),
        ('two.json',{'records':[record(.8,contig='SYNTHETIC_REFERENCE_CONTIG.2')]}),
        ('three.json',{'records':[record(.5,region='2')]})])
    assert len(scores(ev))==3 and ev['riq_source_conflicts']==[]
    assert ev['riq_genome_summary']=={'regions_with_riq':3,'median':.5,'max':.8}


def test_unmapped_observations_sum_across_members_and_hold_survives_apply(tmp_path):
    bad=record(.9);bad.pop('id')
    ev=parse(tmp_path,[('one.json',{'records':[record(.2),bad]}),
        ('two.json',{'records':[record(.8),bad]})])
    assert ev['riq_unmapped_count']==2
    ae.apply_evidence_to_bgcs([bgc()],ev)
    assert ev['riq_unmapped_count']==2 and ev['riq_mapping_status']=='SOURCE_CONFLICT_HELD'
    assert channel(ev)['state']=='SOURCE_CONFLICT_HELD'


def test_txt_kcb_values_survive_riq_conflict(tmp_path):
    ev=parse(tmp_path,[('one.json',{'records':[record(.2)]}),('two.json',{'records':[record(.8)]})])
    other={'source':'synthetic_knownclusterblast.txt','source_kind':'knownclusterblast','cumulative_score':7}
    ev['by_region'][CONTIG+'_c1'].insert(0,other.copy())
    ae._reconcile_riq_members(ev)
    assert other in ev['by_region'][CONTIG+'_c1']
    b=bgc();ae.apply_evidence_to_bgcs([b],ev)
    assert b.riq_score is None and b.kcb_cumulative==7


def test_per_member_maximum_semantics_are_preserved_not_population_proof(tmp_path):
    a=record(.8);a['modules']['cluster_compare']['by_region']['1']['RegionToRegion_RiQ']['scores_by_region']['another']=.2
    b=record(.8);b['modules']['cluster_compare']['by_region']['1']['RegionToRegion_RiQ']['scores_by_region']['different']=.3
    ev=parse(tmp_path,[('one.json',{'records':[a]}),('two.json',{'records':[b]})])
    assert scores(ev)=={CONTIG+'_c1':[.8]}
    assert 'equal maxima do not prove equal reference populations' in ev['riq_member_reconciliation']['scope']


def test_partial_member_stays_parse_held_and_counts_not_last_member_only(tmp_path):
    broken='{"records":['+json.dumps(record(.9))[:-1]
    ev=parse(tmp_path,[('good.json',{'records':[record(.2)]}),('broken.json',broken)])
    assert ev['riq_mapped_count']==1 and ev['riq_unmapped_count']==1
    assert ev['json_errors'] and channel(ev)['state']=='PARSE_HELD'


def test_conflict_does_not_hide_malformed_walk_receipt(tmp_path):
    ev=parse(tmp_path,[('one.json',{'records':[record(.2)]}),('two.json',{'records':[record(.8)]})])
    ev['json_bounded_walks'][0]['riq_observations_seen']=99
    assert channel(ev)['state']=='RECEIPT_CONFLICT'


def test_invalid_archive_reconciliation_is_receipt_conflict(tmp_path):
    ev=parse(tmp_path,[('one.json',{'records':[record(.2)]})])
    ev['riq_member_reconciliation']['mapped_regions']=9
    assert channel(ev)['state']=='RECEIPT_CONFLICT'



def test_actual_visibility_gate_reports_source_conflict_receipt(tmp_path):
    from mamey.validate import _json_evidence_visibility
    ev=parse(tmp_path,[('one.json',{'records':[record(.2)]}),
                       ('two.json',{'records':[record(.8)]})])
    saved=tmp_path/'SYNTHETIC_REFERENCE_AntiSMASH_Evidence_Parse.json'
    saved.write_text(json.dumps(ev))
    result=_json_evidence_visibility(tmp_path,[saved])
    assert result['policy']=='ADVISORY_ONLY_NO_OVERALL_STATUS_CHANGE'
    assert result['status']=='ADVISORY_FINDINGS'
    assert 'JSON_CHANNEL_SOURCE_CONFLICT_HELD' in result['findings']
    assert result['sources'][0]['riq']['state']=='SOURCE_CONFLICT_HELD'
    assert result['sources'][0]['riq']['count']==0
    assert result['sources'][0]['channel_visibility']['riq_source_conflicts']==ev['riq_source_conflicts']


def test_actual_visibility_gate_equal_repeat_is_not_source_conflict(tmp_path):
    from mamey.validate import _json_evidence_visibility
    ev=parse(tmp_path,[('one.json',{'records':[record(.2)]}),
                       ('two.json',{'records':[record(.2)]})])
    saved=tmp_path/'SYNTHETIC_REFERENCE_AntiSMASH_Evidence_Parse.json'
    saved.write_text(json.dumps(ev))
    result=_json_evidence_visibility(tmp_path,[saved])
    assert 'JSON_CHANNEL_SOURCE_CONFLICT_HELD' not in result['findings']
    assert result['sources'][0]['riq']['state']=='READ_COMPLETE_FOR_SELECTED_SCORES'
    assert result['sources'][0]['riq']['count']==1
