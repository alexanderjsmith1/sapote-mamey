"""Synthetic prebuilt-tree input contracts. No tree builds or biological data."""
from pathlib import Path
import importlib.util, os, sys
import pytest
ROOT=Path(os.environ.get('OUTGROUP_REVIEW_BASE',str(Path(__file__).resolve().parents[1])))
@pytest.fixture
def scan(monkeypatch):
    spec=importlib.util.spec_from_file_location('outgroup_contract_review',ROOT/'tools/mlsa_outgroup_scan.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    def forbidden(*a,**k):pytest.fail('Native build route must not run in these fixtures')
    monkeypatch.setattr(mod,'_run_builds',forbidden)
    return mod
GOOD='(((A,B),C),(D,E),X_OUTGROUP);'
CHANGED='(((A,C),B),(D,E),Y_OUTGROUP);'
def files(tmp_path,records):
    out=[]
    for name,text in records:
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text+'\n');out.append(str(p))
    return out

def test_colliding_directory_labels_preserve_all_requested_trees(scan,tmp_path,capsys):
    paths=files(tmp_path,[('same/a.treefile',CHANGED),('same/b.treefile',GOOD),('other/c.treefile',GOOD)])
    assert scan.main(['--trees',*paths])==0
    out=capsys.readouterr().out
    assert sum(' vs ' in line and '(normalized ' in line for line in out.splitlines())==3
    assert 'verdict: CHECK' in out and 'verdict: STABLE' not in out

def test_two_distinct_files_in_one_directory_are_compared(scan,tmp_path,capsys):
    paths=files(tmp_path,[('same/a.treefile',GOOD),('same/b.treefile',GOOD)])
    assert scan.main(['--trees',*paths])==0
    assert 'verdict: STABLE' in capsys.readouterr().out

def test_unique_display_labels_are_preserved(scan,tmp_path,capsys):
    paths=files(tmp_path,[('runA/a.treefile',GOOD),('runB/b.treefile',GOOD)])
    assert scan.main(['--trees',*paths])==0
    assert '  runA vs runB:' in capsys.readouterr().out

def test_repeated_exact_file_is_not_an_extra_tree(scan,tmp_path,capsys):
    paths=files(tmp_path,[('one/a.treefile',GOOD)])
    assert scan.main(['--trees',paths[0],paths[0]])==1
    out=capsys.readouterr()
    assert 'DUPLICATE_TREE_INPUT' in out.err and 'verdict: STABLE' not in out.out

def test_same_file_via_hardlink_is_not_an_extra_tree(scan,tmp_path,capsys):
    paths=files(tmp_path,[('one/a.treefile',GOOD)])
    alias=tmp_path/'alias.treefile';os.link(paths[0],alias)
    assert scan.main(['--trees',paths[0],str(alias)])==1
    out=capsys.readouterr()
    assert 'DUPLICATE_TREE_INPUT' in out.err and 'verdict: STABLE' not in out.out
