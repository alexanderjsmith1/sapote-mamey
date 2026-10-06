"""Geometry and evidence rejection tests for the portable renderer."""
import copy
import importlib.util
import json
from pathlib import Path
import pytest

MODULE=Path(__file__).resolve().parents[1]/'mamey/figures/locus_comparison.py'
spec=importlib.util.spec_from_file_location('comparison_under_test',MODULE)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def sample():
    """Two synthetic loci with reverse-oriented matching cores."""
    tracks=[]
    for i in (0,1):
        tracks.append(dict(id=str(i),label='Query' if i==0 else 'Reference',kind='reference',
                           identity=dict(accession=f'SYNTHETIC_{i}',description='Synthetic fixture'),orientation=1 if i==0 else -1,
                           anchor_gene='g1',genes=[dict(id=f'g{j}',label=f'gene{j}',start=(j if i==0 else 3-j)*1000,
                           end=(j if i==0 else 3-j)*1000+600,strand=1 if i==0 else -1,
                           aa_sha256=str(j)*64,group=f'G{j}') for j in (1,2)]))
    return dict(schema='locus-comparison-v1',synthetic=True,title='Synthetic locus comparison',sources=[],tracks=tracks,
                links=[dict(a=['0',f'g{j}'],b=['1',f'g{j}'],evidence='synthetic fixture',identity_pct=70) for j in (1,2)])


def test_rigid_reverse_preserves_lengths_order_and_strand():
    rows,links=m.layout(sample())
    assert all(r['display_end']-r['display_start']==r['native_end']-r['native_start'] for r in rows)
    for track in ('0','1'):
        assert [r['gene'] for r in sorted([r for r in rows if r['track']==track],key=lambda r:r['display_start'])]==['g1','g2']
    assert all(l['displayed_strands_agree'] for l in links)


def test_disagreement_is_reported_not_fixed():
    s=sample();s['tracks'][1]['orientation']=1
    rows,links=m.layout(s)
    assert not any(l['displayed_strands_agree'] for l in links)
    assert [r['gene'] for r in sorted(rows[2:],key=lambda r:r['display_start'])]==['g2','g1']


@pytest.mark.parametrize('change', ['duplicate','anchor','interval','strand','endpoint','group','nan','identity','hash','source'])
def test_refuses_invalid_evidence(change):
    s=sample();t=s['tracks'][0];g=t['genes'][0]
    if change=='duplicate':t['genes'].append(copy.deepcopy(g))
    if change=='anchor':t['anchor_gene']='absent'
    if change=='interval':g['end']=g['start']
    if change=='strand':g['strand']=0
    if change=='endpoint':s['links'][0]['a'][1]='absent'
    if change=='group':g['group']='conflicting'
    if change=='nan':s['links'][0]['identity_pct']=float('nan')
    if change=='identity':t['kind']='bgc'
    if change=='hash':g['aa_sha256']='wrong'
    if change=='source':s['synthetic']=False
    with pytest.raises(ValueError):m.validate(s)


def test_render_and_output_guard(tmp_path):
    f=tmp_path/'input.json';f.write_text(json.dumps(sample()))
    result=m.render(f,tmp_path/'out')
    assert result['displayed_strand_agreements']==2
    assert all((tmp_path/'out'/name).stat().st_size>100 for name in result['files'])
    assert '<text' in (tmp_path/'out/comparison.svg').read_text()
    with pytest.raises(FileExistsError):m.render(f,tmp_path/'out')


def test_source_hash_mismatch(tmp_path):
    s=sample();src=tmp_path/'source';src.write_text('test')
    s['sources']=[dict(path=str(src),sha256='0'*64)]
    f=tmp_path/'input.json';f.write_text(json.dumps(s))
    with pytest.raises(ValueError,match='source hash'):m.render(f,tmp_path/'out')


def test_overlap_refused_without_stagger(tmp_path):
    s=sample();s['tracks'][0]['genes'][1].update(start=1010,end=1610)
    f=tmp_path/'input.json';f.write_text(json.dumps(s))
    with pytest.raises(ValueError,match='overlap'):m.render(f,tmp_path/'out')
    assert not (tmp_path/'out/comparison.svg').exists()


