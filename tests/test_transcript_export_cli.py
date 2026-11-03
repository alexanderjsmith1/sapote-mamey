import json, os, subprocess, sys
from pathlib import Path
import pytest

HOOK = Path(os.environ.get('SYNTHETIC_HOOK', Path(__file__).resolve().parents[1]/'hooks/save_transcript.py'))

def invoke(root, projects, session=None):
    env=os.environ.copy()
    for key in ('SAPOTE_CHAT_DIR','MAMEY_DATA_ROOT','CLAUDE_PROJECT_DIR'):
        env.pop(key,None)
    env.update(SAPOTE_ROOT=str(root), CLAUDE_PROJECTS_DIR=str(projects), PYTHONDONTWRITEBYTECODE='1')
    args=[sys.executable,'-B',str(HOOK),'--color','blue']
    if session: args+=['--session',session]
    return subprocess.run(args,env=env,text=True,capture_output=True,timeout=10)

def input_file(projects):
    projects.mkdir(); (projects/'sample.jsonl').write_text(json.dumps({'type':'user','message':{'role':'user','content':'example text'}})+'\n')

@pytest.mark.parametrize('explicit',[False,True])
def test_nonexistent_root_refuses_writes(tmp_path,explicit):
    root=tmp_path/'missing-root';projects=tmp_path/'projects';input_file(projects)
    p=invoke(root,projects,'sample' if explicit else None)
    assert p.returncode==1
    assert 'discovery failed' in p.stderr
    assert not root.exists()

def test_pinned_session_reaches_selected_destination(tmp_path):
    root=tmp_path/'root';projects=tmp_path/'projects';input_file(projects)
    chat=root/'chosen'/'blue';chat.mkdir(parents=True);(chat/'STATE.md').write_text('example');(chat/'.session_id').write_text('sample')
    p=invoke(root,projects)
    assert p.returncode==0,p.stderr
    assert '[pinned]' in p.stdout
    assert 'example text' in (chat/'TRANSCRIPTS'/'transcript_latest.md').read_text()
    assert not (root/'sessions').exists()

def test_two_chat_folders_refuse_export(tmp_path):
    root=tmp_path/'root';projects=tmp_path/'projects';input_file(projects)
    for folder in ('one','two'):
        chat=root/folder/'blue';chat.mkdir(parents=True);(chat/'STATE.md').write_text('example')
    p=invoke(root,projects)
    assert p.returncode==1 and 'ambiguous' in p.stderr
    assert not any(root.rglob('TRANSCRIPTS'))
