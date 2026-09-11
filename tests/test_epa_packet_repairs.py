"""Regression and negative controls for panel selection and placement display."""
import csv
import importlib.util
import io
import os
from pathlib import Path
import sqlite3
import sys
import pytest
ROOT=Path(os.environ.get('EPA_REVIEW_ROOT', Path(__file__).resolve().parents[1]))

@pytest.fixture(autouse=True)
def isolated_tool_path(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT/'tools'))

def mod(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'tools'/f'{name}.py')
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj

@pytest.mark.parametrize('scope,tags',[(None,None),('Streptomyces',None),(None,['soil']),('Streptomyces',['soil'])])
def test_metadata_filter_composes_with_genus_and_habitat(monkeypatch,scope,tags):
    m=mod('phylo_16s_panel');con=sqlite3.connect(':memory:')
    con.execute('CREATE TABLE record(acc_base,definition,seq,binomial,source,uncultured,designation,genus,isolation_source,host)')
    con.execute('CREATE TABLE record_tag(acc_base,tag)')
    for accession,genus,habitat in [('NR_123456','Streptomyces','soil'),('NR_123457','Streptomyces','unknown'),('NR_123458','Other','soil')]:
        con.execute('INSERT INTO record VALUES(?,?,?,?,?,?,?,?,?,?)',(accession,genus+' example','ACGT'*300,genus+' example','candidate',0,'REF'+accession,genus,habitat,''))
        con.execute('INSERT INTO record_tag VALUES(?,?)',(accession,'soil'))
    selected=[]
    def capture(c,sql,params=()):
        selected.extend(row[0] for row in c.execute(sql,params));return []
    monkeypatch.setattr(m,'q',capture)
    m.rank_references(con,[],['candidate'],set(),scope,tags,require_metadata=True)
    assert 'NR_123456' in selected
    assert 'NR_123457' not in selected
    assert ('NR_123458' in selected)==(scope is None)

def test_terminal_assessment_never_changes_divergent_alignment(tmp_path):
    m=mod('phylo_place');p=tmp_path/'reference.fasta'
    p.write_text('>one\n'+'A'*400+'\n>two\n'+'A'*400+'\n>divergent\n'+'C'*400+'\n')
    before=p.read_bytes()
    assess=getattr(m,'_assess_terminal_divergence',None) or m._apply_terminal_trim
    assert assess(str(p),str(tmp_path))==1
    assert p.read_bytes()==before

def test_matching_sequences_are_not_flagged():
    m=mod('phylo_place');rows={str(i):'ACGT'*100 for i in range(3)}
    assert m.trim_alignment_termini(rows)[1]=={}

@pytest.mark.parametrize('mismatch',[0,1])
def test_group_label_reports_measured_bounds(tmp_path,mismatch):
    m=mod('collapse_near_identical');seq='ACGT'*200
    aln=tmp_path/'a.fa';tree=tmp_path/'t.nwk';meta=tmp_path/'m.tsv'
    aln.write_text(f'>r1\n{seq}\n>r2\n'+('T'+seq[1:] if mismatch else seq)+f'\n>q\n{seq}\n>outgroup\n'+('TTGA'*200)+'\n')
    tree.write_text('((r1:0,r2:0):0.1,(q:0.05,outgroup:0.5):0.1);')
    meta.write_text('tip\tlabel\trole\ttaxon\nr1\tReference one\treference\tExample\nr2\tReference two\treference\tExample\nq\tQuery\tquery\tQuery\noutgroup\tOutgroup\toutgroup\tOutgroup\n')
    result=m.build_display(aln,tree,meta,dict(max_nt=1,min_cols=100,protect=[],prune_outgroup=False,group_label='representative'))
    rows=list(csv.DictReader(io.StringIO(result['metadata'].decode()),delimiter='\t'))
    label=next(r['label'] for r in rows if r['role']=='reference')
    assert f'max {mismatch} nt differences' in label and 'min 800 shared sites' in label
    assert 'identical' not in label

def test_accession_conflict_refuses_instead_of_pruning(tmp_path):
    m=mod('placement_display');builder=mod('build_placement_ggtree_inputs');p=tmp_path/'t.nwk'
    p.write_text('(SID_1:0.1,Example_NR_123456_1_NR_654321_1:0.1,outgroup:0.1);')
    with pytest.raises(ValueError,match='REFERENCE_ACCESSION_CONFLICT'):
        m.refused_reference_tips(p,builder)
    assert 'NR_123456_1_NR_654321_1' in p.read_text()

def test_unambiguous_accession_keeps_all_tips(tmp_path):
    m=mod('placement_display');p=tmp_path/'t.nwk';p.write_text('(SID_1:0.1,Example_NR_123456_1:0.1,outgroup:0.1);')
    assert m.refused_reference_tips(p,mod('build_placement_ggtree_inputs'))==[]

def test_noloc_removes_country_and_preserves_habitat():
    m=mod('placement_display');row=dict(tip='ref',kind='reference',ref_label='Example species [soil · Canada]',reference_habitat='soil',reference_country='Canada')
    withloc=m.display_rows([row],'withloc')[0];noloc=m.display_rows([row],'noloc')[0]
    assert 'Canada' in withloc['label'] and withloc['source']=='Canada'
    assert 'Canada' not in noloc['label'] and noloc['source']==''
    assert 'soil' in noloc['label'] and noloc['category']=='soil/rock/sediment'

