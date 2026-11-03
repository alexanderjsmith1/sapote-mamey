import importlib.util,io,json,os,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("selected_session_hook",ROOT/"hooks/session_cost_ledger.py");tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)
VALID=json.dumps({"message":{"role":"assistant","usage":{"input_tokens":7,"output_tokens":3},"content":[]}}).encode()+b"\n"

def invoke(tmp_path,monkeypatch,capsys,data):
 transcript=tmp_path/"input.jsonl";transcript.write_bytes(data);ledger=tmp_path/"ledger.tsv";ledger.write_bytes(b"preserve existing\n");before=ledger.read_bytes();monkeypatch.setattr(tool,"LEDGER",str(ledger));monkeypatch.setattr(sys,"stdin",io.StringIO(json.dumps({"transcript_path":str(transcript),"session_id":"synthetic"})));rc=tool.main();streams=capsys.readouterr();assert rc==0 and transcript.read_bytes()==data;return ledger,before,streams

@pytest.mark.parametrize("bad",[b"not json SECRET_SENTINEL\n",b'{"message":"SECRET_SENTINEL_\xff"}\n',b'{"note":"SECRET_SENTINEL_\xff"}\n',b'["SECRET_SENTINEL"]\n'])
def test_partial_or_undecodable_records_do_not_append(tmp_path,monkeypatch,capsys,bad):
 ledger,before,streams=invoke(tmp_path,monkeypatch,capsys,VALID+bad)
 assert ledger.read_bytes()==before and "SESSION_COST_HOLD" in streams.err
 assert "SECRET_SENTINEL" not in streams.err and streams.out==""

def test_valid_records_still_append_correct_total(tmp_path,monkeypatch,capsys):
 ledger,before,streams=invoke(tmp_path,monkeypatch,capsys,VALID+b"\n")
 row=ledger.read_text().splitlines()[-1].split("\t");assert row[3]=="10" and row[7]=="1"
 assert streams.err=="" and streams.out==""

def test_missing_transcript_is_nonblocking_but_reported(tmp_path,monkeypatch,capsys):
 ledger=tmp_path/"ledger.tsv";monkeypatch.setattr(tool,"LEDGER",str(ledger));monkeypatch.setattr(sys,"stdin",io.StringIO(json.dumps({"transcript_path":str(tmp_path/"missing.jsonl")})))
 assert tool.main()==0;streams=capsys.readouterr();assert "SESSION_COST_HOLD" in streams.err and not ledger.exists()

def test_unspecified_transcript_remains_quiet(tmp_path,monkeypatch,capsys):
 monkeypatch.setattr(sys,"stdin",io.StringIO("{}"));assert tool.main()==0
 assert capsys.readouterr().err==""


def test_noninstalled_hook_subprocess_retains_ledger_on_partial_transcript(tmp_path):
 import shutil,subprocess
 hook=tmp_path/".claude/hooks/session_cost_ledger.py";hook.parent.mkdir(parents=True);shutil.copyfile(ROOT/"hooks/session_cost_ledger.py",hook)
 transcript=tmp_path/"input.jsonl";transcript.write_bytes(VALID+b"not json SECRET_SENTINEL\n")
 ledger=tmp_path/"SAPOTE_CONTROL/SESSION_COST_LEDGER.tsv";ledger.parent.mkdir();ledger.write_bytes(b"preserve existing\n")
 env=os.environ.copy();env["PYTHONDONTWRITEBYTECODE"]="1"
 q=subprocess.run([sys.executable,"-B",str(hook)],input=json.dumps({"transcript_path":str(transcript)}),env=env,capture_output=True,text=True,timeout=30)
 assert q.returncode==0 and ledger.read_bytes()==b"preserve existing\n"
 assert "SESSION_COST_HOLD" in q.stderr and "SECRET_SENTINEL" not in q.stderr and q.stdout==""
