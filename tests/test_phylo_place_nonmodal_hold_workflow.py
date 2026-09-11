"""Minority reference genera do not justify broad outgroup exemptions."""
import importlib.util
from io import StringIO
from pathlib import Path
import pytest

pytest.importorskip('Bio')
pytest.importorskip('matplotlib')
from Bio import Phylo

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('phylo_place_nonmodal_hold',ROOT/'tools/phylo_place.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
MULTI='((SID1_query:0.01,Streptomyces_a:0.01):0.01,(Streptomyces_b:0.01,Kitasatospora_ref1:0.02):0.01,Nonomuraea_ref2:0.02);'
SINGLE=MULTI.replace('Nonomuraea_ref2','Streptomyces_c')


def test_proposed_minority_set_is_not_an_exclusive_clade():
    tree=Phylo.read(StringIO(MULTI),'newick')
    minority=[t for t in tree.get_terminals() if t.name.startswith(('Kitasatospora','Nonomuraea'))]
    assert tree.is_monophyletic(minority) is False
    assert len(tree.common_ancestor(minority).get_terminals())>len(minority)


def test_nonmodal_multi_genus_does_not_get_a_broader_hint(tmp_path,monkeypatch):
    path=tmp_path/'tree.nwk';path.write_text(MULTI)
    hints=[]
    def gate(path,outgroup=None):
        hints.append(outgroup);return False,'outgroup evidence required'
    monkeypatch.setattr(mod,'_graft_sane',gate)
    with pytest.raises(RuntimeError,match='outgroup evidence required'):
        mod._render_tree(str(path),{},str(tmp_path/'figure.png'),str(tmp_path/'figure.svg'),'fixture')
    assert hints==[None]
    assert not (tmp_path/'figure.png').exists()


def test_supplied_multigenus_fixture_is_refused_by_real_gate(tmp_path):
    path=tmp_path/'tree.nwk';path.write_text(MULTI)
    with pytest.raises(RuntimeError,match='NO_OUTGROUP'):
        mod._render_tree(str(path),{},str(tmp_path/'figure.png'),str(tmp_path/'figure.svg'),'fixture')


def test_legacy_single_genus_hint_preserved_without_claiming_validation(tmp_path,monkeypatch):
    path=tmp_path/'tree.nwk';path.write_text(SINGLE)
    hints=[]
    def gate(path,outgroup=None): hints.append(outgroup);return False,'hold for test'
    monkeypatch.setattr(mod,'_graft_sane',gate)
    with pytest.raises(RuntimeError):
        mod._render_tree(str(path),{},str(tmp_path/'figure.png'),str(tmp_path/'figure.svg'),'fixture')
    assert hints==['Kitasatospora']