def test_unstructured_location_is_refused_not_guessed():
    m=mod('placement_display');row=dict(tip='ref',kind='reference',ref_label='Example species Canada legacy annotation',reference_habitat='soil',reference_country='Canada')
    with pytest.raises(ValueError,match='LOCATION_LABEL_UNRESOLVED'):m.display_rows([row],'noloc')

def test_display_existing_output_is_preserved(tmp_path):
    m=mod('placement_display');out=tmp_path/'display';out.mkdir();sentinel=out/'accepted.png';sentinel.write_bytes(b'original')
    assert m.main([str(tmp_path),'--name','panel','--group','Example','--host-table','missing','--ref-source-db','missing','--out',str(out)])==2
    assert sentinel.read_bytes()==b'original'

@pytest.mark.parametrize('duplicate',['fasta','metadata'])
def test_panel_split_refuses_duplicate_identity(tmp_path,duplicate):
    m=mod('panel_split');fasta=tmp_path/'p.fa';meta=tmp_path/'m.tsv'
    fasta.write_text('>ref\nACGT\n>query\nACGT\n'+('>query\nTGCA\n' if duplicate=='fasta' else ''))
    meta.write_text('tip\trole\nref\treference\nquery\tquery\n'+('query\treference\n' if duplicate=='metadata' else ''))
    with pytest.raises(ValueError,match='DUPLICATE'):m.split_panel(fasta,meta)

def test_panel_split_uses_roles_not_names(tmp_path):
    m=mod('panel_split');fasta=tmp_path/'p.fa';meta=tmp_path/'m.tsv'
    fasta.write_text('>plain_one\nACGT\n>plain_two\nTGCA\n')
    meta.write_text('tip\trole\nplain_one\treference\nplain_two\tquery\n')
    assert m.split_panel(fasta,meta)==([('plain_one','ACGT')],[('plain_two','TGCA')])

def test_aux_export_preserves_existing_file_and_rejects_duplicate_query(tmp_path):
    import json
    m=mod('panel_receipt_to_aux');p=tmp_path/'r.json';out=tmp_path/'aux.tsv'
    row=dict(kind='query',tip='SID_1',accession='NR_123456.1')
    p.write_text(json.dumps({'records':[row,row]}))
    assert m.main([str(p),'--out',str(out)])==2 and not out.exists()
    p.write_text(json.dumps({'records':[row]}))
    assert m.main([str(p),'--out',str(out)])==0
    before=out.read_bytes()
    assert m.main([str(p),'--out',str(out)])==2 and out.read_bytes()==before


@pytest.mark.parametrize('accession', ['NR_123456.1','NR_123456.2','NR_123456'])
def test_query_reference_display_format_is_consistent(accession):
    m=mod('build_placement_ggtree_inputs')
    query=m._label_styles('SID_1','soil','Canada',accession)
    reference=m._ref_label('Example_species_'+accession, '', {m._acckey(accession):'soil'})
    assert query['noloc']=='SID_1 [soil] (NR_123456)'
    assert query['withloc']=='SID_1 [soil · Canada] (NR_123456)'
    assert reference=='Example species [soil] (NR_123456)'
    assert m._ref_accession('Example_species_'+accession)==accession


def test_outgroup_is_metadata_not_a_tip_annotation():
    m=mod('placement_display');row=dict(tip='outside',kind='reference',ref_label='Outside species [soil] (NR_123456) (outgroup)',reference_habitat='soil',reference_country='')
    rendered=m.display_rows([row],outgroup_tip='outside')[0]
    assert rendered['role']=='outgroup'
    assert rendered['label']=='Outside species [soil] (NR_123456)'
    builder=mod('build_placement_ggtree_inputs')
    assert 'outgroup' not in builder._ref_label('Outside_species_NR_123456_1_outgroup','').lower()


@pytest.mark.parametrize('style',['withloc','noloc'])
def test_query_accession_required_and_visible_in_each_variant(style):
    m=mod('placement_display');builder=mod('build_placement_ggtree_inputs')
    labels=builder._label_styles('SID_1','moss','Canada','PX000001.1')
    row=dict(tip='SID_1',kind='query',accession='PX000001.1',host='moss',region='Canada',label_withloc=labels['withloc'],label_noloc=labels['noloc'])
    assert m.display_rows([row],style)[0]['label'].endswith('(PX000001)')
    row['accession']=''
    with pytest.raises(ValueError,match='QUERY_ACCESSION_MISSING'):m.display_rows([row],style)

def test_query_label_cannot_drop_or_substitute_bound_accession():
    m=mod('placement_display')
    row=dict(tip='SID_1',kind='query',accession='PX000001.1',label_noloc='SID_1 [moss] (PX000002)')
    with pytest.raises(ValueError,match='QUERY_ACCESSION_LABEL_MISMATCH'):m.display_rows([row],'noloc')
