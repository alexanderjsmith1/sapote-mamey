"""v9.7.95 AUDIT (P-A1/P-A2): sync_version RULES must stay live and the tree in sync.

Root cause this guards:
  docs/GUIDE/01_User_Guide.md was renamed to 01_User_Manual.md and examples/* exemplars were
  removed, but sync_version.RULES kept pointing at the old paths. A rule whose target file is
  missing is a DEAD rule: `--check` fails on a MISSING-FILE noise line, and — worse — the renamed
  file silently falls out of version coverage. That blind spot let 01_User_Manual.md ship stale at
  (engine 1.9.86, bundle v9.7.85) while the bundle was at 1.9.95 / v9.7.95.

Two guards:
  1. Every rule path resolves to a file that exists in the tree (catches rename/delete drift at the
     source, with the offending path named).
  2. `sync_version --check` exits 0 on the shipped tree (catches any genuinely stale live anchor).
"""
from __future__ import annotations
import sys
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import sync_version  # noqa: E402


def test_every_sync_rule_targets_an_existing_file():
    missing = []
    for rule in sync_version.RULES:
        rel = rule[0]
        if not (ROOT / rel).is_file():
            missing.append(rel)
    assert not missing, (
        "sync_version.RULES point at files that do not exist in the tree "
        "(dead rules — retarget or prune them): " + ", ".join(sorted(set(missing)))
    )


def test_sync_version_check_exits_zero_on_shipped_tree():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "sync_version.py"), "--check"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        "sync_version --check failed on the shipped tree:\n"
        + (proc.stdout or "") + (proc.stderr or "")
    )


def test_renamed_user_manual_is_under_coverage():
    # Direct guard against re-introducing the blind spot: the current manual filename must be
    # covered by at least one rule, and the old (renamed-away) filename must not linger.
    paths = {rule[0] for rule in sync_version.RULES}
    assert "docs/GUIDE/01_User_Manual.md" in paths, (
        "01_User_Manual.md is not tracked by any sync_version rule — version anchors in the user "
        "manual can drift undetected (this is exactly the v9.7.95 blind spot)."
    )
    assert "docs/GUIDE/01_User_Guide.md" not in paths, (
        "stale rule target docs/GUIDE/01_User_Guide.md is back — that file was renamed to "
        "01_User_Manual.md and no longer exists."
    )
