"""Audit F05: a heredoc no longer exempts the commands around it, and the sealed-tree guard checks NotebookEdit
targets and symlink aliases. Each deny case has an allow twin, so documentation that only mentions a command stays
allowed."""
import json
import os
import subprocess
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
SEALED = "sapote-mamey-v9.7.446-CODE-20261001v97446a"


def run(hook, tool, tool_input, cwd):
    payload = {"tool_name": tool, "tool_input": tool_input, "cwd": str(cwd), "session_id": "fixture",
               "hook_event_name": "PreToolUse"}
    r = subprocess.run(["bash", str(HOOKS / hook)], input=json.dumps(payload), capture_output=True, text=True,
                       cwd=cwd, env={**os.environ, "CLAUDE_PROJECT_DIR": str(cwd)})
    return r.returncode == 2 or '"deny"' in r.stdout


HEREDOC = "cat > notes.md <<'EOF'\nsome notes\nEOF\n"


def test_seal_runner_after_a_heredoc_is_denied(tmp_path):
    assert run("block_seal_commands.sh", "Bash", {"command": "bash tools/release_cut.sh"}, tmp_path)
    assert run("block_seal_commands.sh", "Bash", {"command": HEREDOC + "bash tools/release_cut.sh"}, tmp_path)
    assert run("block_seal_commands.sh", "Bash", {"command": "bash tools/release_cut.sh\n" + HEREDOC}, tmp_path)


def test_a_heredoc_that_only_mentions_the_seal_runner_is_allowed(tmp_path):
    doc = "cat > notes.md <<'EOF'\nNever run bash tools/release_cut.sh yourself.\nEOF\n"
    assert not run("block_seal_commands.sh", "Bash", {"command": doc}, tmp_path)
    assert not run("block_seal_commands.sh", "Bash", {"command": "grep -n release_cut.sh docs/*.md"}, tmp_path)


def test_dash_heredoc_with_indented_terminator_is_stripped(tmp_path):
    doc = "cat > n.md <<-EOF\n\tbash tools/release_cut.sh\n\tEOF\necho done"
    assert not run("block_seal_commands.sh", "Bash", {"command": doc}, tmp_path)


def test_release_folder_creation_after_a_heredoc_is_still_checked(tmp_path):
    plain = 'mkdir "Sapote Mamey v9.9.9"'
    if not run("block_top_level_release_folder.sh", "Bash", {"command": plain}, tmp_path):
        pytest.skip("this guard allows the plain form here; nothing to compare")
    assert run("block_top_level_release_folder.sh", "Bash", {"command": HEREDOC + plain}, tmp_path)


def test_notebook_edit_into_a_sealed_tree_is_denied():
    # The guard allows /tmp working copies, and pytest's tmp_path is under /tmp on Linux runners. The guard only
    # resolves the path and never touches the file, so the session cwd is the filesystem root: no temp directory.
    root = Path(os.path.abspath(os.sep))
    nb = {"notebook_path": f"{SEALED}/notebooks/x.ipynb", "new_source": "x"}
    assert run("block_sealed_tree_edits.sh", "NotebookEdit", nb, root)
    assert run("block_sealed_tree_edits.sh", "Edit", {"file_path": f"{SEALED}/mamey/cli.py"}, root)
    assert not run("block_sealed_tree_edits.sh", "NotebookEdit", {"notebook_path": "work/x.ipynb"}, root)


def test_a_symlink_alias_cannot_hide_a_sealed_destination(tmp_path):
    if "/tmp/" in str(tmp_path):
        pytest.skip("the guard deliberately allows /tmp working copies")
    real = tmp_path / SEALED
    real.mkdir()
    (tmp_path / "alias").symlink_to(real)
    assert run("block_sealed_tree_edits.sh", "Edit", {"file_path": str(tmp_path / "alias" / "a.py")}, tmp_path)
    assert not run("block_sealed_tree_edits.sh", "Edit", {"file_path": str(tmp_path / "work" / "a.py")}, tmp_path)
