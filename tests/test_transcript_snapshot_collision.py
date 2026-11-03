import datetime,importlib.util,json,os,sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest

HOOK=Path(os.environ.get('SYNTHETIC_HOOK', Path(__file__).resolve().parents[1]/'hooks/save_transcript.py'))
def load():
 s=importlib.util.spec_from_file_location('snapshot_test',HOOK);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def test_same_minute_exports_preserve_both_snapshots(tmp_path,monkeypatch):
 m=load();root=tmp_path/'root';chat=root/'chosen'/'blue';chat.mkdir(parents=True);(chat/'STATE.md').write_text('example');projects=tmp_path/'projects';projects.mkdir();session=projects/'sample.jsonl'
 def payload(text):return json.dumps({'type':'user','message':{'role':'user','content':text}})+'\n'
 session.write_text(payload('first synthetic message'));monkeypatch.setattr(m,'ROOT',root);monkeypatch.setattr(m,'PROJECTS',projects);monkeypatch.delenv('SAPOTE_CHAT_DIR',raising=False);monkeypatch.setattr(sys,'argv',['save_transcript.py','--color','blue','--session','sample'])
 class Frozen(datetime.datetime):
  @classmethod
  def now(cls,tz=None):return cls(2026,1,2,3,4)
 monkeypatch.setattr(m.dt,'datetime',Frozen);assert m.main()==0;session.write_text(payload('second synthetic message'));assert m.main()==0
 out=chat/'TRANSCRIPTS';snaps=sorted(out.glob('transcript_sample_*.md'));assert len(snaps)==2
 assert 'first synthetic message' in snaps[0].read_text();assert 'second synthetic message' in snaps[1].read_text();assert 'second synthetic message' in (out/'transcript_latest.md').read_text()

def test_exclusive_creation_handles_concurrent_claims(tmp_path):
 m=load()
 with ThreadPoolExecutor(max_workers=8) as pool:
  paths=list(pool.map(lambda n:m._write_snapshot(tmp_path,'session','2026-01-02_0304',str(n)),range(20)))
 assert len(set(paths))==20 and {p.read_text() for p in paths}=={str(n) for n in range(20)}

def test_existing_snapshot_file_is_untouched(tmp_path):
 m=load();old=tmp_path/'transcript_session_2026-01-02_0304.md';old.write_text('preserved')
 p=m._write_snapshot(tmp_path,'session','2026-01-02_0304','new');assert old.read_text()=='preserved' and p!=old and p.read_text()=='new'

def test_existing_symlink_does_not_overwrite_target(tmp_path):
 m=load();out=tmp_path/'out';out.mkdir();target=tmp_path/'outside.md';target.write_text('protected')
 (out/'transcript_session_2026-01-02_0304.md').symlink_to(target)
 p=m._write_snapshot(out,'session','2026-01-02_0304','new')
 assert target.read_text()=='protected' and p.read_text()=='new'

def test_snapshot_failure_does_not_replace_latest(tmp_path,monkeypatch):
 m=load();root=tmp_path/'root';chat=root/'chosen'/'blue';out=chat/'TRANSCRIPTS';out.mkdir(parents=True);(chat/'STATE.md').write_text('example');latest=out/'transcript_latest.md';latest.write_text('prior latest')
 projects=tmp_path/'projects';projects.mkdir();(projects/'sample.jsonl').write_text('{}\n');monkeypatch.setattr(m,'ROOT',root);monkeypatch.setattr(m,'PROJECTS',projects);monkeypatch.delenv('SAPOTE_CHAT_DIR',raising=False);monkeypatch.setattr(sys,'argv',['save_transcript.py','--color','blue','--session','sample'])
 def fail(*_):raise OSError('synthetic snapshot write failure')
 monkeypatch.setattr(m,'_write_snapshot',fail)
 with pytest.raises(OSError):m.main()
 assert latest.read_text()=='prior latest'
