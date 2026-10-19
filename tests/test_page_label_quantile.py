"""Four fabricated points; real selection and table/caption serialization, no draw or fit."""
import copy
import csv
import pytest
from tools import protein_pcoa_render as render
from tools import protein_pcoa_page_docs as docs


def record(layout, q, groups, threshold):
    return dict(page=[layout], legend={'iso_low':'synthetic query protein, closest match'},
                cohort_genomes={'SYN_Q':1}, n_cohort_points=1, n_low=0, n_mid=0, n_high=1,
                n_unknown=0, n_ref_centroids=3, n_ref=3, n_reference_genomes=1,
                n_mibig_centroids=0, n_mibig=0, label_below=70., mid_below=85.,
                title='Synthetic saved-coordinate control',
                labels={layout:dict(numbered=False,labelled=len(groups),outlier_groups=len(groups),threshold=threshold)},
                leader_max_in=.35,prefix='SYNTHETIC',set='SYNTHETIC',panel='query',
                pct_axes=[30.,20.],quantile=q)


@pytest.mark.parametrize('layout',['pcoa','trimap','tsne'])
@pytest.mark.parametrize('q,threshold,groups',[(.5,1.,[[0]]),(.95,2.8,[])])
def test_four_points_keep_selection_and_serialize_actual_quantile(tmp_path,layout,q,threshold,groups):
    bg=[(0.,0.),(1.,0.),(4.,0.)]
    query=[dict(x=2.5,y=0.,strain='SYN_Q',pid=95.,row={},identity_state='AVAILABLE')]
    original=copy.deepcopy((bg,query))
    selected,texts,t,numbered=render.choose_labels(query,bg,q=q,span=4.)
    assert selected==groups and t==pytest.approx(threshold)
    assert (bg,query)==original and not numbered
    labels=[dict(drawn='yes',label_text='Synthetic Q',strain='SYN_Q')] if groups else []
    caption=docs.caption_text(record(layout,q,groups,t),labels,{'SYN_Q':'Synthetic query'},None)
    assert f'than {q*100:g}%' in caption
    if q==.5: assert 'than 95%' not in caption
    b=dict(cpts=query,all_groups=groups,unknown=[False],low=[False],mid=[False],dist=[1.5],threshold=t)
    placed=[[dict(rank=1,text='Synthetic Q',res=None)]] if groups else [[]]
    path=tmp_path/'labels.tsv'
    schema=render.write_page_labels(path,[layout],[b],placed,{'SYN_Q':1},{},q)
    with path.open() as stream:
        reader=csv.DictReader(stream,delimiter='\t'); rows=list(reader); fields=reader.fieldnames
    assert fields[-2:]==['threshold_distance','label_quantile']
    assert 'threshold_p95' in fields and schema['version']==2
    assert schema['quantile']==q and f'p{q*100:g}' in schema['label_rule']
    if groups:
        assert float(rows[0]['threshold_distance'])==pytest.approx(t)
        assert float(rows[0]['label_quantile'])==q
        assert rows[0]['threshold_p95']==('' if q!=.95 else f'{t:.5f}')
    else: assert rows==[]


def test_default_legacy_column_retains_value(tmp_path):
    query=[dict(x=7.,y=0.,strain='SYN_Q',pid=95.,row={},identity_state='AVAILABLE')]
    groups,_,threshold,_=render.choose_labels(query,[(0.,0.),(1.,0.),(4.,0.)],q=.95,span=7.)
    assert groups==[[0]] and threshold==pytest.approx(2.8)
    b=dict(cpts=query,all_groups=groups,unknown=[False],low=[False],mid=[False],dist=[3.],threshold=threshold)
    path=tmp_path/'default.tsv'
    render.write_page_labels(path,['pcoa'],[b],[[dict(rank=1,text='Synthetic Q',res=None)]],{}, {},.95)
    with path.open() as stream: row=next(csv.DictReader(stream,delimiter='\t'))
    assert row['threshold_p95']==row['threshold_distance']=='2.80000'


def test_legacy_caption_without_quantile_uses_historical_default():
    rec=record('pcoa',.95,[[0]],2.8);del rec['quantile'];before=copy.deepcopy(rec)
    text=docs.caption_text(rec,[dict(drawn='yes',label_text='Synthetic Q',strain='SYN_Q')],{},None)
    assert 'than 95%' in text and rec==before


@pytest.mark.parametrize('q',['nan','-0.1','1.1'])
def test_invalid_quantile_refused_before_output(tmp_path,q):
    out=tmp_path/'new'
    assert render.main(['--kit',str(tmp_path/'absent'),'--out',str(out),
                        '--cohort-table','absent','--panel','query=g','--quantile',q])==2
    assert not out.exists()


def test_existing_complete_packet_is_not_rewritten(tmp_path):
    out=tmp_path/'old';out.mkdir()
    original={'render_receipt.json':b'{"status":"COMPLETE"}\n','LABELS_SYN_PAGE.tsv':b'threshold_p95\n1.00000\n'}
    for name,value in original.items(): (out/name).write_bytes(value)
    assert render.main(['--kit',str(tmp_path/'absent'),'--out',str(out),
                        '--cohort-table','absent','--panel','query=g','--quantile','.5'])==2
    assert {p.name:p.read_bytes() for p in out.iterdir()}==original
