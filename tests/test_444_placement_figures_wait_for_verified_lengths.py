from pathlib import Path
from types import SimpleNamespace
import json
import sys
import pytest
from tools import phylo_place as pp
from .test_m5_restored_graft_receipt import fixture_sources

@pytest.mark.parametrize("state", ["missing_reference", "not_reestimated", "estimated", "no_defaults"])
def test_report_holds_both_figure_routes_until_lengths_verified(tmp_path, monkeypatch, state):
    run, report, sources, native_calls=fixture_sources(tmp_path,monkeypatch,default=state!='no_defaults')
    if state=='missing_reference':sources['reference_tree'].unlink()
    monkeypatch.setattr(pp,'ROOT',str(tmp_path/'unused'))
    monkeypatch.setattr(pp,'_which',lambda name,*args:'synthetic-gappa' if name=='gappa' else sys.executable if state=='estimated' and name=='raxml-ng' else None)
    monkeypatch.setattr(pp,'_env',lambda *args:{})
    monkeypatch.setattr(pp,'_dedup_summary',lambda *args:None)
    consumed=[]
    monkeypatch.setattr(pp,'_grafted_neighborhoods',lambda tree,*args,**kwargs:consumed.append(('neighborhood',tree)) or 0)
    monkeypatch.setattr(pp,'_render_tree',lambda tree,*args,**kwargs:consumed.append(('python',tree)))
    monkeypatch.setattr(pp,'_color_strips_deliverable',lambda a,out,group,tree,*args,**kwargs:consumed.append(('strips',tree)) or {'requested':False,'state':'NOT_REQUESTED','variants':[],'artifacts':[]})
    args=SimpleNamespace(jplace=str(sources['jplace']),outdir=str(report),refpkg=str(sources['reference_tree'].parent),taxonomy=None)
    passed=state in {'estimated','no_defaults'}
    assert pp.cmd_report(args)==(0 if passed else 2)
    receipt=json.loads((report/'graft_length_evidence/receipt.json').read_text())
    assert receipt['state']==('PASS_LENGTH_QA' if passed else 'HOLD_LENGTH_QA')
    assert [name for name,_ in consumed]==(['neighborhood','python','strips'] if passed else [])
    assert all(str(tree).endswith('lengths_restored.newick') for _,tree in consumed)
    assert len(native_calls)==({'missing_reference':0,'not_reestimated':1,'estimated':2,'no_defaults':1}[state])
