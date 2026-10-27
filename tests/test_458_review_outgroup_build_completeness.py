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

def arguments(tmp_path):
    ingroup=tmp_path/'ingroup';ingroup.mkdir()
    return ['--build','--ingroup-dir',str(ingroup),'--outgroup','A.fna','--outgroup','B.fna','--outgroup','C.fna','--workdir',str(tmp_path/'work')]

def test_failed_requested_build_prevents_global_stable(scan,tmp_path,capsys,monkeypatch):
    paths=files(tmp_path,[('one/a.treefile',GOOD),('two/b.treefile',GOOD)])
    monkeypatch.setattr(scan,'_run_builds',lambda *a,**k:{'A':paths[0],'B':paths[1]})
    assert scan.main(arguments(tmp_path))==1
    out=capsys.readouterr().out
    assert 'verdict: INSUFFICIENT' in out and '2 of 3' in out and 'verdict: STABLE' not in out

def test_all_requested_builds_keep_stable_control(scan,tmp_path,capsys,monkeypatch):
    paths=files(tmp_path,[('one/a.treefile',GOOD),('two/b.treefile',GOOD),('three/c.treefile',GOOD)])
    monkeypatch.setattr(scan,'_run_builds',lambda *a,**k:dict(zip(['A','B','C'],paths)))
    assert scan.main(arguments(tmp_path))==0
    assert 'verdict: STABLE' in capsys.readouterr().out

def test_zero_completed_builds_refuse(scan,tmp_path,capsys,monkeypatch):
    monkeypatch.setattr(scan,'_run_builds',lambda *a,**k:{})
    assert scan.main(arguments(tmp_path))==1
    assert 'verdict: INSUFFICIENT' in capsys.readouterr().out

def test_colliding_output_labels_refuse_before_staging(scan,tmp_path,capsys,monkeypatch):
    calls=[]
    def fake(*a,**k):calls.append(a);return {}
    monkeypatch.setattr(scan,'_run_builds',fake)
    work=tmp_path/'work'
    rc=scan.main(['--build','--ingroup-dir',str(tmp_path),'--outgroup','/one/same.fna','--outgroup','/two/same.fna','--workdir',str(work)])
    assert rc==1 and calls==[] and not work.exists()
    assert 'DUPLICATE_OUTGROUP_LABEL' in capsys.readouterr().err
