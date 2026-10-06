"""Audit F03: advice from an advisory hook must reach someone. The Claude Code hooks reference says stderr from a hook
that exits 0 goes to the debug log only, plain PostToolUse stdout is not added to Claude's context, and the reason
attached to a PreToolUse "allow" goes to the debug log while the allow skips the permission prompt."""
import json
import os
import subprocess
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1] / "hooks"


def run(hook, payload, root):
    runner = ["python3"] if hook.endswith(".py") else ["bash"]
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(root), "SAPOTE_WORKSPACE_ROOT": str(root)}
    return subprocess.run(runner + [str(HOOKS / hook)], input=json.dumps(payload), capture_output=True, text=True,
                          cwd=root, env=env)


def transcript(tmp_path, text):
    t = tmp_path / "t.jsonl"
    t.write_text(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}) + "\n")
    return str(t)


def test_chat_link_check_holds_the_reply_once_then_notifies(tmp_path):
    payload = {"transcript_path": transcript(tmp_path, "See [the file](missing.md)."), "stop_hook_active": False}
    first = run("chat_link_check.py", payload, tmp_path)
    assert first.returncode == 2 and "MISSING: missing.md" in first.stderr  # exit 2: Claude gets the message
    payload["stop_hook_active"] = True
    again = run("chat_link_check.py", payload, tmp_path)
    assert again.returncode == 0 and "MISSING" in json.loads(again.stdout)["systemMessage"]  # no loop; user told


def test_chat_link_check_is_silent_on_good_links(tmp_path):
    (tmp_path / "ok.md").write_text("x")
    r = run("chat_link_check.py", {"transcript_path": transcript(tmp_path, "See [ok](ok.md)."),
                                   "stop_hook_active": False}, tmp_path)
    assert r.returncode == 0 and not r.stdout.strip() and not r.stderr.strip()


def test_docx_reminder_is_a_system_message(tmp_path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "deliverable_folders.txt").write_text("out\n")
    (tmp_path / "out").mkdir()
    (tmp_path / "out" / "report.md").write_text("x")
    r = run("deliverable_docx_warn.sh", {}, tmp_path)
    assert r.returncode == 0 and not r.stderr.strip()
    assert "out/report.md" in json.loads(r.stdout)["systemMessage"]


def test_staging_reminder_reaches_claude_as_additional_context(tmp_path):
    fp = str(tmp_path / ".claude" / "hooks" / "x.sh")
    r = run("bundle_staging_reminder.sh", {"tool_name": "Edit", "tool_input": {"file_path": fp}}, tmp_path)
    out = json.loads(r.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "PostToolUse" and "x.sh" in out["additionalContext"]


def test_tool_reminder_never_auto_approves(tmp_path):
    src = (HOOKS / "check_tools_before_building.py").read_text()
    assert '"permissionDecision": "allow"' not in src and '"additionalContext": reason' in src
