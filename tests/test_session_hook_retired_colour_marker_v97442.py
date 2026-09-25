"""The shipped SessionStart hook must not tell a chat to use the shared colour marker.

`.claude/current_chat_color` is one value shared by every concurrent chat. Chats that
wrote and trusted it inherited each other's identity, so the rule was retired. Sibling
hooks (`block_subagent_spawn.py`, `session_cost_ledger.py`) already refuse to read it.
"""
import json
import os
import subprocess
from pathlib import Path

from tests.conftest import hermetic_env

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / 'hooks' / 'sapote_session_start.sh'


def _message(tmp_path):
    env = hermetic_env(PATH=os.environ['PATH'], SAPOTE_WORKSPACE_ROOT=tmp_path)
    proc = subprocess.run(['bash', str(HOOK)], env=env, text=True,
                          capture_output=True, check=True)
    return json.loads(proc.stdout)['hookSpecificOutput']['additionalContext']


def test_hook_never_tells_a_chat_to_write_the_shared_colour_marker(tmp_path):
    message = _message(tmp_path)
    assert 'COLOR-CHAT RULE' not in message
    assert 'write it to .claude/current_chat_color' not in message


def test_hook_binds_identity_to_the_session_id(tmp_path):
    message = _message(tmp_path)
    assert 'SESSION-ADDRESS RULE' in message
    assert 'Do NOT read or write .claude/current_chat_color' in message
