"""Generic geometry and provenance negatives; no fabricated scientific results."""
import copy
import json
from pathlib import Path
import pytest
from mamey.cohort_enzyme_neighborhoods import identity, project, pinned, pages, sha, write_json


def fixture():
    l=dict(strain='TEST-1',full_node='contig_complete_001',region='region001',bgc_alias='cluster001',
           exact_identity='TEST-1 / contig_complete_001 / region001 / cluster001',start=100,end=500)
    genes=[dict(locus_tag='g'+str(i),start=100+i*100,end=150+i*100,strand=1,protein_sha256=str(i)*64,
                owner_term_groups=['CDPS'] if i==1 else [],product=None) for i in range(3)]
    census=[dict(g,cds_start=g['start'],cds_end=g['end'],hold=None) for g in genes]
    arch=[dict(g,membership='EXACT_REGION',product='source annotation') for g in genes]
    return l,genes,[],[],arch,[],census


def test_order_gap_recurrence_and_unknown():
    args=fixture();args[1].reverse();r=project(*args)
    assert [g['locus_tag'] for g in r['genes']]==['g0','g1','g2']
    assert r['genes'][1]['gap_previous_bp']==49
    assert len(r['signatures'])==1
    assert r['denominators']['exact_region_cds']==3
    assert r['genes'][0]['domain_state']=='TESTED_NO_LINKED_FEATURE'


@pytest.mark.parametrize('field', ['strain','full_node','region','bgc_alias'])
def test_missing_identity(field):
    l=fixture()[0];l[field]=''
    with pytest.raises(ValueError,match='IDENTITY'):identity(l)


def test_conflicting_full_identity():
    l=fixture()[0];l['full_node']='other_contig'
    with pytest.raises(ValueError,match='CONFLICT'):identity(l)


@pytest.mark.parametrize('field,value',[('protein_sha256','f'*64),('start',101),('strand',-1)])
def test_wrong_protein_or_geometry(field,value):
    args=fixture();args[4][0][field]=value
    with pytest.raises(ValueError,match='ROSTER_CONFLICT'):project(*args)


def test_duplicate_records_rejected():
    args=fixture();args[1].append(copy.deepcopy(args[1][0]))
    with pytest.raises(ValueError,match='DUPLICATE'):project(*args)


def test_wrong_assembly_context_rejected():
    args=fixture();args[2].append(dict(args[1][0],contig='other_assembly',membership='BOUNDARY_CONTEXT_10KB'))
    with pytest.raises(ValueError,match='CONTIG_CONFLICT'):project(*args)


def test_sparse_flank_never_enters_recurrence():
    args=fixture();args[2].append(dict(locus_tag='flank',start=50,end=99,strand=-1,protein_sha256='f'*64,contig=args[0]['full_node'],membership='BOUNDARY_CONTEXT_10KB',owner_term_groups=['CDPS'],product=None))
    r=project(*args)
    assert r['denominators']['sparse_flank_cds']==1 and len(r['signatures'])==1
    assert r['genes'][0]['distance_to_region_bp']==-1
    assert r['genes'][0]['domain_state']=='NOT_AVAILABLE_IN_SPARSE_FLANK_VIEW'


def test_domain_name_alone_does_not_bind():
    args=fixture();args[5].append(dict(feature_order=1,start=110,end=120,contig=args[0]['full_node'],locus_tag='g0',binding_json=json.dumps({'parents':[],'holds':[]})))
    r=project(*args);assert len(r['unbound_features'])==1
    assert not r['genes'][0]['domains']


def test_domain_correct_parent_binds_wrong_hash_does_not():
    args=fixture();parent=dict(locus_tag='g0',cds_start=100,cds_end=150,strand=1,protein_sha256='0'*64)
    args[5].append(dict(feature_order=1,start=110,end=120,contig=args[0]['full_node'],binding_json=json.dumps({'parents':[parent],'holds':[]})))
    assert len(project(*args)['genes'][0]['domains'])==1
    parent['protein_sha256']='a'*64;args[5][0]['binding_json']=json.dumps({'parents':[parent],'holds':[]})
    assert len(project(*args)['unbound_features'])==1