def test_identity_overlap_is_refused(tmp_path):
    s=sample()
    for t in s['tracks']:
        for g in t['genes']:g['label']=''
    s['tracks'][0]['genes'][1].update(start=1010,end=1610)
    f=tmp_path/'input.json';f.write_text(json.dumps(s))
    with pytest.raises(ValueError,match='overlap'):m.render(f,tmp_path/'out')


def test_text_outside_canvas_is_refused(tmp_path):
    s=sample();s['title']='W'*400
    f=tmp_path/'input.json';f.write_text(json.dumps(s))
    with pytest.raises(ValueError,match='boundary'):m.render(f,tmp_path/'out')


def test_receipt_orientation_disagreement_rejected():
    s=sample();rows,_=m.layout(s)
    with pytest.raises(ValueError,match='receipt'):
        m.verify_drawn_orientation(s,rows,{'orientation':{'0':1,'1':1}})


def test_actual_wrong_arrow_is_rejected(tmp_path,monkeypatch):
    import matplotlib.patches as patches
    original=patches.FancyArrow
    def wrong(x,y,dx,dy,**kw):return original(x,y,-dx,dy,**kw)
    monkeypatch.setattr(patches,'FancyArrow',wrong)
    f=tmp_path/'input.json';f.write_text(json.dumps(sample()))
    with pytest.raises(ValueError,match='drawn strand'):m.render(f,tmp_path/'out')
    assert not (tmp_path/'out/comparison.png').exists()


def test_contig_markers_and_missing_stop_exported(tmp_path):
    s=sample();s['tracks'][0]['sequence_length']=4000
    s['tracks'][0]['genes'][1]['missing_stop_codon']=True
    f=tmp_path/'input.json';f.write_text(json.dumps(s))
    r=m.render(f,tmp_path/'out')
    assert r['assembly_markers']['0']=={'sequence_length':4000,'missing_stop_genes':['g2']}
    svg=(tmp_path/'out/comparison.svg').read_text()
    assert 'gene2*' in svg and 'contig end' in svg and 'Missing stop codon' in svg


def test_gene_beyond_sequence_refused():
    s=sample();s['tracks'][0]['sequence_length']=1
    with pytest.raises(ValueError,match='boundary'):m.validate(s)


def slide_sample():
    s=sample();s['display']=dict(label_rotation=40,font_size=10,width_in=14,axis_zero_track='1')
    s['tracks'][0]['kind']='bgc';s['tracks'][0]['identity']=dict(strain='SYNTHETIC',contig='CONTIG_A',region='region001',bgc='BGC001')
    return s


def test_slide_offset_is_rigid_and_actual_arrows_are_checked(tmp_path):
    s=slide_sample();before,_=m.layout(s);s['tracks'][0]['offset_bp']=2314.5;after,_=m.layout(s)
    for a,b in zip(before,after):
        shift=2314.5 if a['track']=='0' else 0
        assert b['display_start']==a['display_start']+shift
        assert b['display_end']==a['display_end']+shift
        assert b['display_strand']==a['display_strand']
    f=tmp_path/'in.json';f.write_text(json.dumps(s));r=m.render(f,tmp_path/'out')
    assert r['offset_bp']['0']==2314.5 and r['drawn_orientation_check']=='PASS'
    coordinates=json.loads((tmp_path/'out/display_coordinates.json').read_text())
    assert m.verify_drawn_orientation(s,coordinates['drawn_arrows'],r)


@pytest.mark.parametrize('field,value',[('offset_bp',float('nan')),('row',[]),('row',True),('label_side','inside'),('heading_side','right'),('heading_align','center')])
def test_invalid_track_display_rejected(field,value):
    s=slide_sample();s['tracks'][0][field]=value
    with pytest.raises(ValueError):m.validate(s)


@pytest.mark.parametrize('field,value',[('axis_zero_track','missing'),('font_size',True),('width_in',0),('label_rotation',float('inf'))])
def test_invalid_global_display_rejected(field,value):
    s=slide_sample();s['display'][field]=value
    with pytest.raises(ValueError):m.validate(s)


