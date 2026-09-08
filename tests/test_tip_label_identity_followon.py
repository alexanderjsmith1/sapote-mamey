"""Generic display-only fixtures. No inference, sequence search or real tree rewriting."""
import hashlib, importlib.util, json
from pathlib import Path
from types import SimpleNamespace
import pytest
from mamey.tip_label import accession_candidates, make_label, unique_labels

SRC=Path(__file__).resolve().parents[1]/'tools/phylo_place.py'
spec=importlib.util.spec_from_file_location('tip_label_placement',SRC)
pp=importlib.util.module_from_spec(spec);spec.loader.exec_module(pp)
SOURCE={'source_file':'records.tsv','source_sha256':'a'*64,'record_locator':'row:2'}
def fields(acc='NR_112543.123'):
 return dict(source=SOURCE,accession=acc,species='Genus example long description',host='Host example')

@pytest.mark.parametrize('text,want',[
 ('NR_112543.123',['NR_112543.123']),
 ('NR_112543.1XYZ',[]),('NR_112543.1.2',[]),('NR_112543_1XYZ',[]),
 ('ATCC_19285',[]),('IFO_14684',[]),('CC_19285',[]),
 ('Genus_species_NR_112543_123',['NR_112543.123']),
 ('GCF_000372745.1',['GCF_000372745.1']),
 ('GCF_000372745.1XYZ',[]),('XNR_112543.1',[]),
 ('PZ730308.1 Genus species',['PZ730308.1']),
])
def test_full_candidate_boundaries(text,want):
 assert accession_candidates(text)['candidates']==want

def test_ambiguity_not_first_match():
 text='NR_112543.1 and NR_118886.1';r=accession_candidates(text)
 assert r['state']=='AMBIGUOUS' and pp._accession(text)==''
 assert accession_candidates('NR_112543.1 NR_112543.1')['state']=='HEURISTIC_CANDIDATE'
 assert pp._accession('NR_112543.123')=='NR_112543.123'

@pytest.mark.parametrize('width',[1,14,20,58])
def test_protected_fields_overflow(width):
 r=make_label('QUERY-LONG-IDENTIFIER','raw',query=True,outgroup=True,fields=fields(),width=width)
 assert all(x in r['label']for x in ['QUERY-LONG-IDENTIFIER','OUTGROUP','NR_112543.123'])
 if len(r['label'])>width:assert 'WIDTH_OVERFLOW_HOLD'in r['holds']
 assert r['authority']=='SOURCE_FIELD_ONLY_NOT_SEQUENCE_IDENTITY'
 assert 'ACCESSION_TO_TIP_SEQUENCE_UNVERIFIED'in r['holds']

@pytest.mark.parametrize('width',[0,-1,True,1.5,'20',None])
def test_invalid_width(width):
 with pytest.raises(ValueError,match='WIDTH'):make_label('Q','raw',width=width)

@pytest.mark.parametrize('value',['CC_19285','NR_112543.1XYZ','NR_112543_1','NR_112543.1 and NR_118886.1'])
def test_explicit_invalid_accession(value):
 with pytest.raises(ValueError,match='ACCESSION'):make_label('Q','raw',fields=fields(value))

@pytest.mark.parametrize('raw',['Genus (example','Host ]','bad\nlabel','([)]'])
def test_bad_brackets_or_control(raw):
 with pytest.raises(ValueError):make_label('Q',raw)

def test_no_authority_no_promotion():
 r=make_label('Q','NR_112543.123 Genus species',fields={'accession':'NR_112543.123'},width=5)
 assert 'UNBOUND' in r['label'] and 'NR_112543.123 Genus species'in r['label']
 assert r['authority']=='UNBOUND' and r['candidate_inspection']['authority']=='UNBOUND'

def test_conflicting_fields_preserved():
 r=make_label('Q','NR_118886.1',fields=fields())
 assert 'LABEL_SOURCE_ACCESSION_CONFLICT'in r['holds'] and r['raw_label']=='NR_118886.1'

def test_duplicate_labels_and_keys():
 rs=[make_label(k,'same',fields=fields())for k in ['a','b']]
 result=unique_labels(rs);assert len({r['label']for r in result.values()})==2
 with pytest.raises(ValueError,match='MACHINE'):unique_labels([rs[0],rs[0]])

def test_no_gappa_suffix_guess_and_marker_owner():
 tips=[SimpleNamespace(name='SID123_2'),SimpleNamespace(name='Ref_OUTGROUP')]
 result=pp._placement_display_labels(tips,{'SID123':'different header'},set())
 assert result['SID123_2']['raw_label']=='SID123_2'
 assert 'LABELMAP_KEY_UNBOUND'in result['SID123_2']['holds']
 assert result['Ref_OUTGROUP']['outgroup'] and 'OUTGROUP'in result['Ref_OUTGROUP']['label']
 with pytest.raises(ValueError,match='TIP_KEY_UNBOUND'):pp._placement_display_labels(tips,{},set(),tip_fields={'wrong':fields()})

def test_labelmap_conflict_refused(tmp_path):
 p=tmp_path/'map.tsv';p.write_text('safe\toriginal\nx\ta\nx\tb\n')
 with pytest.raises(ValueError,match='LABELMAP_KEY_CONFLICT'):pp._load_labelmap(p)

def test_actual_render_receipt_and_gate(tmp_path,monkeypatch):
 pytest.importorskip('matplotlib');pytest.importorskip('Bio')
 # Synthetic saved topology, used only to exercise the existing render path.
 tree=tmp_path/'fixture.nwk';tree.write_text('((SID12345:0.01,Ref1:0.01):0.01,Ref2:0.02,Outer_OUTGROUP:0.03);')
 before=tree.read_bytes();svg=tmp_path/'figure.svg';png=tmp_path/'figure.png'
 labelmap={'SID12345':'SID12345','Ref1':'Genus_species_NR_112543.123','Ref2':'Genus_species_NR_118886.1','Outer_OUTGROUP':'Outer_species_NR_119181.1_OUTGROUP'}
 # Only the gate result is stubbed here; real gate behavior has existing focused tests.
 monkeypatch.setattr(pp,'_graft_sane',lambda *a:(True,'synthetic fixture'))
 pp._render_tree(str(tree),labelmap,str(png),str(svg),'fixture')
 receipt=json.loads(Path(str(svg)+'.labels.json').read_text());records={r['tip_key']:r for r in receipt['records']}
 assert set(records)==set(labelmap) and tree.read_bytes()==before
 assert 'NR_112543.123'in records['Ref1']['label']
 assert 'SID12345'in records['SID12345']['label'] and records['SID12345']['query']
 assert records['Outer_OUTGROUP']['outgroup'] and 'OUTGROUP'in records['Outer_OUTGROUP']['label']
 assert all('SOURCE_FIELDS_UNBOUND'in r['holds']for r in records.values())
 monkeypatch.setattr(pp,'_graft_sane',lambda *a:(False,'synthetic refusal'))
 with pytest.raises(RuntimeError,match='tree_sanity_check FAILED'):
  pp._render_tree(str(tree),labelmap,str(tmp_path/'blocked.png'),str(tmp_path/'blocked.svg'),'fixture')
 assert not (tmp_path/'blocked.png').exists()
