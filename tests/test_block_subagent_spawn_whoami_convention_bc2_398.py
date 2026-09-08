"""BC2 .398 audit: hooks/block_subagent_spawn.py::whoami() (the identity resolver behind the
workhorse subagent-ban enforcement hook) used the same broken "sessions/<Name>/STATE.md"
pattern that tools/session_cost_audit.py::identify() was already fixed to drop, at v97395 tick
22 (see tests/test_session_cost_audit_identify_v97395.py) -- but the fix was never propagated
to this sibling, whose whole job is enforcing the standing "no subagents for workhorse lanes"
rule.

Deliberately does NOT hardcode the project's real private-workspace parent-directory literal
anywhere in this file (matching test_session_cost_audit_identify_v97395.py's own discipline) --
proves the fix matches on the STATE.md-owning directory's own name, not a specific parent.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

HOOKS_DIR = pathlib.Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS_DIR))
import block_subagent_spawn as bss  # noqa: E402


def _write_fake_transcript(path, file_path, n=5):
    rec = {
        "type": "assistant",
        "message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "Edit", "input": {"file_path": file_path}}
        ]},
    }
    with open(path, "w") as f:
        for _ in range(n):
            f.write(json.dumps(rec) + "\n")


def test_whoami_recognizes_the_real_convention_regardless_of_parent_dir_name(tmp_path):
    p = tmp_path / "fake_session.jsonl"
    # deliberately a synthetic parent name, not the project's real private folder name --
    # proves resolution keys on the STATE.md-owning directory's own name, not a hardcoded parent.
    _write_fake_transcript(p, "/some/workspace_root/Sea Green/STATE.md")
    assert bss.whoami(str(p), "sid-1") == "Sea Green"


def test_whoami_still_recognizes_legacy_sessions_convention(tmp_path):
    """No regression: the old sessions/<Name>/STATE.md shape still resolves."""
    p = tmp_path / "fake_legacy.jsonl"
    _write_fake_transcript(p, "/some/old/path/sessions/Aquarius/STATE.md")
    assert bss.whoami(str(p), "sid-1") == "Aquarius"


def test_whoami_does_not_hardcode_a_workspace_specific_literal():
    src = (HOOKS_DIR / "block_subagent_spawn.py").read_text(encoding="utf-8")
    assert "Color folders" not in src


def test_end_to_end_ban_actually_fires_for_a_real_convention_workhorse_transcript(tmp_path, monkeypatch):
    """The consequential proof: a workhorse-roster lane using the real, non-'sessions/'
    STATE.md convention must actually be DENIED a Task/Agent call, not silently allowed."""
    root = tmp_path
    hooks_dir = root / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True)
    control_dir = root / "SAPOTE_CONTROL"
    control_dir.mkdir()
    (control_dir / "MAINTENANCE_LANES.tsv").write_text("color\tnotes\nSea Green\tworkhorse\n")

    hook_src = (HOOKS_DIR / "block_subagent_spawn.py").read_text(encoding="utf-8")
    hook_path = hooks_dir / "block_subagent_spawn.py"
    hook_path.write_text(hook_src, encoding="utf-8")

    transcript = root / "fake.jsonl"
    _write_fake_transcript(transcript, "/some/workspace_root/Sea Green/STATE.md")

    payload = json.dumps({
        "tool_name": "Task", "session_id": "sea-green-uuid-xyz",
        "transcript_path": str(transcript),
        "tool_input": {"description": "delegate a BGC read", "subagent_type": "general-purpose"},
    })
    proc = subprocess.run([sys.executable, str(hook_path)], input=payload,
                           capture_output=True, text=True, cwd=str(root))
    assert proc.stdout.strip(), "expected a permissionDecision:deny payload for a workhorse lane"
    decision = json.loads(proc.stdout)
    assert decision["hookSpecificOutput"]["permissionDecision"] == "deny"
    reason = decision["hookSpecificOutput"]["permissionDecisionReason"]
    assert "Sea Green" in reason  # identity resolved correctly, not the "?" fallback
