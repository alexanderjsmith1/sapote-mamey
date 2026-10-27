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

def test_partial_pair_measurement_refuses_global_stable(scan,tmp_path,capsys):
    paths=files(tmp_path,[('one/a.treefile',GOOD),('two/b.treefile',GOOD),('three/c.treefile','(A,B,Z_OUTGROUP);')])
    assert scan.main(['--trees',*paths])==1
    out=capsys.readouterr().out
    assert 'verdict: INSUFFICIENT' in out and 'verdict: STABLE' not in out

def test_measured_match_remains_stable(scan,tmp_path,capsys):
    paths=files(tmp_path,[('one/a.treefile',GOOD),('two/b.treefile',GOOD)])
    assert scan.main(['--trees',*paths])==0
    assert 'verdict: STABLE' in capsys.readouterr().out

def test_measured_rearrangement_remains_check(scan,tmp_path,capsys):
    paths=files(tmp_path,[('one/a.treefile',GOOD),('two/b.treefile',CHANGED)])
    assert scan.main(['--trees',*paths])==0
    assert 'verdict: CHECK' in capsys.readouterr().out

def test_all_unmeasured_pairs_refuse(scan,tmp_path,capsys):
    paths=files(tmp_path,[('one/a.treefile','(A,B,X_OUTGROUP);'),('two/b.treefile','(A,B,Y_OUTGROUP);')])
    assert scan.main(['--trees',*paths])==1
    assert 'verdict: INSUFFICIENT' in capsys.readouterr().out
