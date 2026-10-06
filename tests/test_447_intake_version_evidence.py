"""Version admission exercises actual batch control flow with a fake engine."""
import csv
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
HARNESS=ROOT/'tools/intake_harness.py'


def fake_batch(tmp_path,monkeypatch,manifest):
    spec=importlib.util.spec_from_file_location('intake_version_under_test',HARNESS)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    source=tmp_path/'synthetic_fixture.zip';source.write_bytes(b'fixture; never extracted')
    out=tmp_path/'out';registry=out/'registry.csv';metrics=out/'metrics.csv'
    monkeypatch.setattr(sys,'argv',['intake_harness.py','--inputs',str(source),'--outdir',str(out),
        '--registry',str(registry),'--metrics',str(metrics),'--release','PRIVATE'])
    monkeypatch.setattr(module,'detect_and_stage',lambda *args:('ANTISMASH',str(source),None,'Synthetic fixture'))
    calls={'summary':0,'rescue':0,'cores':0}
    def fake_engine(*args,**kwargs):
        package=out/'synthetic_fixture/package';package.mkdir(parents=True)
        if manifest!='ABSENT':
            value={'mamey_version':module._BUNDLE_ENGINE_VERSION} if manifest=='MATCH' else manifest
            (package/'manifest_short.json').write_text('{invalid' if value=='MALFORMED' else json.dumps(value))
        return 0,.01,1.,'synthetic engine diagnostic'
    def summary(log):
        calls['summary']+=1;return {'assembly_tier':'SYNTHETIC','raw_bgcs':0}
    def rescue(*args):
        calls['rescue']+=1;return {k:0 for k in ['rescue_leads','rescue_HIGH','rescue_MODERATE','IDC_split_HIGH']}
    def cores(*args):calls['cores']+=1;return ''
    monkeypatch.setattr(module,'run_monitored',fake_engine)
    monkeypatch.setattr(module,'parse_run_summary',summary)
    monkeypatch.setattr(module,'rescue_summary',rescue)
    monkeypatch.setattr(module,'cores_present',cores)
    code=module.main()
    rows=list(csv.DictReader(metrics.open()))
    return code,registry,rows,calls


@pytest.mark.parametrize('manifest',['ABSENT','MALFORMED',{}, {'mamey_version':None},
    [], {'mamey_version':''}, {'mamey_version':123}, {'mamey_version':'WRONG_ENGINE'}])
def test_unknown_or_mismatched_version_cannot_bank_success(tmp_path,monkeypatch,manifest):
    code,registry,rows,calls=fake_batch(tmp_path,monkeypatch,manifest)
    assert code==1 and rows[0]['status']=='RUN_FAILED'
    assert not registry.exists()
    assert calls=={'summary':0,'rescue':0,'cores':0}


def test_matching_version_control_can_bank(tmp_path,monkeypatch):
    code,registry,rows,calls=fake_batch(tmp_path,monkeypatch,'MATCH')
    assert code==0 and rows[0]['status']=='OK'
    assert registry.exists() and calls=={'summary':1,'rescue':1,'cores':1}

