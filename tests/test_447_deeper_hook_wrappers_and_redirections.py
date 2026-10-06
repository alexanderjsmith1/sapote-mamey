"""Static hook payloads only: never run a command under review."""
import json,os,subprocess
from pathlib import Path
import pytest
ROOT=Path(os.environ.get('SAPOTE_DEEP_TARGET',str(Path(__file__).resolve().parents[1])))
OUT='/opt/sapote_deep_outside'

def denied(command, project, cwd=None):
 p=subprocess.run(['python3',str(ROOT/'hooks/block_out_of_bounds_writes.py')],
  input=json.dumps({'tool_name':'Bash','cwd':cwd or str(project),'tool_input':{'command':command}}),
  text=True,capture_output=True,env={**os.environ,'SAPOTE_WORKSPACE_ROOT':str(project),'CLAUDE_PROJECT_DIR':str(project)})
 assert p.returncode==0,p.stderr
 return bool(p.stdout.strip()) and json.loads(p.stdout)['hookSpecificOutput']['permissionDecision']=='deny'

@pytest.mark.parametrize('prefix', ['sudo -n','sudo -Hn','sudo -u root -n','sudo --non-interactive','sudo -n MODE=test','env -','env --','nice -n 5','nohup','exec'])
def test_wrapper_preserves_outside_write(prefix,tmp_path):
 assert denied(prefix+' touch '+OUT+'/file',tmp_path)

@pytest.mark.parametrize('prefix',['env -C '+OUT,'env -C'+OUT,'env --chdir '+OUT,'env --chdir='+OUT,'sudo -D '+OUT,'sudo --chdir='+OUT,'env -C '+OUT+' nice -n 5'])
def test_wrapper_directory_applies_to_operand(prefix,tmp_path):
 assert denied(prefix+' touch file',tmp_path)

@pytest.mark.parametrize('command',['printf hello 2>&1','printf hello >&2','cat 3<&0','printf hello 2>&-','printf hello 2>&1-','FD=1; printf hello 2>&"$FD"','printf hello &>>local.log','cat <>local.txt'])
def test_legitimate_descriptor_and_file_forms(command,tmp_path):
 assert not denied(command,tmp_path)

@pytest.mark.parametrize('command',['echo hello >123','echo hello >>123','echo hello >|123','cat <>123','touch 123 > /dev/null','touch -- -filename'])
def test_numeric_and_dash_filenames_are_targets(command,tmp_path):
 assert denied(command,tmp_path,cwd=OUT)

@pytest.mark.parametrize('command',['command -v touch '+OUT,'command -V touch '+OUT,'command -pv touch '+OUT])
def test_command_lookup_is_read_only(command,tmp_path):
 assert not denied(command,tmp_path)

@pytest.mark.parametrize('command',['echo x >&'+OUT+'/file','echo x &>>'+OUT+'/file','cat <>'+OUT+'/file','command -v touch >'+OUT+'/log'])
def test_redirection_remains_checked(tmp_path,command):
 assert denied(command,tmp_path)

def test_wrapper_cwd_does_not_escape_to_next_segment(tmp_path):
 assert not denied('env -C '+OUT+' ls; touch local.txt',tmp_path)

def test_wrapper_cwd_does_not_change_shell_redirection(tmp_path):
 assert not denied('env -C '+OUT+' ls > local.txt',tmp_path)
 assert denied('env -C '+str(tmp_path)+' ls > file',tmp_path,cwd=OUT)

@pytest.mark.parametrize('prefix',['sudo -n','sudo -Hn','sudo -u root -n','env -','nice -n 5','exec'])
def test_local_write_wrapper_controls(prefix,tmp_path):
 assert not denied(prefix+' touch local.txt',tmp_path)
