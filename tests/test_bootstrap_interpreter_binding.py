import os,json,subprocess,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]

def shim(path,label):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text("#!"+sys.executable+"\nimport os,sys,json\nwith open(os.environ['SHIM_LOG'],'a') as log: log.write(json.dumps({'label':"+repr(label)+",'argv0':sys.argv[0],'args':sys.argv[1:]})+'\\n')\nif sys.argv[1:]==['--version']:print('Python 3.13.13')\n")
    path.chmod(0o755)

@pytest.mark.parametrize("selection",["relative","relative_path","symlink"])
def test_one_interpreter_stays_pinned_after_source_cd(tmp_path,selection):
    source=tmp_path/"selected source";source.mkdir()
    (source/"bootstrap.sh").write_bytes((ROOT/"bootstrap.sh").read_bytes())
    caller=tmp_path/"caller π";caller.mkdir()
    log=tmp_path/"calls.jsonl"
    if selection=="relative_path":
        relative=Path("bin/python3")
    else:relative=Path("bin/python shim")
    shim(caller/relative,"CALLER");shim(source/relative,"WRONG_SOURCE")
    selected=caller/relative
    if selection=="symlink":
        link=caller/"venv symlink/bin/python";link.parent.mkdir(parents=True);link.symlink_to(selected);selected=link
    env=dict(os.environ,SHIM_LOG=str(log))
    if selection=="relative_path":env.pop("PYTHON",None);env["PATH"]="bin:"+env['PATH']
    else:env['PYTHON']="./"+str(selected.relative_to(caller))
    result=subprocess.run(["bash",str(source/"bootstrap.sh")],cwd=caller,env=env,capture_output=True,text=True,timeout=15)
    assert result.returncode==0,result.stdout+result.stderr
    rows=[json.loads(line) for line in log.read_text().splitlines()]
    assert rows and all(row['label']=='CALLER' for row in rows)
    if selection=="symlink":assert all(os.path.normpath(row['argv0'])==str(selected) for row in rows)

def test_missing_selected_interpreter_has_locator_diagnostic(tmp_path):
    env=dict(os.environ,PYTHON=str(tmp_path/'missing python'))
    result=subprocess.run(["bash",str(ROOT/'bootstrap.sh')],cwd=tmp_path,env=env,capture_output=True,text=True,timeout=15)
    assert result.returncode==2
    assert "selected Python executable not found" in result.stderr
