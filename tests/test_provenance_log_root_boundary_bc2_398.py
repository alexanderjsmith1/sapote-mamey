"""BC2 .398 audit: hooks/provenance_log.py computed the logged 'path' column via a bare
`fp.startswith(root)` check -- a classic string-prefix false positive for a sibling path that
shares root's string prefix with no path separator between them (e.g. root=".../Foo",
fp=".../Foo_archive/x.md"). This workspace has many dated/versioned/archived sibling folder
names (confirmed real convention: "Patches for Sapote Mamey Claude (vX)" across dozens of
versions, "CUT_395_READY_TO_SEAL..." style archive folders, etc.), so this is a real risk
pattern for this project specifically, even though no coincidental collision exists for
today's exact SAPOTE_WORKSPACE_ROOT value.

Not currently triggering in this exact environment (checked: no real sibling of the current
root shares its prefix) -- this is a latent defect in an actively-executing code path (runs on
every real Write/Edit/MultiEdit/NotebookEdit), not a demonstrated-live-today failure. Fixed with
a boundary-safe check regardless.

Uses only synthetic paths.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
from tests.conftest import hermetic_env  # v9.7.404 bytecode-leak fix

HOOKS_DIR = pathlib.Path(__file__).resolve().parents[1] / "hooks"
HOOK = HOOKS_DIR / "provenance_log.py"


def _run_hook(root, file_path, log_path):
    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": file_path}})
    env = hermetic_env(SAPOTE_WORKSPACE_ROOT=str(root), PATH="/usr/bin:/bin")
    proc = subprocess.run([sys.executable, str(HOOK), str(log_path), "TestChat"],
                           input=payload, capture_output=True, text=True, env=env)
    return proc


def test_sibling_with_shared_prefix_is_not_treated_as_inside_root(tmp_path):
    """The consequential case: a sibling directory whose name merely starts with the same
    string as root (no path separator between them) must be logged as its own full path, not
    a '../'-prefixed relpath implying it's just outside the workspace."""
    root = tmp_path / "Workspace"
    root.mkdir()
    sibling = tmp_path / "Workspace_archive"
    sibling.mkdir()
    target = sibling / "unrelated_file.md"
    target.write_text("x")

    log = tmp_path / "log.tsv"
    _run_hook(root, str(target), log)

    rows = log.read_text().strip().splitlines()
    assert len(rows) == 2
    logged_path = rows[1].split("\t")[2]
    assert logged_path == str(target)  # full absolute path, not a relpath with ".."
    assert not logged_path.startswith("..")


def test_genuinely_inside_root_still_gets_a_clean_relative_path(tmp_path):
    """No regression: a file genuinely under root still gets a clean relative path."""
    root = tmp_path / "Workspace"
    root.mkdir()
    target = root / "sub" / "file.md"
    target.parent.mkdir(parents=True)
    target.write_text("x")

    log = tmp_path / "log.tsv"
    _run_hook(root, str(target), log)

    rows = log.read_text().strip().splitlines()
    logged_path = rows[1].split("\t")[2]
    assert logged_path in ("sub/file.md", "sub\\file.md")


def test_root_itself_is_treated_as_inside(tmp_path):
    """Edge case: fp == root exactly must not error and must resolve to '.'."""
    root = tmp_path / "Workspace"
    root.mkdir()
    log = tmp_path / "log.tsv"
    _run_hook(root, str(root), log)
    rows = log.read_text().strip().splitlines()
    logged_path = rows[1].split("\t")[2]
    assert logged_path == "."
