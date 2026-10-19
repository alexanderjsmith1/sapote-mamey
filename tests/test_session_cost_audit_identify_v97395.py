"""Regression test — v97395 tick 22 (corrected): session_cost_audit.py's identify() never
matches this project's real STATE.md write convention.

The original regex required the literal substring "sessions/" immediately before the color
name. This project's real, universal convention is a title-case-word(s) directory immediately
containing STATE.md, regardless of what its own parent directory is named — matching on the
parent-directory-name shape directly (not a specific hardcoded parent-of-parent literal) is both
more robust to a future rename of that parent directory AND avoids hardcoding any
workspace-specific path fragment into shipped source (see PATCH_CARD.md's correction note:
the first version of this fix hardcoded the actual private workspace directory name, which
tripped tools/public_release_audit.py's own banned-identity gate).
"""
import json
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import session_cost_audit as m


def _write_fake_transcript(path, file_path):
    rec = {
        "type": "assistant",
        "timestamp": "2026-08-31T20:00:00Z",
        "message": {
            "role": "assistant",
            "usage": {"input_tokens": 100, "cache_creation_input_tokens": 0,
                      "cache_read_input_tokens": 5000, "output_tokens": 50},
            "content": [
                {"type": "tool_use", "id": "tu_1", "name": "Edit",
                 "input": {"file_path": file_path}}
            ],
        },
    }
    path.write_text(json.dumps(rec) + "\n", encoding="utf-8")


def test_identify_recognizes_the_real_convention_regardless_of_parent_dir_name_v97395(tmp_path):
    p = tmp_path / "fake_session.jsonl"
    # A distinct invented parent proves the direct STATE owner supplies identity.
    _write_fake_transcript(
        p, "/home/user/some_workspace_root/Example Lane/STATE.md"
    )
    assert m.identify(str(p)) == "Example Lane"


def test_identify_still_recognizes_legacy_sessions_convention_v97395(tmp_path):
    """No regression: the old sessions/<Name>/STATE.md shape still resolves -- it's a special
    case of the same general pattern now, not a separately-maintained one."""
    p = tmp_path / "fake_legacy_session.jsonl"
    _write_fake_transcript(p, "/some/old/path/sessions/Example Lane/STATE.md")
    assert m.identify(str(p)) == "Example Lane"


def test_identify_uses_state_owner_with_distinct_and_misleading_parents_v97395(tmp_path):
    """The direct STATE owner determines identity; parent names cannot supply it.

    All transcript records here are fabricated; no real session payload is loaded.
    """
    for index, parent in enumerate(("arbitrary_parent", "Parent With Spaces", "sessions/Decoy Lane")):
        p = tmp_path / f"invented_{index}.jsonl"
        _write_fake_transcript(p, f"/invented/{parent}/Sea Green/STATE.md")
        assert m.identify(str(p)) == "Sea Green"
    p = tmp_path / "not_state.jsonl"
    _write_fake_transcript(p, "/invented/Decoy Lane/Sea Green/NOT_STATE.md")
    assert m.identify(str(p)) in (None, "?")

