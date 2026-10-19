"""New fabricated shell controls: never install or launch scientific tools."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(os.environ.get('DIAGNOSTIC_SOURCE', str(Path(__file__).resolve().parents[1])))

def executable(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('#!'+sys.executable+'\n'+body)
    path.chmod(0o700)

def bootstrap(tmp_path, scenario):
    selected=tmp_path/'runtime with spaces/bin/python'
    log=tmp_path/'python_calls.jsonl'
    executable(selected, '''import json, os, sys
args=sys.argv[1:]
with open(os.environ['MOCK_CALLS'],'a') as f: f.write(json.dumps(args)+'\\n')
if args==['--version']: print('Python 3.13.13')
elif args[:1]==['-c']:
    if os.environ['MOCK_SCENARIO']=='old_python': raise SystemExit(2)
elif args[:3]==['-m','pip','--version']:
    if os.environ['MOCK_SCENARIO']=='missing_pip':
        print('No module named pip',file=sys.stderr); raise SystemExit(1)
    if os.environ['MOCK_SCENARIO']=='broken_pip':
        print('ImportError: fabricated incompatible extension',file=sys.stderr); raise SystemExit(1)
elif args[:3]==['-m','pip','install'] or args[:4]==['-m','pip','--isolated','install']:
    if os.environ['MOCK_SCENARIO'] in ('missing_pip','broken_pip'):
        print('No module named pip',file=sys.stderr); raise SystemExit(1)
''')
    env=dict(os.environ, PYTHON=str(selected), MOCK_CALLS=str(log), MOCK_SCENARIO=scenario)
    result=subprocess.run(['/bin/bash',str(ROOT/'bootstrap.sh')],cwd=tmp_path,env=env,
                          capture_output=True,text=True,timeout=10)
    calls=[json.loads(x) for x in log.read_text().splitlines()]
    return result,calls

@pytest.mark.parametrize('scenario',['missing_pip','broken_pip'])
def test_unusable_pip_is_a_preinstallation_runtime_hold(tmp_path,scenario):
    result,calls=bootstrap(tmp_path,scenario)
    assert result.returncode==2, result.stdout+result.stderr
    assert 'pip is unavailable or cannot start in selected Python' in result.stderr
    assert 'No package installation was attempted' in result.stderr
    assert not any('install' in a for a in calls)
    assert not any(a[:2]==['-m','pytest'] for a in calls)

def test_old_python_still_refuses_before_any_pip_command(tmp_path):
    result,calls=bootstrap(tmp_path,'old_python')
    assert result.returncode==2
    assert 'Python 3.12+ required' in result.stderr
    assert not any(a[:2]==['-m','pip'] for a in calls)

def test_compatible_mock_runtime_retains_bootstrap_success_scope(tmp_path):
    result,calls=bootstrap(tmp_path,'compatible')
    assert result.returncode==0,result.stdout+result.stderr
    assert 'bootstrap done: ALL_EXTRAS' in result.stdout
    assert any('install' in a for a in calls)
    assert any(a[:2]==['-m','pytest'] for a in calls)

def tree_runtime(tmp_path):
    caller=tmp_path/'caller with spaces';caller.mkdir()
    runtime=caller/'runtime with spaces'
    for name in ['GToTree','muscle','prodigal','hmmsearch','iqtree']:
        executable(runtime/'bin'/name, '''import os, sys
if sys.argv[1:]==['-v']:
    print('GToTree v1.8.19')
    raise SystemExit(int(os.environ.get('MOCK_VERSION_EXIT','0')))
''')
    hmm=runtime/'share/gtotree/hmm_sets';hmm.mkdir(parents=True)
    (hmm/'Actinobacteria.hmm').write_text('SELF_AUTHORED_NOT_A_MODEL\n')
    return caller,runtime

def tree_env(tmp_path, *, relative=False, version_exit=0, change_directory=False):
    caller,runtime=tree_runtime(tmp_path)
    after=tmp_path/'other cwd';after.mkdir()
    env=dict(os.environ,PHYLO_ENV='runtime with spaces' if relative else str(runtime),
             PROJECT_ROOT='.' if relative else str(caller),
             GTOTREE_HOME='missing standalone' if relative else str(caller/'missing standalone'),
             GTOTREE_GTDB_DIR='gtdb' if relative else str(caller/'gtdb'),
             GTOTREE_HMM_SETS='runtime with spaces/share/gtotree/hmm_sets' if relative else str(runtime/'share/gtotree/hmm_sets'),
             Pfam_data_dir='pfam' if relative else str(caller/'pfam'),
             MAMEY_DATA_ROOT='data' if relative else str(caller/'data'),
             MOCK_VERSION_EXIT=str(version_exit),ENV_SCRIPT=str(ROOT/'tools/gtotree_env.sh'),
             AFTER_CWD=str(after),PATH='/usr/bin:/bin')
    command='source "$ENV_SCRIPT"\n'
    if change_directory:command+='cd "$AFTER_CWD"\n'
    command+='gtotree_preflight\nresult=$?\nprintf "BOUND:%s\\n" "$PHYLO_ENV" "$GTOTREE_HMM_SETS" "$PROJECT_ROOT" "$MAMEY_DATA_ROOT" "$Pfam_data_dir"\nexit "$result"\n'
    result=subprocess.run(['/bin/bash','-c',command],cwd=caller,env=env,capture_output=True,text=True,timeout=10)
    return result,caller,runtime

def test_failed_version_probe_cannot_report_preflight_ok(tmp_path):
    result,_,_=tree_env(tmp_path,version_exit=7)
    assert result.returncode==1,result.stdout+result.stderr
    assert 'GToTree version probe failed (exit 7)' in result.stderr
    assert 'gtotree_preflight OK' not in result.stdout

def test_successful_version_probe_keeps_existing_environment_check(tmp_path):
    result,_,_=tree_env(tmp_path)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'gtotree_preflight OK' in result.stdout

def test_relative_runtime_overrides_survive_later_cd(tmp_path):
    result,caller,runtime=tree_env(tmp_path,relative=True,change_directory=True)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'BOUND:'+str(runtime) in result.stdout
    assert 'BOUND:'+str(caller/'data') in result.stdout
    assert 'BOUND:'+str(caller/'pfam') in result.stdout

def test_absolute_overrides_still_survive_later_cd(tmp_path):
    result,_,runtime=tree_env(tmp_path,change_directory=True)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'BOUND:'+str(runtime) in result.stdout

def test_relative_symlink_parent_traversal_keeps_os_selected_runtime(tmp_path):
    caller=tmp_path/'caller';caller.mkdir()
    physical=tmp_path/'physical';(physical/'deep').mkdir(parents=True)
    (caller/'jump').symlink_to(physical/'deep',target_is_directory=True)
    executable(physical/'runtime/bin/GToTree',"print('SELF_AUTHORED_OS_SELECTED_RUNTIME')\n")
    executable(caller/'runtime/bin/GToTree',"print('WRONG_LEXICALLY_COLLAPSED_RUNTIME')\n")
    after=tmp_path/'later';after.mkdir()
    env=dict(os.environ,PHYLO_ENV='jump/../runtime',PROJECT_ROOT=str(caller),
             GTOTREE_HOME=str(caller/'missing'),ENV_SCRIPT=str(ROOT/'tools/gtotree_env.sh'),
             AFTER_CWD=str(after),MAMEY_DATA_ROOT=str(caller/'missing-data'),PATH='/usr/bin:/bin')
    result=subprocess.run(['/bin/bash','-c','source "$ENV_SCRIPT"; cd "$AFTER_CWD"; GToTree'],
                          cwd=caller,env=env,capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stdout+result.stderr
    assert result.stdout.strip()=='SELF_AUTHORED_OS_SELECTED_RUNTIME'

def test_unset_optional_overrides_are_compatible_with_nounset(tmp_path):
    env=dict(os.environ,PROJECT_ROOT=str(tmp_path),PHYLO_ENV=str(tmp_path/'missing-env'),
             GTOTREE_HOME=str(tmp_path/'missing-home'),ENV_SCRIPT=str(ROOT/'tools/gtotree_env.sh'))
    for key in ['MAMEY_DATA_ROOT','Pfam_data_dir','GTOTREE_HMM_SETS','GTOTREE_GTDB_DIR']:
        env.pop(key,None)
    result=subprocess.run(['/bin/bash','-u','-c','source "$ENV_SCRIPT"; printf "%s" "$Pfam_data_dir"'],
                          cwd=tmp_path,env=env,capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stdout+result.stderr
    assert result.stdout==str(tmp_path/'gtotree_pfam')+'/'
