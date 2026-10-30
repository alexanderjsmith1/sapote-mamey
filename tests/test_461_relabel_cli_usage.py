"""CLI help/admission must work without reading inputs or invoking a renderer."""
from pathlib import Path
import os,subprocess,sys
import pytest
SCRIPT=Path(__file__).resolve().parents[1]/'tools/relabel_and_render.py'
@pytest.mark.parametrize('args,code,stream',[(['--help'],0,'stdout'),([],2,'stderr'),(['missing.tree','missing genomes','never.png'],2,'stderr')])
def test_usage_before_inputs_or_rendering(tmp_path,args,code,stream):
 p=subprocess.run([sys.executable,'-B',str(SCRIPT),*args],cwd=tmp_path,capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
 assert p.returncode==code and 'usage:' in getattr(p,stream)
 assert 'Traceback' not in p.stderr
 assert not list(tmp_path.iterdir())
