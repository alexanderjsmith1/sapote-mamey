"""Portable exact-ID adapter: scope stays in factory receipts, never renderer heuristics."""
import csv
import hashlib
import json
from pathlib import Path
import pytest
from tools.build_tree_tracks import prepare, TrackHold

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def fixture(root):
    root.mkdir(exist_ok=True)
    metadata=root/'metadata.tsv'
    metadata.write_text('tip\tstrain\tlabel\trole\nquery_A\tstrain-1\tExample alpha\tquery\nquery_B\tstrain-2\tExample beta\tquery\nref_A\t\tReference as deposited\treference\nroot_A\t\tOutgroup as deposited\toutgroup\n')
    factory=root/'factory'; factory.mkdir()
    track=factory/'bioassay_tree_track.tsv'
    track.write_text('strain\tchannel\tfeature\tvalue\tstate\nstrain-1\tBIOASSAY\tselected\t0\tOBSERVED\nstrain-2\tBIOASSAY\tselected\t\tNOT_MEASURED\n')
    selection=dict(selection_id='selected',target='Example target',target_state='VERIFIED',timepoint_hours=48,material_type='CRUDE_EXTRACT',final_concentration_ug_ml=120,aggregation='mean_inhibition_pct',strain_roster=['strain-1','strain-2'],material_ids_by_strain={'strain-1':'material-A','strain-2':'material-B'})
    caption=factory/'bioassay_caption_methods.json'
    caption.write_text(json.dumps(dict(tree_overlay_state='EMITTED_EXPLICIT_SELECTION',tree_track_selection=selection)))
    receipt=factory/'bioassay_figure_factory_receipt.json'
    receipt.write_text(json.dumps(dict(status='PASS_DATA_READY_R_NOT_REQUESTED',outputs=[dict(logical_locator=p.name,sha256=sha(p)) for p in [track,caption]])))
    config=root/'config.json'
    config.write_text(json.dumps(dict(schema='sapote.tree-tracks.v1',input_root='.',metadata=dict(path=metadata.name,sha256=sha(metadata)),tracks=[dict(column='selected_value',label='Selected material',colour='#287D8E',receipt=dict(path='factory/'+receipt.name,sha256=sha(receipt)))])))
    return config

def test_exact_values_and_missingness_survive_relocation(tmp_path):
    config=fixture(tmp_path/'any-project')
    out=prepare(config,tmp_path/'out')
    rows=list(csv.DictReader((out/'tracks.tsv').open(),delimiter='\t'))
    assert [r['selected_value'] for r in rows]==['0','','','']
    assert rows[2]['label']=='Reference as deposited'
    assert json.loads((out/'track_adapter_receipt.json').read_text())['status']=='PASS_EXACT_ADMITTED_VALUES'
    with pytest.raises(FileExistsError):prepare(config,out)

@pytest.mark.parametrize('defect',['hash','duplicate_tip','alias','nonfinite','unmeasured_value','duplicate_track','escape','selection','extra_strain'])
def test_invalid_inputs_refused_without_output(tmp_path,defect):
    config=fixture(tmp_path/'project');root=config.parent;data=json.loads(config.read_text())
    track=root/'factory/bioassay_tree_track.tsv';caption=root/'factory/bioassay_caption_methods.json';receipt=root/'factory/bioassay_figure_factory_receipt.json';meta=root/'metadata.tsv'
    if defect=='duplicate_tip':meta.write_text(meta.read_text().replace('query_B','query_A'))
    elif defect=='alias':meta.write_text(meta.read_text().replace('strain-1','strain_1'))
    elif defect=='hash':track.write_text(track.read_text().replace('\t0\t','\t12\t'))
    elif defect=='nonfinite':track.write_text(track.read_text().replace('\t0\t','\tNaN\t'))
    elif defect=='unmeasured_value':track.write_text(track.read_text().replace('\t\tNOT_MEASURED','\t0\tNOT_MEASURED'))
    elif defect=='duplicate_track':track.write_text(track.read_text()+track.read_text().splitlines()[1]+'\n')
    elif defect=='escape':data['metadata']['path']='../metadata.tsv'
    elif defect=='selection':caption.write_text(json.dumps(dict(tree_overlay_state='REQUIRES_SELECTION')))
    elif defect=='extra_strain':track.write_text(track.read_text()+'strain-3\tBIOASSAY\tselected\t1\tOBSERVED\n')
    if defect!='hash':
        r=json.loads(receipt.read_text())
        for a in r['outputs']:a['sha256']=sha(receipt.parent/a['logical_locator'])
        receipt.write_text(json.dumps(r))
    data['tracks'][0]['receipt']['sha256']=sha(receipt);data['metadata']['sha256']=sha(meta);config.write_text(json.dumps(data))
    with pytest.raises((TrackHold,FileNotFoundError)):prepare(config,tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_real_factory_output_adapts_after_relocation(tmp_path, monkeypatch):
    import shutil
    from mamey import bioassay_figure_factory as factory
    source = Path(__file__).resolve().parents[1] / 'examples/tree_tracks'
    project = tmp_path / 'relocated'
    shutil.copytree(source, project)
    monkeypatch.chdir(project)
    config = json.loads((project/'factory_48.json').read_text())
    config['output_dir'] = 'fresh_factory'
    (project/'fresh.json').write_text(json.dumps(config))
    assert factory.build(project/'fresh.json')['status'] == 'PASS_DATA_READY_R_NOT_REQUESTED'
    assert (project/'fresh_factory/bioassay_tree_track.tsv').read_bytes() == (project/'factory_48/bioassay_tree_track.tsv').read_bytes()
    adapter = json.loads((project/'single.json').read_text())
    receipt = project/'fresh_factory/bioassay_figure_factory_receipt.json'
    adapter['tracks'][0]['receipt'] = {'path':'fresh_factory/'+receipt.name,'sha256':sha(receipt)}
    (project/'fresh_adapter.json').write_text(json.dumps(adapter))
    out=prepare(project/'fresh_adapter.json',tmp_path/'adapted')
    rows=list(csv.DictReader((out/'tracks.tsv').open(),delimiter='\t'))
    assert [r['value_48'] for r in rows] == ['72.0','0.0','-10.0','','','']
