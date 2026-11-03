"""The Stop hook saves a transcript with the bundled save_transcript.py, and says so when it cannot."""
import json
import os
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "save_transcript_stop.sh"
SID = "00000000-0000-4000-8000-000000000001"


def _run(tmp_path, with_jsonl=True):
    ws = tmp_path / "ws"
    (ws / "sessions" / "Synthetic").mkdir(parents=True)
    (ws / "sessions" / "Synthetic" / ".session_id").write_text(SID)
    projects = tmp_path / "projects"
    projects.mkdir()
    if with_jsonl:
        lines = [{"type": "user", "message": {"role": "user", "content": "synthetic question"}},
                 {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "synthetic answer"}]}}]
        (projects / f"{SID}.jsonl").write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    env = dict(os.environ, SAPOTE_WORKSPACE_ROOT=str(ws), CLAUDE_PROJECTS_DIR=str(projects))
    env.pop("SAPOTE_CHAT_DIR", None)
    r = subprocess.run(["bash", str(HOOK)], input=json.dumps({"session_id": SID}),
                       capture_output=True, text=True, env=env)
    return r, ws / "sessions" / "Synthetic" / "TRANSCRIPTS" / "transcript_latest.md"


def test_pinned_session_gets_a_transcript(tmp_path):
    r, latest = _run(tmp_path)
    assert r.returncode == 0, r.stderr
    assert latest.is_file()
    assert "synthetic question" in latest.read_text()


def test_failure_is_reported_not_silent(tmp_path):
    r, latest = _run(tmp_path, with_jsonl=False)
    assert r.returncode == 0
    assert not latest.exists()
    assert "transcript not saved" in r.stderr