def test_slide_outer_text_axis_and_markers(tmp_path):
    s=slide_sample();s['tracks'][0]['sequence_length']=4000;s['tracks'][0]['genes'][0]['missing_stop_codon']=True
    f=tmp_path/'in.json';f.write_text(json.dumps(s));r=m.render(f,tmp_path/'out');svg=(tmp_path/'out/comparison.svg').read_text()
    assert r['display_view']=='slide' and r['axis_ticks_kb'][0]==0
    assert r['axis_zero_bp']==min(g['display_start'] for g in m.layout(s)[0] if g['track']=='1')
    assert any(x['text']=='gene1* 70%' for x in r['visible_gene_labels'])
    assert 'contig start' in svg and 'contig end' in svg and 'missing stop codon' in svg
    assert 'Colors and ribbons show' not in svg and 'assembly limit' not in svg
    assert all('70%' not in x['text'] for x in r['visible_gene_labels'] if x['track']=='1')


def test_slide_thins_collisions_and_records_omissions(tmp_path):
    s=slide_sample();s['tracks'][0]['genes'][1].update(start=1010,end=1610)
    f=tmp_path/'in.json';f.write_text(json.dumps(s));r=m.render(f,tmp_path/'out')
    assert len([x for x in r['visible_gene_labels'] if x['track']=='0'])==1
    assert len(r['omitted_gene_labels'])==1
    assert len(json.loads((tmp_path/'out/display_coordinates.json').read_text())['drawn_arrows'])==4


def test_shared_partner_row_headings_stack_and_middle_labels_are_absent(tmp_path):
    s=slide_sample();ref=s['tracks'][1];ref.update(label_side='none',heading_side='left')
    for tid in ('p1','p2'):
        t=copy.deepcopy(s['tracks'][0]);t.update(id=tid,row='partners',label_side='below',heading_side='below',label='A long partner heading that wraps across two lines '+tid,subtitle='Synthetic partner '+tid)
        s['tracks'].append(t)
    f=tmp_path/'in.json';f.write_text(json.dumps(s));r=m.render(f,tmp_path/'out')
    assert r['row_y']['p1']==r['row_y']['p2']<r['row_y']['1']<r['row_y']['0']
    assert not any(x['track']=='1' for x in r['visible_gene_labels'])
    assert len(r['omitted_gene_labels'])>=2  # labels across coincident partner tracks
    assert 'partner heading' in (tmp_path/'out/comparison.svg').read_text()


def test_slide_inward_heading_rejected(tmp_path):
    s=slide_sample();s['tracks'][0]['heading_side']='below'
    f=tmp_path/'in.json';f.write_text(json.dumps(s))
    with pytest.raises(ValueError,match='0.*ribbon'):m.render(f,tmp_path/'out')


def test_slide_wrong_actual_arrow_rejected(tmp_path,monkeypatch):
    import matplotlib.patches as patches
    original=patches.FancyArrow
    monkeypatch.setattr(patches,'FancyArrow',lambda x,y,dx,dy,**kw:original(x,y,-dx,dy,**kw))
    f=tmp_path/'in.json';f.write_text(json.dumps(slide_sample()))
    with pytest.raises(ValueError,match='drawn strand'):m.render(f,tmp_path/'out')
    assert not (tmp_path/'out/comparison.png').exists()


def test_slide_boundary_error_names_text(tmp_path):
    s=slide_sample();s['title']='OFFENDING_'+('W'*400)
    f=tmp_path/'in.json';f.write_text(json.dumps(s))
    with pytest.raises(ValueError,match="boundary.*OFFENDING_"):m.render(f,tmp_path/'out')


def test_no_bare_percentage_for_unlabelled_gene(tmp_path):
    s=slide_sample();s['tracks'][0]['genes'][0]['label']=''
    f=tmp_path/'in.json';f.write_text(json.dumps(s));r=m.render(f,tmp_path/'out')
    assert not any(x['track']=='0' and x['gene']=='g1' for x in r['visible_gene_labels'])


def test_heading_measured_gap_and_shared_row_stacking(tmp_path):
    s=slide_sample();s['tracks'][1].update(label_side='none',heading_side='left')
    for tid in ('p1','p2'):
        t=copy.deepcopy(s['tracks'][0]);t.update(id=tid,row='partners',label='Partner contig '+tid,label_side='below')
        s['tracks'].append(t)
    f=tmp_path/'in.json';f.write_text(json.dumps(s));r=m.render(f,tmp_path/'out')
    headings={x['track']:x for x in r['heading_placements']}
    assert headings['0']['offset_pt']==pytest.approx(headings['0']['label_extent_pt']+6)
    assert headings['p2']['offset_pt']>headings['p1']['offset_pt']
