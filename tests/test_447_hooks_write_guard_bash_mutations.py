"""Audit F04: the Bash branch of block_out_of_bounds_writes.py recognises deletions, moves from outside, `dd of=`,
`cp -t`, and a `cd` earlier in the command. Every deny case has in-project twins that stay allowed. Nothing in a
payload is executed; the outside path is never created."""
import json
import os
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "hooks" / "block_out_of_bounds_writes.py"
OUT = "/opt/sapote_fixture_outside"   # outside every allowed root; only named in payloads


def denied(cmd, project):
    payload = {"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": str(project), "session_id": "fixture",
               "hook_event_name": "PreToolUse"}
    env = {k: v for k, v in os.environ.items() if k != "SAPOTE_WORKSPACE_ROOT"}
    env["CLAUDE_PROJECT_DIR"] = str(project)
    r = subprocess.run(["python3", str(HOOK)], input=json.dumps(payload), capture_output=True, text=True, env=env)
    return '"deny"' in r.stdout


@pytest.fixture
def project(tmp_path):
    p = tmp_path / "project"
    (p / "sub").mkdir(parents=True)
    return p


@pytest.mark.parametrize("cmd", [
    f"touch {OUT}/a.txt",
    f"rm {OUT}/a.txt",
    f"rm -rf {OUT}",
    f"dd if=/dev/zero of={OUT}/a.bin count=0",
    f"cd {OUT} && touch a.txt",
    f"cd {OUT}; echo x > a.txt",
    f"cp -t {OUT} ./a.txt",
    f"cp --target-directory={OUT} ./a.txt",
    f"mv {OUT}/a.txt ./a.txt",
    f"nice -n 15 touch {OUT}/a.txt",
    f"cat > notes.md <<'EOF'\nsome text\nEOF\ntouch {OUT}/a.txt",
])
def test_writes_outside_the_project_are_denied(cmd, project):
    assert denied(cmd, project)


@pytest.mark.parametrize("cmd", [
    "rm -f sub/a.txt",
    "cd sub && touch a.txt",
    "mv sub/a.txt sub/b.txt",
    "cp -t sub ./a.txt",
    "dd if=/dev/zero of=sub/a.bin count=0",
    "python3 x.py > out.txt 2>/dev/null",
    "FOO=1 nice -n 15 python3 x.py > sub/log.txt",
    f"ls {OUT}",
    f"cat > notes.md <<'EOF'\nnever touch {OUT}/a.txt\nEOF",
    f"cd {OUT} && ls",
    "cd - && echo hi",
])
def test_in_project_writes_and_reads_stay_allowed(cmd, project):
    assert not denied(cmd, project)
