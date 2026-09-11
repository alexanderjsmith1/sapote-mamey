"""BC2 .398 audit: hooks/session_cost_ledger.py::identify() carried the same broken
"sessions/<Name>/STATE.md" pattern already found and fixed at v97395 in the sibling
tools/session_cost_audit.py::identify() (see tests/test_session_cost_audit_identify_v97395.py)
and again in hooks/block_subagent_spawn.py::whoami() (see
tests/test_block_subagent_spawn_whoami_convention_bc2_398.py) -- the fix was never propagated
to this third sibling. session_cost_ledger.py is the Stop-hook that appends one row per session
to SAPOTE_CONTROL/SESSION_COST_LEDGER.tsv, whose entire stated purpose (per its own docstring)
is "so nobody ever has to guess again" which lane's tokens went where -- a ledger that
attributes every real session's row to chat="?" cannot answer that question.

Deliberately does NOT hardcode the project's real private-workspace parent-directory literal
anywhere in this file, matching the established discipline for this bug family.
"""
from __future__ import annotations

import json
import pathlib
import sys

HOOKS_DIR = pathlib.Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS_DIR))
import session_cost_ledger as scl  # noqa: E402


def _write_fake_transcript(path, file_path, n=5):
    rec = {
        "type": "assistant",
        "message": {"role": "assistant",
                     "usage": {"input_tokens": 1, "cache_creation_input_tokens": 0,
                               "cache_read_input_tokens": 1, "output_tokens": 1},
                     "content": [{"type": "tool_use", "name": "Edit",
                                  "input": {"file_path": file_path}}]},
    }
    with open(path, "w") as f:
        for _ in range(n):
            f.write(json.dumps(rec) + "\n")


def test_identify_recognizes_the_real_convention_regardless_of_parent_dir_name(tmp_path):
    p = tmp_path / "fake_session.jsonl"
    # synthetic parent name -- proves resolution keys on the STATE.md-owning directory's own
    # name, not a hardcoded parent literal.
    _write_fake_transcript(p, "/some/workspace_root/Sea Green/STATE.md")
    assert scl.identify(str(p)) == "Sea Green"


def test_identify_still_recognizes_legacy_sessions_convention(tmp_path):
    """No regression: the old sessions/<Name>/STATE.md shape still resolves."""
    p = tmp_path / "fake_legacy.jsonl"
    _write_fake_transcript(p, "/some/old/path/sessions/Aquarius/STATE.md")
    assert scl.identify(str(p)) == "Aquarius"


def test_identify_does_not_hardcode_a_workspace_specific_literal():
    src = (HOOKS_DIR / "session_cost_ledger.py").read_text(encoding="utf-8")
    assert "Color folders" not in src


def test_ledger_row_carries_real_identity_not_the_unknown_fallback(tmp_path, monkeypatch):
    """The consequential proof: a real session on the real convention must produce a ledger
    row attributable to its actual chat, not the '?' fallback."""
    root = tmp_path
    control_dir = root / "SAPOTE_CONTROL"
    monkeypatch.setattr(scl, "LEDGER", str(control_dir / "SESSION_COST_LEDGER.tsv"))

    transcript = root / "fake.jsonl"
    _write_fake_transcript(transcript, "/some/workspace_root/Sea Green/STATE.md", n=3)

    payload = json.dumps({"transcript_path": str(transcript), "session_id": "sea-green-uuid"})
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO(payload))
    scl.main()

    rows = (control_dir / "SESSION_COST_LEDGER.tsv").read_text().strip().splitlines()
    assert len(rows) == 2  # header + one data row
    chat_col = rows[1].split("\t")[2]
    assert chat_col == "Sea Green"
