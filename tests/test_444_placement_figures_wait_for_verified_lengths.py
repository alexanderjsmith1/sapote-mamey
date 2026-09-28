from pathlib import Path
from types import SimpleNamespace
import pytest
from tools import phylo_place as pp, graft_integrity as gi

@pytest.mark.parametrize("state", ["missing_reference", "not_reestimated", "estimated", "no_defaults"])
def test_report_holds_both_figure_routes_until_lengths_verified(tmp_path, monkeypatch, state):
    jp=tmp_path/'input.jplace'; jp.write_text('{}')
    graft=tmp_path/'input.newick'; graft.write_text('(A:0.1,Q1:0.1053605157);')
    refpkg=tmp_path/'refpkg'; refpkg.mkdir()
    if state!='missing_reference': (refpkg/'ref.tree').write_text('(A:0.1);')
    monkeypatch.setattr(pp,'ROOT',str(tmp_path/'unused'))
    monkeypatch.setattr(pp,'_which',lambda name,*args:'stub' if name=='gappa' else None)
    monkeypatch.setattr(pp,'_env',lambda *args:{})
    monkeypatch.setattr(gi,'generate_checked_graft',lambda *args:str(graft))
    defaults=[] if state=='no_defaults' else ['Q1']
    how='RAXML_NG_EVALUATE' if state=='estimated' else 'NOT_REESTIMATED'
    monkeypatch.setattr(gi,'generate_length_restored_graft',lambda *args,**kwargs:(str(graft),0,defaults,how))
    def table(jplace,tsv,*args): Path(tsv).write_text('query\tbest_edge_lwr\nQ1\t1.0\n')
    monkeypatch.setattr(pp,'_jplace_besthit_tsv',table)
    monkeypatch.setattr(pp,'_jplace_placements_tsv',table)
    monkeypatch.setattr(pp,'_jplace_query_names',lambda *args:['Q1'])
    monkeypatch.setattr(pp,'_grafted_neighborhoods',lambda *args,**kwargs:0)
    monkeypatch.setattr(pp,'_dedup_summary',lambda *args:None)
    calls=[]
    monkeypatch.setattr(pp,'_render_tree',lambda *args,**kwargs:calls.append('python'))
    monkeypatch.setattr(pp,'_color_strips_deliverable',lambda *args,**kwargs:calls.append('strips'))
    args=SimpleNamespace(jplace=str(jp),outdir=str(tmp_path),refpkg=str(refpkg),taxonomy=None)
    assert pp.cmd_report(args)==0
    assert calls==(['python','strips'] if state in {'estimated','no_defaults'} else [])
