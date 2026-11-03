import importlib.util
from pathlib import Path
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('fixture444', ROOT/'tests/test_444_gap_directed_rescue.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)

@pytest.mark.parametrize('bad', ['unknown\tq000001\t90\t60\t50\n',
    'g001\tunknown\t90\t60\t50\n', 'g001\tq000001\t90\t60\t50\t1\t9999\n',
    'g001\tq000001\t90\t60\t50\t100\t1\n'])
def test_precomputed_rows_bound_before_output(tmp_path, bad):
    genome, ref, hits = fixture._setup(tmp_path)
    with hits.open('a') as f: f.write(bad)
    out=tmp_path/'out'
    run=subprocess.run([sys.executable, str(ROOT/'tools/gap_directed_rescue.py'), '--zip',str(genome),
        '--label','T','--core','ctgA.region001','--reference',str(ref),'--out',str(out),
        '--hits',str(hits),'--no-figure','--no-gene-table'],capture_output=True,text=True)
    assert run.returncode != 0 and 'GAP_RESCUE_HIT_BINDING_INVALID' in run.stderr
    assert not out.exists()
