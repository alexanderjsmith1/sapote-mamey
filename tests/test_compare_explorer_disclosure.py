"""Consumer disclosure without a fit; native text geometry is checked separately."""
import json
from pathlib import Path
import pytest
from tests import test_449_protein_pcoa_compare as old_compare
from tests import test_446_pcoa_bgc_explorer as old_explorer


def test_comparison_retains_full_supplied_ratios_without_native_claim(tmp_path):
    kit=old_compare._kit(tmp_path)
    rf=kit/'out_KS/RUN_KS.json';run=json.loads(rf.read_text())
    run.update(pct_axes=[150.,0.,-50.],axis_metadata={'definition':{'state':'NATIVE_COORDINATE_SOURCE_BOUND'}})
    rf.write_text(json.dumps(run));before=rf.read_bytes()
    mod=old_compare._load();out=tmp_path/'out'
    assert mod.main(['--kit',str(kit),'--cohort',str(tmp_path/'cohort.tsv'),'--out',str(out),
                     '--no-figures','--permutations','10'])==0
    annotation=json.loads((out/'AXIS_ANNOTATIONS.json').read_text())['KS']
    assert annotation['pct_axes']==[150.,0.,-50.]
    assert annotation['definition']['state']=='SUPPLIED_UNVERIFIED'
    assert annotation['consumer_fit_execution']=='NOT_EXECUTED'
    caption=(out/'CAPTION.md').read_text()
    assert 'not variance explained' in caption and '150' in caption and '-50' in caption
    assert rf.read_bytes()==before


def test_explorer_built_set_and_visible_note_disclose_supplied_axes(tmp_path):
    kit=old_explorer.kit.__wrapped__(tmp_path)
    rf=kit/'kit/out_KS/RUN_KS.json';run=json.loads(rf.read_text());run['pct_axes']=[150.,0.,-50.]
    rf.write_text(json.dumps(run));before=rf.read_bytes()
    assert old_explorer.run(kit)==0
    record=old_explorer.js(kit/'out/data/sets/KS.js')
    assert record['pct']==[150.,0.,-50.]
    assert record['axis_annotations']['definition']['state']=='SUPPLIED_UNVERIFIED'
    assert record['axis_annotations']['consumer_fit_execution']=='NOT_EXECUTED'
    assert 'not variance explained' in record['axis_annotations']['disclosure']
    html=(kit/'out/index.html').read_text()
    assert 'id="axisnote"' in html and 'D.axis_annotations' in html
    assert 'all-against-all protein search, classical PCoA' not in html
    assert rf.read_bytes()==before


@pytest.mark.parametrize('floor',['7','nan','inf'])
def test_comparison_refuses_unsupported_floor_before_output(tmp_path,floor):
    mod=old_compare._load();out=tmp_path/'out'
    assert mod.main(['--kit','missing','--cohort','missing','--out',str(out),'--min-text-pt',floor])==2
    assert not out.exists()


@pytest.mark.parametrize('values',[[1.],[1.,float('nan')],[True,2.]])
def test_invalid_axis_annotations_refuse(values):
    from tools.protein_pcoa_annotations import supplied_axis_annotations
    with pytest.raises(ValueError): supplied_axis_annotations({'pct_axes':values})


def test_missing_annotations_produce_plain_axis_labels():
    from tools.protein_pcoa_annotations import supplied_axis_annotations,supplied_axis_label
    annotations=supplied_axis_annotations({})
    assert annotations['state']=='NOT_PROVIDED' and annotations['pct_axes'] is None
    assert supplied_axis_label(annotations,0)=='PCoA 1'
    assert supplied_axis_label(annotations,1)=='PCoA 2'
