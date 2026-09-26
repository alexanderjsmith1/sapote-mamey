"""PostToolUse attribution must use the event session, never a shared color marker."""
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

HOOKS = Path(__file__).resolve().parents[1] / "hooks"


@pytest.mark.parametrize("session_id, expected", [
    ("session-actual-123", "session-actual-123"),
    ("bad\tactor\nrow", "unattributed"),
    (None, "unattributed"),
])
def test_provenance_ignores_cross_session_marker(tmp_path, session_id, expected):
    root = tmp_path / "workspace"
    hooks = root / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    shutil.copy2(HOOKS / "provenance_log.py", hooks / "provenance_log.py")
    shutil.copy2(HOOKS / "provenance_log.sh", hooks / "provenance_log.sh")
    (root / ".claude" / "current_chat_color").write_text("Other Chat\n")
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(root / "note.txt")}}
    if session_id is not None:
        payload["session_id"] = session_id
    env = os.environ.copy()
    env["SAPOTE_WORKSPACE_ROOT"] = str(root)
    result = subprocess.run(["bash", str(hooks / "provenance_log.sh")],
                            input=json.dumps(payload), text=True, capture_output=True,
                            env=env, timeout=20)
    assert result.returncode == 0
    rows = (root / "strain_data/_PROVENANCE/AUTO_FILE_LOG.tsv").read_text().splitlines()
    assert len(rows) == 2
    assert rows[0] == "timestamp\ttool\tpath\tchat"
    assert rows[1].split("\t")[-1] == expected
