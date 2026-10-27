"""hooks/md_link_check.sh checks links even without a workspace Tools/ copy, and reports a crashed checker.

The hook looked only for <root>/Tools/check_md_links.py and exited 0 when it was absent, and it
judged captured stdout only, so a checker crash also looked clean. Absence of a warning did not
mean the links were checked.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "md_link_check.sh"


def _run(bundle, ws, md):
    env = dict(os.environ, SAPOTE_WORKSPACE_ROOT=str(ws))
    payload = json.dumps({"tool_input": {"file_path": str(md)}})
    return subprocess.run(["bash", str(bundle / "hooks" / "md_link_check.sh")], input=payload,
                          capture_output=True, text=True, env=env)


def _bundle(tmp_path, checker_text=None):
    b = tmp_path / "bundle"
    (b / "hooks").mkdir(parents=True)
    (b / "tools").mkdir()
    shutil.copy(HOOK, b / "hooks" / "md_link_check.sh")
    if checker_text is None:
        shutil.copy(ROOT / "tools" / "check_md_links.py", b / "tools" / "check_md_links.py")
    else:
        (b / "tools" / "check_md_links.py").write_text(checker_text)
    return b


def test_bundle_checker_is_used_without_workspace_tools(tmp_path):
    b = _bundle(tmp_path)
    ws = tmp_path / "ws"
    ws.mkdir()
    md = ws / "note.md"
    md.write_text("[x](missing_file.md)\n")
    proc = _run(b, ws, md)
    assert proc.returncode == 2 and "MD-LINK" in proc.stderr


def test_crashed_checker_is_reported(tmp_path):
    b = _bundle(tmp_path, "import sys\nsys.exit(3)\n")
    ws = tmp_path / "ws"
    ws.mkdir()
    md = ws / "note.md"
    md.write_text("# fine\n")
    proc = _run(b, ws, md)
    assert proc.returncode == 2 and "NOT checked" in proc.stderr


def test_clean_page_stays_quiet(tmp_path):
    b = _bundle(tmp_path)
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "other.md").write_text("ok\n")
    md = ws / "note.md"
    md.write_text("[x](other.md)\n")
    proc = _run(b, ws, md)
    assert proc.returncode == 0 and proc.stderr == ""