def test_tamper_changed_dependency_and_live_sidecar(tmp_path):
    p=tmp_path/'source';p.write_text('original');entry=dict(path=str(p),sha256=sha(p));assert pinned(entry)==p
    p.write_text('changed')
    with pytest.raises(ValueError,match='SOURCE_PIN'):pinned(entry)
    entry['sha256']=sha(p);p.with_name('source-wal').touch()
    with pytest.raises(ValueError,match='LIVE_SOURCE'):pinned(entry)


def test_negative_gap_overlap_and_unknown_orientation():
    args=fixture();args[1][1]['start']=140;args[4][1]['start']=140;args[6][1]['start']=140
    for table in (args[1],args[4],args[6]):table[1]['strand']=None
    r=project(*args);assert r['genes'][1]['gap_previous_bp']==-11
    assert 'ORIENTATION_UNKNOWN' in r['genes'][1]['holds']


def test_pagination_no_failure_to_zero():
    with pytest.raises(ValueError,match='COUNT'):pages(lambda off:dict(rows=[],next_offset=None,total=1))
    with pytest.raises(ValueError,match='PROGRESS'):pages(lambda off:dict(rows=[],next_offset=0,total=1))


def test_output_escape(tmp_path):
    allowed=tmp_path/'allowed';allowed.mkdir()
    with pytest.raises(ValueError,match='OUTPUT_ROOT'):write_json(tmp_path/'outside.json',{},allowed)


def test_mixed_population_fails_before_reader_or_outputs(tmp_path):
    from mamey.cohort_enzyme_neighborhoods import build
    sources={}
    manifests={'dkp_manifest':{'binding':{'census_database_sha256':'a'}},
               'architecture_manifest':{'binding':{'census_sha256':'b'}},
               'census_manifest':{'database_sha256':'a'},'domain_manifest':{}}
    for k,v in manifests.items():
        p=tmp_path/k;p.write_text(json.dumps(v));sources[k]={'path':str(p),'sha256':sha(p)}
    contract=tmp_path/'current50.md';contract.write_text('\n'.join('| '+str(i)+' | Fixture requirement '+str(i)+' |' for i in range(1,51)))
    sources['current50_contract']={'path':str(contract),'sha256':sha(contract)}
    config=tmp_path/'config.json';config.write_text(json.dumps({'sources':sources,'allowed_output_root':str(tmp_path)}))
    with pytest.raises(ValueError,match='POPULATION_JOIN_HOLD'):build(config,tmp_path/'output')
    assert not (tmp_path/'output').exists()


def test_malformed_contract_fails_before_reader(tmp_path):
    from mamey.cohort_enzyme_neighborhoods import build
    sources={}
    for k in ('dkp_manifest','architecture_manifest','census_manifest','domain_manifest'):
        p=tmp_path/k;p.write_text('{}');sources[k]={'path':str(p),'sha256':sha(p)}
    p=tmp_path/'current50';p.write_text('| 1 | Incomplete fixture |');sources['current50_contract']={'path':str(p),'sha256':sha(p)}
    cfg=tmp_path/'config';cfg.write_text(json.dumps({'sources':sources,'allowed_output_root':str(tmp_path)}))
    with pytest.raises(ValueError,match='CONTRACT_SHAPE'):build(cfg,tmp_path/'output')


def test_cli_missing_and_parse_failed_are_distinct(tmp_path):
    import subprocess,sys
    tool=Path(__file__).resolve().parents[1]/'tools/build_enzyme_neighborhoods.py'
    out=tmp_path/'output'
    r=subprocess.run([sys.executable,str(tool),'--config',str(tmp_path/'absent'),'--out',str(out)],capture_output=True,text=True)
    assert r.returncode==2 and json.loads(r.stderr)['status']=='MISSING_SOURCE'
    p=tmp_path/'bad.json';p.write_text('{broken')
    r=subprocess.run([sys.executable,str(tool),'--config',str(p),'--out',str(out)],capture_output=True,text=True)
    assert r.returncode==2 and json.loads(r.stderr)['status']=='PARSE_FAILED'
