"""The no-draw panel result is the actual input to page assembly."""
import copy,json
from pathlib import Path
from types import SimpleNamespace
import pytest
from tools import protein_pcoa_render as ppr

@pytest.mark.parametrize('bound',[False,True])
def test_spec_only_preserves_full_axis_metadata_for_page(tmp_path,bound):
    rows=[dict(id='SYN_R1',PC1=0.,PC2=0.,n_represented=1,source='reference',strain='SYN_R'),dict(id='SYN_R2',PC1=1.,PC2=1.,n_represented=1,source='reference',strain='SYN_R'),dict(id='SYN_Q1',PC1=2.,PC2=2.,n_represented=1,source='isolate',strain='SYN_Q')]
    original=copy.deepcopy(rows);run=dict(pct_axes=[150.,0.,-50.]);axes=ppr.axis_metadata(run)
    if bound:
        # Synthetic already-admitted association fixture, not a live fit assertion.
        axes.update(definition=dict(state='NATIVE_COORDINATE_SOURCE_BOUND',source={'sha256':'synthetic fixture'}),fit_execution='RECORDED_SUCCESSFUL_RESOURCE_CHAIN')
    a=SimpleNamespace(drop_origins=None,exclude_strain=[],label_below=70.,mid_below=85.,top_strains=0,quantile=.95,number_above=30,_axis_metadata_by_set={'KS':axes})
    panel=ppr.build_panel(a,'KS',rows,{'SYN_Q1':95.},run,{'SYN_Q':'g'},'query',{'g'},'#0072B2','Synthetic isolates',{},tmp_path,'r',spec_only=True)
    assert panel['axis_metadata'] is axes
    assert panel['axis_metadata']['pct_axes']==[150.,0.,-50.]
    assert panel['axis_metadata']['definition']==axes['definition']
    assert rows==original
    assert [(p['x'],p['y']) for p in panel['spec']['points']]==[(0.,0.),(1.,1.),(2.,2.)]
    assert not list(tmp_path.iterdir()),'Spec-only assembly must not draw or write an artifact'
