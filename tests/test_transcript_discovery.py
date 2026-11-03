import importlib.util
from pathlib import Path
import os
import pytest

PATH = Path(os.environ.get('SYNTHETIC_HOOK', Path(__file__).resolve().parents[1] / 'hooks/save_transcript.py'))

def load():
    spec = importlib.util.spec_from_file_location('transcript_discovery_test', PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def test_failure_refuses_fallback_and_reports(tmp_path, monkeypatch, capsys):
    m = load()
    monkeypatch.delenv('SAPOTE_CHAT_DIR', raising=False)
    def fail(_): raise PermissionError('private diagnostic')
    monkeypatch.setattr(Path, 'iterdir', fail)
    assert m.chat_dir(tmp_path, 'blue') is None
    warning = capsys.readouterr().err
    assert 'discovery failed' in warning and 'private diagnostic' not in warning

def test_successful_empty_discovery_keeps_default(tmp_path, monkeypatch):
    m = load(); monkeypatch.delenv('SAPOTE_CHAT_DIR', raising=False)
    assert m.chat_dir(tmp_path, 'blue') == tmp_path / 'sessions'

def test_unique_discovery_and_explicit_override(tmp_path, monkeypatch):
    m = load(); monkeypatch.delenv('SAPOTE_CHAT_DIR', raising=False)
    (tmp_path/'actual'/'blue').mkdir(parents=True)
    (tmp_path/'actual'/'blue'/'STATE.md').write_text('synthetic')
    assert m.chat_dir(tmp_path, 'blue') == tmp_path/'actual'
    monkeypatch.setenv('SAPOTE_CHAT_DIR', 'chosen')
    assert m.chat_dir(tmp_path, 'blue') == tmp_path/'chosen'

def test_ambiguous_discovery_remains_refused(tmp_path, monkeypatch):
    m=load(); monkeypatch.delenv('SAPOTE_CHAT_DIR', raising=False)
    for name in ('one','two'):
        (tmp_path/name/'blue').mkdir(parents=True)
        (tmp_path/name/'blue'/'STATE.md').write_text('synthetic')
    assert m.chat_dir(tmp_path,'blue') is None

@pytest.mark.parametrize('explicit', [False, True])
def test_main_refuses_without_render_or_write(tmp_path, monkeypatch, capsys, explicit):
    import sys
    m=load(); monkeypatch.setattr(m, 'ROOT', tmp_path)
    monkeypatch.setattr(m, 'PROJECTS', tmp_path/'projects')
    (tmp_path/'projects').mkdir(); (tmp_path/'projects'/'sample.jsonl').write_text('{}\n')
    monkeypatch.setattr(m, 'chat_dir', lambda *_: None)
    monkeypatch.setattr(m, 'render', lambda *_: pytest.fail('must not render'))
    monkeypatch.setattr(sys, 'argv', ['save_transcript.py'] + (['--session','sample'] if explicit else []))
    assert m.main() == 1
    assert not (tmp_path/'sessions').exists()

def test_partial_discovery_refuses_if_one_entry_cannot_be_checked(tmp_path, monkeypatch):
    m=load(); monkeypatch.delenv('SAPOTE_CHAT_DIR', raising=False)
    for name in ('one','two'):
        (tmp_path/name/'blue').mkdir(parents=True)
        (tmp_path/name/'blue'/'STATE.md').write_text('synthetic')
    original=Path.stat
    def intermittent(self, *args, **kwargs):
        if self == tmp_path/'two'/'blue'/'STATE.md': raise PermissionError('hidden')
        return original(self,*args,**kwargs)
    monkeypatch.setattr(Path,'stat',intermittent)
    assert m.chat_dir(tmp_path,'blue') is None

def test_main_binds_session_and_output_to_one_discovery(tmp_path, monkeypatch):
    import json,sys
    m=load(); monkeypatch.setattr(m,'ROOT',tmp_path); projects=tmp_path/'projects';projects.mkdir();monkeypatch.setattr(m,'PROJECTS',projects)
    first=tmp_path/'first';second=tmp_path/'second'
    for folder in (first,second): (folder/'blue').mkdir(parents=True)
    (first/'blue'/'.session_id').write_text('synthetic')
    (projects/'synthetic.jsonl').write_text(json.dumps({'type':'user','message':{'role':'user','content':'synthetic sample'}})+'\n')
    answers=iter((first,second)); calls=[]
    def changing(*_):
        result=next(answers);calls.append(result);return result
    monkeypatch.setattr(m,'chat_dir',changing);monkeypatch.setattr(sys,'argv',['save_transcript.py','--color','blue'])
    assert m.main()==0
    assert calls==[first]
    assert (first/'blue'/'TRANSCRIPTS'/'transcript_latest.md').is_file()
    assert not (second/'blue'/'TRANSCRIPTS').exists()
