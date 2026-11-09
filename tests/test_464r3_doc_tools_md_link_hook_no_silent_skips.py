"""Synthetic Markdown only: every path where the hook checks nothing says so."""
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "md_link_check.sh"


def _bundle(tmp_path, checker_text=None, with_checker=True):
    b = tmp_path / "bundle"
    (b / "hooks").mkdir(parents=True)
    (b / "tools").mkdir()
    shutil.copy(HOOK, b / "hooks" / "md_link_check.sh")
    if with_checker:
        if checker_text is None:
            shutil.copy(ROOT / "tools" / "check_md_links.py", b / "tools" / "check_md_links.py")
        else:
            (b / "tools" / "check_md_links.py").write_text(checker_text)
    ws = tmp_path / "ws"
    ws.mkdir()
    return b, ws


def _run(bundle, ws, md):
    env = dict(os.environ, SAPOTE_WORKSPACE_ROOT=str(ws))
    return subprocess.run(["bash", str(bundle / "hooks" / "md_link_check.sh")],
                          input=json.dumps({"tool_input": {"file_path": str(md)}}),
                          capture_output=True, text=True, env=env)


def test_missing_markdown_file_is_reported(tmp_path):
    b, ws = _bundle(tmp_path)
    proc = _run(b, ws, ws / "absent.md")
    assert proc.returncode == 2 and "NOT checked" in proc.stderr


def test_missing_checker_is_reported(tmp_path):
    b, ws = _bundle(tmp_path, with_checker=False)
    md = ws / "note.md"
    md.write_text("[x](missing.md)\n")
    proc = _run(b, ws, md)
    assert proc.returncode == 2 and "NOT checked" in proc.stderr


def test_silent_exit_one_is_reported(tmp_path):
    b, ws = _bundle(tmp_path, "import sys\nsys.exit(1)\n")
    md = ws / "note.md"
    md.write_text("text\n")
    proc = _run(b, ws, md)
    assert proc.returncode == 2 and "NOT checked" in proc.stderr


def test_clean_file_stays_silent(tmp_path):
    b, ws = _bundle(tmp_path)
    md = ws / "note.md"
    md.write_text("no links here\n")
    proc = _run(b, ws, md)
    assert proc.returncode == 0 and proc.stderr == ""
