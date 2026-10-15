"""Display reproducibility across fresh processes, without database or genome reads."""
import os, subprocess, sys, json, importlib.util
from pathlib import Path
SOURCE = Path(__file__).resolve().parents[1] / "tools/blastp_identity_figures.py"

def probe(seed):
    code = """import importlib.util,json,sys
s=importlib.util.spec_from_file_location('fig',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
keys=[('Genome α',i) for i in range(200)]+[('Genome β','NRPS',i) for i in range(200)]
print(json.dumps({'jitter':[m.stable_jitter(k,.5) for k in keys],'median':m.median([88.,95.])}))
"""
    env = dict(os.environ, PYTHONHASHSEED=str(seed), PYTHONDONTWRITEBYTECODE="1")
    return json.loads(subprocess.check_output([sys.executable,"-c",code,str(SOURCE)],env=env,text=True))

def test_fresh_processes_with_distinct_hash_seeds_agree():
    assert probe(0) == probe(1) == probe(42)

def test_offsets_stay_bounded_and_do_not_collapse():
    x=probe(0)['jitter']
    assert all(-.25 <= v < .25 for v in x)
    assert len(set(x)) > 50

def test_existing_even_count_median_is_preserved():
    assert probe(0)['median'] == 91.5
