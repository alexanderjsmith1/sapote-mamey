"""Synthetic producer-schema tests; no source packet admission, search or render."""
import csv,copy,json,os,sys
from pathlib import Path
import pytest
root=Path(os.environ.get('Y02_RUNTIME',str(Path(__file__).resolve().parents[1])))
sys.path.insert(0,str(root/'tests'))
from test_y02_multi_reference_gecco import mrc

def spec_fixture(tmp_path):
    regions=tmp_path/'regions';regions.mkdir()
    for name in ['q0.gbk','q1.gbk','shared.gbk']:(regions/name).write_text(name)
    fields=['locus','region_file','label','accession','role','identity','sha256','genes_present']
    rows=[]
    for i in range(2):
        identity=f'SYN-{i} / synthetic_contig / region001 / BGC001'
        for filename,role in [(f'q{i}.gbk','query'),('shared.gbk','public')]:
            rows.append(dict(locus=identity,region_file=filename,label='synthetic',accession='SYNREF',role=role,
                             identity=identity if role=='query' else 'reference',sha256=mrc.rlc.sha_file(regions/filename),genes_present='2'))
    path=tmp_path/'SPEC.tsv'
    with path.open('w') as h:
        w=csv.DictWriter(h,fieldnames=fields,delimiter='\t');w.writeheader();w.writerows(rows)
    return path

def test_grouped_spec_shared_reference_stays_scoped(tmp_path):
    plans=mrc.spec_plans(spec_fixture(tmp_path))
    assert len(plans)==2 and all(len(p['references'])==1 for p in plans)
    assert plans[0]['locus']!=plans[1]['locus']
    assert all(p['producer_grouped'] for p in plans)

def map_fixture():
    row=dict(genome='SYNREF',region_file='r.gbk',antismash_locus_tag='cds',gecco_protein_id='g1',
             gecco_start='1',gecco_end='100',overlap_share_of_shorter='.6',accepted_ge_50pct='yes',gecco_average_p='.8123456789')
    proteins={1:dict(tag='cds',start=0,end=1000)}
    genes=[dict(protein_id='g1',sequence_id='record',start='1',end='100',average_p='.8123456789')]
    clusters=[dict(sequence_id='record',cluster_id='c1',start='1',end='100',average_p='.8',type='NRP')]
    return row,proteins,genes,clusters

def test_producer_shorter_overlap_replayed_without_cds_rule():
    row,proteins,genes,clusters=map_fixture()
    result=mrc.producer_gecco_binding([row],'SYNREF','r.gbk',proteins,genes,clusters)
    assert result['p']=={1:.8123456789}
    assert result['binding']['overlap_denominator']=='shorter_gene'
    assert result['clusters'][0]['genes']==[1]

def test_producer_probability_disagreement_refused():
    row,proteins,genes,clusters=map_fixture();row['gecco_average_p']='.1'
    with pytest.raises(ValueError,match='probability disagrees'):
        mrc.producer_gecco_binding([row],'SYNREF','r.gbk',proteins,genes,clusters)

def test_producer_map_region_scoping_and_rejection():
    row,proteins,genes,clusters=map_fixture()
    other=dict(row,region_file='other.gbk',gecco_average_p='.2')
    result=mrc.producer_gecco_binding([row,other],'SYNREF','r.gbk',proteins,genes,clusters)
    assert result['p']=={1:.8123456789}
    row['accepted_ge_50pct']='no'
    assert mrc.producer_gecco_binding([row],'SYNREF','r.gbk',proteins,genes,clusters)['p']=={}

def test_grouped_count_spec_cannot_trigger_research(tmp_path,monkeypatch):
    spec=spec_fixture(tmp_path)
    monkeypatch.setattr(mrc,'build',lambda *a,**kw:pytest.fail('must not run search/build'))
    out=tmp_path/'out'
    with pytest.raises(ValueError,match='SAVED_PAIRS_REQUIRED'):
        mrc.main(['--spec',str(spec),'--out',str(out)])
    assert not out.exists()

def test_grouped_spec_dry_run_is_available(tmp_path):
    spec=spec_fixture(tmp_path);out=tmp_path/'out'
    mrc.main(['--spec',str(spec),'--dry-run','--out',str(out)])
    assert len(json.loads((out/'SPEC_PLAN.json').read_text()))==2


def test_producer_no_overlapping_gene_is_unscored_not_unrun():
    row,proteins,genes,clusters=map_fixture()
    row.update(accepted_ge_50pct='no GECCO gene overlaps',overlap_share_of_shorter='0',gecco_protein_id='',gecco_average_p='')
    assert mrc.producer_gecco_binding([row],'SYNREF','r.gbk',proteins,genes,clusters)['p']=={}


def test_genbank_source_replays_exact_supplied_tags():
    row,proteins,genes,clusters=map_fixture()
    genes[0]['protein_id']='cds'
    result=mrc.saved_gene_id_binding(proteins,genes,clusters)
    assert result['p']=={1:.8123456789}
    assert result['binding']['mapping_mode']=='genbank_cds_exact_locus_tag'


def test_missing_producer_region_map_is_not_unscored_evidence():
    row,proteins,genes,clusters=map_fixture()
    with pytest.raises(ValueError,match='map rows unavailable'):
        mrc.producer_gecco_binding([row],'SYNREF','absent.gbk',proteins,genes,clusters)


def test_identical_repeated_map_rows_count_once_and_are_reported():
    row,proteins,genes,clusters=map_fixture()
    result=mrc.producer_gecco_binding([row,dict(row)],'SYNREF','r.gbk',proteins,genes,clusters)
    assert result['p']=={1:.8123456789}
    assert result['binding']['identical_duplicate_rows']==1
    assert result['binding']['distinct_CDS_rows']==1


def test_conflicting_repeated_map_rows_refused():
    row,proteins,genes,clusters=map_fixture()
    other=dict(row,gecco_protein_id='different')
    with pytest.raises(ValueError,match='conflicting producer CDS'):
        mrc.producer_gecco_binding([row,other],'SYNREF','r.gbk',proteins,genes,clusters)
