"""Tie-aware descriptive ladder checks on small generic trees."""
import importlib.util
import json
from pathlib import Path
import pytest

pytest.importorskip('Bio')
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('ladder_workflow',ROOT/'tools/ladder_test.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
MONO='((A_M:1,B_M:1):1,(C:1,D:1):1);'
SPAN='((A_M:1,C:1):1,(B_M:1,D:1):1);'


def analyse(tmp_path,text,pattern='_M'):
    path=tmp_path/'tree.nwk';path.write_text(text)
    return mod.analyse(str(path),pattern)


def test_opposite_neighbor_structures_have_expected_descriptive_values(tmp_path):
    mono=analyse(tmp_path,MONO);span=analyse(tmp_path,SPAN)
    assert mono['sister_obs']==1 and mono['sister_ratio']==3
    assert mono['mono'] and not mono['vacuous']
    assert span['sister_obs']==0 and span['vacuous']
    assert span['intruders']==span['total']-span['n']
    assert span['status']=='DESCRIPTIVE'


def test_ties_are_order_invariant_and_uniform_star_is_uninformative(tmp_path):
    views=[]
    for text in ('(A_M:1,C:1,B_M:1,D:1);','(C:1,D:1,A_M:1,B_M:1);','(B_M:1,D:1,C:1,A_M:1);'):
        result=analyse(tmp_path,text)
        views.append((result['sister_obs'],result['sister_ratio'],result['tie_frac']))
        assert result['status']=='UNINFORMATIVE'
    assert views[0]==views[1]==views[2]==(1/3,1.0,1.0)


@pytest.mark.parametrize('text,pattern',[(MONO,''),(MONO,'ZZZ'),(MONO,'A_'),(MONO,'_'),
    ('(A_M:1,A_M:1,C:1);','_M'),('((A_M,B_M),C);','_M'),
    ('(A_M:-1,B_M:1,C:1);','_M'),('(A_M:1e309,B_M:1,C:1);','_M')])
def test_invalid_or_vacuous_marked_data_rejected(tmp_path,text,pattern):
    # '_' matches all marked tips in MONO, so use a pattern that matches all tips explicitly.
    if pattern=='_': text='(A_M:1,B_M:1,C_M:1);';pattern='_M'
    with pytest.raises(ValueError): analyse(tmp_path,text,pattern)


def ladder(tmp_path,trees):
    for i,text in enumerate(trees):
        d=tmp_path/f'panel_{i}x';d.mkdir();(d/'tree.nwk').write_text(text)


def test_cli_never_promotes_ratio_to_biological_reading(tmp_path,capsys):
    ladder(tmp_path,[MONO,SPAN])
    assert mod.main([str(tmp_path),'panel','_M'])==0
    result=json.loads(capsys.readouterr().out)
    assert result['interpretation'].startswith('UNDETERMINED')
    assert len(result['panels'])==2


def test_missing_rung_tree_is_not_silently_skipped(tmp_path):
    ladder(tmp_path,[MONO,MONO]);(tmp_path/'panel_1x/tree.nwk').unlink()
    assert mod.main([str(tmp_path),'panel','_M'])==2


def test_ambiguous_tree_selection_refused(tmp_path):
    ladder(tmp_path,[MONO,MONO]);(tmp_path/'panel_1x/other.nwk').write_text(MONO)
    assert mod.main([str(tmp_path),'panel','_M'])==2


def test_membership_changes_across_rungs_refused(tmp_path):
    ladder(tmp_path,[MONO,MONO.replace('B_M','Z_M')])
    assert mod.main([str(tmp_path),'panel','_M'])==2


def test_all_tied_rung_has_nonzero_cli_status(tmp_path):
    ladder(tmp_path,[MONO,'(A_M:1,B_M:1,C:1,D:1);'])
    assert mod.main([str(tmp_path),'panel','_M'])==2
