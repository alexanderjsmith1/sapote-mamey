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

def test_empty_restriction_has_no_bipartitions(scan):
    assert scan.bipartitions(scan._parse(GOOD),set())==set()

def test_none_restriction_keeps_unrestricted_behavior(scan):
    root=scan._parse(GOOD)
    assert scan.bipartitions(root,None)==scan.bipartitions(root)
    assert scan.bipartitions(root)

@pytest.mark.parametrize('other',['((E,F),(G,H),Y_OUTGROUP);','((E,F),(G,H),X_OUTGROUP);'])
def test_disjoint_ingroup_is_unmeasured(scan,other):
    assert scan.rf_distance('((A,B),(C,D),X_OUTGROUP);',other)==(0,0,0)

def test_disjoint_cli_has_no_supported_verdict(scan,tmp_path,capsys):
    paths=files(tmp_path,[('one/a.treefile','((A,B),(C,D),X_OUTGROUP);'),('two/b.treefile','((E,F),(G,H),Y_OUTGROUP);')])
    assert scan.main(['--trees',*paths])==1
    out=capsys.readouterr().out
    assert 'verdict: INSUFFICIENT' in out and 'verdict: CHECK' not in out and 'verdict: STABLE' not in out
