"""Synthetic renderer and source-contract tests; no sequence search or thesis render."""
import importlib.util
import json
import sys
from pathlib import Path
import pytest
ROOT = Path(__file__).parent
RUNTIME = Path(__import__('os').environ.get('Y02_RUNTIME', str(Path(__file__).resolve().parents[1])))
sys.path.insert(0, str(RUNTIME/'tools'))
sys.path.insert(0, str(RUNTIME))
spec = importlib.util.spec_from_file_location('y02mrc', RUNTIME/'tools/multi_reference_comparison.py')
mrc = importlib.util.module_from_spec(spec); spec.loader.exec_module(mrc)
old = importlib.util.spec_from_file_location('oldmodel', RUNTIME/'tests/test_466_multi_reference_aligned_layout.py')
modelmod = importlib.util.module_from_spec(old);old.loader.exec_module(modelmod)


def tables(path, accession='AS-1', contig='cA', coordinate_system='region'):
    path.mkdir(exist_ok=True)
    g=path/f'{accession}.genes.tsv'
    g.write_text('sequence_id\tprotein_id\tstart\tend\taverage_p\n'+
                 f'{contig}\tx1\t1\t1000\t0.3\n{contig}\tx2\t1001\t2000\t0.9\n')
    c=path/f'{accession}.clusters.tsv'
    c.write_text('sequence_id\tcluster_id\tstart\tend\taverage_p\ttype\n'+f'{contig}\tc1\t1\t2000\t0.8\tNRP\n')
    return g,c


def test_shared_strip_mapping_and_missing_state(tmp_path):
    model=modelmod._model(); tables(tmp_path)
    result=mrc.attach_gecco(model,tmp_path)
    assert result['query']['p']=={'a1':.3,'a2':.9}
    assert result['Top_region001']['state']=='NOT_RUN'
    assert result['Top_region001']['note']=='GECCO not run'
    assert len(model['gecco_bindings'])==2


def test_pyrodigal_explicit_overlap(tmp_path):
    model=modelmod._model(); tables(tmp_path,contig='pyrodigal_record')
    mapping=tmp_path/'overlap.tsv'
    mapping.write_text('accession\tcds_id\tgecco_protein_id\toverlap_fraction\nAS-1\ta1\tx2\t0.8\nAS-1\ta2\tx1\t0.4\n')
    result=mrc.attach_gecco(model,tmp_path,mapping)['query']
    assert result['p']=={'a1':.9}
    assert result['binding']['mapping_mode']=='explicit_CDS_overlap'
    assert result['clusters'][0]['genes']==['a1']


def test_nonfinite_probability_refused_before_output(tmp_path):
    model=modelmod._model();g,c=tables(tmp_path)
    g.write_text(g.read_text().replace('0.3','nan'))
    with pytest.raises(ValueError,match='probability'):mrc.attach_gecco(model,tmp_path)


def test_gecco_render_shared_key_and_note(tmp_path):
    model=modelmod._model();tables(tmp_path)
    mrc.attach_gecco(model,tmp_path)
    out=tmp_path/'figure'
    mrc.draw_aligned(model,mrc.aligned_layout(model),out,width_in=9.6)
    assert sum(row['boxes'] for row in model['gecco_drawn'])==2
    svg=(out/'comparison.svg').read_text()
    assert svg.count('GECCO probability 0–1')==1
    assert 'GECCO not run' in svg
    assert model['text_overlaps']==[]


def test_landscape_preserves_scale(tmp_path):
    model=modelmod._model();lay=mrc.aligned_layout(model)
    lo,hi=mrc.aligned_span_bp(lay)
    scale=(hi-lo)*1.02/1000/5
    mrc.draw_with_fallback(model,lay,tmp_path/'landscape',width_in=6.5,landscape_width_in=9.6,kb_per_in=scale)
    assert model['landscape_fallback'] is True
    assert model['aligned_layout']['width_in']==9.6
    assert model['kb_per_in']==scale


def test_fallback_never_retries_unrelated_failure(monkeypatch,tmp_path):
    calls=[]
    def fail(*args,**kwargs):calls.append(kwargs);raise ValueError('bad input')
    monkeypatch.setattr(mrc,'draw_aligned',fail)
    with pytest.raises(ValueError,match='bad input'):mrc.draw_with_fallback({}, {}, tmp_path)
    assert len(calls)==1


def test_j3_spec_real_source_dry_run(tmp_path):
    root=__import__('os').environ.get('Y02_SOURCE_ROOT')
    if not root:pytest.skip('external J3 source root not selected')
    source=Path(root)/'AS Strain Master New/04 Gene clusters/Closest public regions/Lomofungin-like loci Nocardia neighbours 2026-10-22/SPEC.tsv'
    plans=mrc.spec_plans(source)
    assert len(plans)==2 and all(len(p['references'])==9 for p in plans)
    mrc.main(['--spec',str(source),'--dry-run','--out',str(tmp_path/'plan')])
    assert (tmp_path/'plan/SPEC_PLAN.json').exists()
    assert not list(tmp_path.rglob('*.png'))


