"""CLI admission must distinguish absent input from an available empty source."""
import json,os,subprocess,sys
from pathlib import Path
SCRIPT=Path(__file__).resolve().parents[1]/'tools/kcb_confidence.py'
def call(*args):
 return subprocess.run([sys.executable,'-B',str(SCRIPT),*map(str,args)],capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
def test_help_is_help():
 p=call('--help');assert p.returncode==0 and 'usage:' in p.stdout and 'n_kcb_hits' not in p.stdout
def test_no_argument_is_usage():
 p=call();assert p.returncode==2 and 'usage:' in p.stderr and 'Traceback' not in p.stderr
def test_missing_directory_is_refused(tmp_path):
 p=call(tmp_path/'absent');assert p.returncode==2 and 'KCB_CONFIDENCE_SOURCE_UNAVAILABLE' in p.stderr and not p.stdout

def test_missing_index_is_refused(tmp_path):
 p=call(tmp_path);assert p.returncode==2 and 'KCB_CONFIDENCE_SOURCE_UNAVAILABLE' in p.stderr and not p.stdout

def test_available_empty_index_keeps_zero(tmp_path):
 (tmp_path/'index.html').write_text('<html><body><table></table></body></html>')
 p=call(tmp_path);assert p.returncode==0 and json.loads(p.stdout)['summary']['n_kcb_hits']==0
