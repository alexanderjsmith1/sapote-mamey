from pathlib import Path
import json,os,subprocess,sys
import pytest
HOOK=Path(__file__).resolve().parents[1]/"hooks/link_check.py"

def run(workspace,explicit):
 env=os.environ.copy();env.update(PYTHONDONTWRITEBYTECODE="1",SAPOTE_WORKSPACE_ROOT=str(workspace));env.pop("SAPOTE_DELIVERABLE_ROOT",None)
 if explicit is not None:env["SAPOTE_DELIVERABLE_ROOT"]=str(explicit)
 return subprocess.run([sys.executable,"-B",str(HOOK)],env=env,capture_output=True,text=True,timeout=30)

@pytest.mark.parametrize("kind",["index_missing","index_directory","root_missing"])
def test_selected_root_or_index_unavailable_is_visible(tmp_path,kind):
 workspace=tmp_path/"workspace";workspace.mkdir();selected=workspace/"selected"
 if kind!="root_missing":selected.mkdir()
 if kind=="index_directory":(selected/"WHERE_THINGS_LIVE.md").mkdir()
 q=run(workspace,selected);assert q.returncode==0
 assert "unavailable" in json.loads(q.stdout)["systemMessage"]

def test_selected_readable_index_stays_quiet(tmp_path):
 workspace=tmp_path/"workspace";workspace.mkdir();selected=workspace/"selected";selected.mkdir();(selected/"WHERE_THINGS_LIVE.md").write_text("# synthetic\n")
 q=run(workspace,selected);assert q.returncode==0 and not q.stdout and not q.stderr

def test_no_configured_root_stays_quiet(tmp_path):
 workspace=tmp_path/"workspace";workspace.mkdir();q=run(workspace,None);assert q.returncode==0 and not q.stdout and not q.stderr
