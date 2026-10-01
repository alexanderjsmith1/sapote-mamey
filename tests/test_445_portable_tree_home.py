from pathlib import Path
from types import SimpleNamespace
import importlib.util
import pytest
from mamey.workspace_root import tree_home
ROOT=Path(__file__).resolve().parents[1]

def load_tool():
    spec=importlib.util.spec_from_file_location("portable_pp",ROOT/"tools/phylo_place.py")
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def test_default_tree_home_is_generic(tmp_path,monkeypatch):
    monkeypatch.delenv("SAPOTE_TREE_HOME",raising=False)
    assert tree_home(tmp_path)==tmp_path/"trees"

@pytest.mark.parametrize("configured",["custom trees","absolute"])
def test_configured_tree_home_binds_refpkg(tmp_path,monkeypatch,configured):
    chosen=tmp_path/"elsewhere" if configured=="absolute" else Path(configured)
    monkeypatch.setenv("SAPOTE_TREE_HOME",str(chosen));pp=load_tool();pp.ROOT=str(tmp_path)
    expected=chosen if chosen.is_absolute() else tmp_path/chosen
    assert pp._default_refpkg(SimpleNamespace(refpkg=None,outdir=None,group="rare_genera"))==str(expected/"_PLACEMENT/rare_genera/refpkg")

def test_explicit_outdir_precedes_tree_home(tmp_path,monkeypatch):
    monkeypatch.setenv("SAPOTE_TREE_HOME","custom");pp=load_tool()
    assert pp._default_refpkg(SimpleNamespace(refpkg=None,outdir=str(tmp_path/"result"),group="rare_genera"))==str(tmp_path/"result/refpkg")
