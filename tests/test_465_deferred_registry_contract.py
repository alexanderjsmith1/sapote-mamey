"""Deferred lookups preserve introspection and direct-import compatibility."""
import ast
import importlib
import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('name',['load_registry','find_row'])
def test_registry_docstrings_remain_available(name):
    module=ast.parse((ROOT/'tools/outgroup_registry.py').read_text())
    fn=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name==name)
    assert ast.get_docstring(fn),f'{name} must retain its callable documentation'

@pytest.mark.parametrize('module_name,attribute,lookup',[
    ('phylo_16s_build_db','DB','rrna16s_db'),
    ('phylo_16s_build_db','BLASTDB','refseq_16s_blastdb'),
    ('phylo_16s_from_genome','DB','refseq_16s_blastdb')])
def test_direct_constant_import_and_explicit_bound_override(monkeypatch,module_name,attribute,lookup):
    monkeypatch.syspath_prepend(str(ROOT/'tools'))
    mod=importlib.import_module(module_name)
    monkeypatch.delitem(mod.__dict__,attribute,raising=False)
    monkeypatch.setattr(mod._p16,lookup,lambda *a,**kw:'synthetic-selected-location')
    scope={};exec(f'from {module_name} import {attribute}',scope)
    assert scope[attribute]=='synthetic-selected-location'
    assert mod._bound(attribute)=='synthetic-selected-location'
    monkeypatch.setitem(mod.__dict__,attribute,'synthetic-explicit-binding')
    assert mod._bound(attribute)=='synthetic-explicit-binding'