def test_reference_original_coordinate_offset(tmp_path):
    from Bio.Seq import Seq
    from Bio.SeqRecord import SeqRecord
    from Bio import SeqIO
    model=modelmod._model();tables(tmp_path)
    g,c=tables(tmp_path,'REF','record1')
    g.write_text(g.read_text().replace('\t1\t1000','\t10001\t11000').replace('\t1001\t2000','\t11001\t12000'))
    record=SeqRecord(Seq('A'*2000),id='record1',annotations={'molecule_type':'DNA',
                      'structured_comment':{'antiSMASH-Data':{'Orig. start':'10000'}}})
    gbk=tmp_path/'ref.gbk';SeqIO.write(record,gbk,'genbank')
    ref=model['refs'][0];ref['gbk']=str(gbk);ref['gecco_accession']='REF'
    (tmp_path/'INDEX.tsv').write_text('accession\tgenes\tclusters\tcoordinate_system\nAS-1\tAS-1.genes.tsv\tAS-1.clusters.tsv\tgenome\nREF\tREF.genes.tsv\t\tgenome\n')
    # second reference lacks tables and remains NOT_RUN.
    result=mrc.attach_gecco(model,tmp_path)
    assert result['Top_region001']['p']=={1:.3,2:.9}


def test_duplicate_overlap_and_unscored_distinguished(tmp_path):
    model=modelmod._model();g,c=tables(tmp_path,contig='unrelated')
    result=mrc.attach_gecco(model,tmp_path)
    assert result['query']['state']=='AVAILABLE' and result['query']['p']=={}
    mapping=tmp_path/'bad.tsv'
    mapping.write_text('accession\tcds_id\tgecco_protein_id\toverlap_fraction\nAS-1\ta1\tx1\t.9\nAS-1\ta1\tx2\t.9\n')
    with pytest.raises(ValueError,match='duplicate CDS'):mrc.attach_gecco(model,tmp_path,mapping)


@pytest.mark.parametrize("query_index", [0, 1])
def test_matched_real_source_gecco_tables_without_render(tmp_path,query_index):
    from Bio import SeqIO
    root=__import__('os').environ.get('Y02_SOURCE_ROOT')
    if not root:pytest.skip('external matched GECCO source root not selected')
    source=Path(root)
    j3=source/'AS Strain Master New/04 Gene clusters/Closest public regions/Lomofungin-like loci Nocardia neighbours 2026-10-22'
    plan=mrc.spec_plans(j3/'SPEC.tsv')[query_index]
    query=plan['query']; record=SeqIO.read(query['path'],'genbank')
    offset=int(record.annotations['structured_comment']['antiSMASH-Data']['Orig. start'])
    strain,contig,region,alias=query['identity'].split(' / ')
    genes,_=mrc.gdr.load_reference(query['path'])
    prots={g['id']:dict(g,tag=g['id'],contig=contig,start=g['start']+offset,end=g['end']+offset) for g in genes}
    reference=next(row for row in plan['references'] if row['role']=='mibig')
    rg,_=mrc.gdr.load_reference(reference['path'])
    model={'label':strain,'prots':prots,'refs':[{'accession':reference['accession'],'gbk':reference['path'],'genes':rg}], 'sources':[]}
    qdir=source/'AS Strain Master/_GECCO_COHORT_2026-10-02'/strain
    rdir=source/'October 21 2026 Claude/GECCO_MIBIG_2088_2026-10-21/gecco'/reference['accession']
    (tmp_path/'INDEX.tsv').write_text('accession\tgenes\tclusters\tcoordinate_system\n'+
        f'{strain}\t{qdir/(strain+".genes.tsv")}\t{qdir/(strain+".clusters.tsv")}\tgenome\n'+
        f'{reference["accession"]}\t{rdir/(reference["accession"]+".genes.tsv")}\t{rdir/(reference["accession"]+".clusters.tsv")}\tregion\n')
    tracks=mrc.attach_gecco(model,tmp_path)
    assert len(tracks['query']['p'])>0 and len(tracks[reference['accession']]['p'])>0
    assert all(0<=p<=1 for data in tracks.values() for p in data['p'].values())
    (tmp_path/'MATCHED_REAL_SOURCE.json').write_text(json.dumps({'identity':query['identity'],
        'query_CDS':len(genes),'query_scored':len(tracks['query']['p']),
        'reference_CDS':len(rg),'reference_scored':len(tracks[reference['accession']]['p']),
        'bindings':model['gecco_bindings'],'depth':'saved-table coordinate binding only; no search/render'},indent=1))


def test_spec_keeps_unplaced_declared_rows(tmp_path,monkeypatch):
    model=modelmod._model()
    model['refs']=model['refs'][:1]
    plan={'references':[{'path':str(tmp_path/'Top_region001.gbk'),'accession':'Top_region001','label':'Genus alpha'},
                        {'path':str(tmp_path/'unplaced.gbk'),'accession':'ref2','label':'Genus beta'}]}
    monkeypatch.setattr(mrc.gdr,'load_reference',lambda path:(modelmod._model()['refs'][1]['genes'],'synthetic'))
    mrc.complete_spec_rows(model,plan)
    assert len(model['refs'])==2
    assert model['refs'][1]['pairs']==[]
    assert model['refs'][1]['not_placed_reason']=='below discovery admission threshold'
    assert mrc.aligned_layout(model)['rows'][0]['place']=={}
