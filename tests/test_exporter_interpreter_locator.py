"""Selected exporter interpreter survives stage cd; fake executables only, no tier run."""
import json,os,re,subprocess,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
BUILDER=ROOT/'tools/make_public_tier.sh'

def locator(text):
 return text.split('# BEGIN EXPORTER PYTHON LOCATOR',1)[1].split('# END EXPORTER PYTHON LOCATOR',1)[0]

def stage_call(text):
 # Extract the actual staged pytest interpreter call, omit its global log redirection.
 found=re.search(r'\( cd "\$STAGE" && PYTHONPATH="\$STAGE" "\$PYTHON" -m pytest -p no:randomly -q',text)
 assert found is not None
 return found.group()+" )\n"

def fake(path,label,version=(3,12,0),broken=False):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text('#!'+sys.executable+'\n'+'''import json,os,sys
args=sys.argv[1:]
with open(os.environ['LOCATOR_LOG'],'a') as h:h.write(json.dumps({'label':LABEL,'argv0':sys.argv[0],'args':args,'cwd':os.getcwd(),'selected':os.environ.get('PYTHON')})+'\\n')
if args[:1]==['-c'] and 'sys.version_info' in args[1]:
 if BROKEN:sys.exit(3)
 sys.version_info=VERSION
 exec(args[1])
'''.replace('LABEL',repr(label)).replace('VERSION',repr(version)).replace('BROKEN',repr(broken)))
 path.chmod(0o755)

def fixture_run(tmp_path,mode,*,text=None,version=(3,12,0),broken=False):
 caller=tmp_path/'caller π';caller.mkdir();stage=tmp_path/'stage source';stage.mkdir();log=tmp_path/'calls.jsonl'
 relative=Path('bin/python3') if mode=='bare_path' else Path('bin/python shim');fake(caller/relative,'CALLER',version,broken);fake(stage/relative,'WRONG_STAGE')
 choice='./'+str(relative)
 selected=caller/relative
 if mode in ['absolute','symlink']:
  if mode=='symlink':
   link=caller/'venv prefix/bin/python';link.parent.mkdir(parents=True);link.symlink_to(selected);selected=link
  choice=str(selected)
 if mode=='relative_symlink':
  link=caller/'venv prefix/bin/python';link.parent.mkdir(parents=True);link.symlink_to(selected);selected=link;choice='./'+str(link.relative_to(caller));fake(stage/'venv prefix/bin/python','WRONG_STAGE')
 env=dict(os.environ,PYTHON=choice,STAGE=str(stage),LOCATOR_LOG=str(log),PYTHONDONTWRITEBYTECODE='1')
 if mode=='bare_path':env.pop('PYTHON',None);env['PATH']='bin:'+env['PATH']
 source=BUILDER.read_text() if text is None else text
 selection=locator(source) if '# BEGIN EXPORTER PYTHON LOCATOR' in source else 'PYTHON="${PYTHON:-python3}"\n'
 code='set -eu\n'+selection+'\n"$PYTHON" -c "import sys"\n'+stage_call(source)
 r=subprocess.run(['bash','-c',code],cwd=caller,env=env,capture_output=True,text=True,timeout=10)
 rows=[json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []
 (tmp_path/'receipt.json').write_text(json.dumps({'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'calls':rows},indent=2)+'\n')
 return r,rows,caller,stage,selected

@pytest.mark.parametrize('mode',['relative','bare_path','absolute','symlink','relative_symlink'])
def test_selected_executable_stays_pinned_across_actual_stage_call(tmp_path,mode):
 r,rows,caller,stage,selected=fixture_run(tmp_path,mode)
 assert r.returncode==0,r.stdout+r.stderr
 assert len(rows)==3 and all(x['label']=='CALLER' for x in rows)
 assert rows[-1]['cwd']==str(stage) and rows[-1]['args'][:2]==['-m','pytest']
 assert all(os.path.isabs(x['selected']) for x in rows)
 if 'symlink' in mode:assert all(os.path.normpath(x['argv0'])==str(selected) for x in rows)

@pytest.mark.parametrize('version,broken', [((3,11,9),False),((3,12,0),True)])
def test_incompatible_or_failed_runtime_refuses_before_stage_call(tmp_path,version,broken):
 r,rows,caller,stage,selected=fixture_run(tmp_path,'absolute',version=version,broken=broken)
 assert r.returncode==2 and 'EXPORT-PYTHON-002' in r.stderr and 'Python 3.12+' in r.stderr and 'before staging' in r.stderr
 assert len(rows)==1 and rows[0]['cwd']==str(caller)

@pytest.mark.parametrize('mode',['missing','command_string','directory','nonexecutable','function_shadow'])
def test_invalid_selection_has_typed_locator_diagnostic(tmp_path,mode):
 caller=tmp_path/'caller';caller.mkdir();chosen=caller/'python';prefix=''
 if mode=='command_string':choice='python3 -B'
 elif mode=='directory':chosen.mkdir();choice=str(chosen)
 elif mode=='nonexecutable':chosen.write_text('synthetic not executable');chosen.chmod(0o644);choice=str(chosen)
 elif mode=='function_shadow':
  fake(caller/'python3','MUST_NOT_RUN');choice='python3';prefix='python3(){ :; }\n'
 else:choice=str(chosen)
 env=dict(os.environ,PYTHON=choice,LOCATOR_LOG=str(tmp_path/'unexpected.jsonl'))
 code='set -eu\n'+prefix+locator(BUILDER.read_text())+'\necho UNREACHABLE_STAGING\n'
 r=subprocess.run(['bash','-c',code],cwd=caller,env=env,capture_output=True,text=True,timeout=10)
 assert r.returncode==2 and 'EXPORT-PYTHON-001' in r.stderr and 'set PYTHON' in r.stderr and 'UNREACHABLE_STAGING' not in r.stdout
 assert not (tmp_path/'unexpected.jsonl').exists()

def test_locator_is_before_source_preflight_and_staging():
 text=BUILDER.read_text();start=text.index('# BEGIN EXPORTER PYTHON LOCATOR');end=text.index('# END EXPORTER PYTHON LOCATOR')
 assert start<end<text.index('source "$SRC/tools/cut_preflight.sh"')<text.index('WORK="$(mktemp -d)"')
 block=locator(text);assert 'realpath' not in block and 'readlink' not in block


@pytest.mark.parametrize('response',['','unrecognized response'])
def test_zero_exit_nonpython_selection_cannot_pass_version_probe(tmp_path,response):
 selected=tmp_path/'not python';selected.write_text('#!/bin/sh\nprintf "%s\\n" '+repr(response)+'\nexit 0\n');selected.chmod(0o755)
 code='set -eu\n'+locator(BUILDER.read_text())+'\necho UNREACHABLE_STAGING\n'
 r=subprocess.run(['bash','-c',code],cwd=tmp_path,env=dict(os.environ,PYTHON=str(selected)),capture_output=True,text=True,timeout=10)
 assert r.returncode==2 and 'EXPORT-PYTHON-002' in r.stderr and 'UNREACHABLE_STAGING' not in r.stdout


@pytest.mark.skipif(sys.version_info < (3,12),reason='requires supported selected Python for real version-handshake control')
def test_real_supported_python_version_handshake_is_silent(tmp_path):
 r=subprocess.run(['bash','-c','set -eu\n'+locator(BUILDER.read_text())],cwd=tmp_path,env=dict(os.environ,PYTHON=sys.executable),capture_output=True,text=True,timeout=10)
 assert r.returncode==0 and r.stdout=='' and r.stderr==''
