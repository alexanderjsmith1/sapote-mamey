"""v9.7.95 AUDIT (P-A3): RELEASE_MANIFEST.md self-describing fields must match live truth.

Guards the rot class where the manifest header is bumped each release but the body keeps an old
release's version anchors / build stamp (v9.7.95 shipped a v9.7.57 body under a v9.7.95 header).
`gen_release_manifest.py --check` derives bundle/engine/stamp from the source-of-truth files and
fails if any anchored field in RELEASE_MANIFEST.md is stale. (Test counts are not checked here —
they are runtime-derived and supplied to the tool at cut time via --pytest-log/--tests-*.)
"""
from __future__ import annotations
import sys
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_release_manifest_version_fields_in_sync():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "gen_release_manifest.py"), "--root", str(ROOT), "--check"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        "RELEASE_MANIFEST.md self-describing fields are stale — run "
        "`python3 tools/gen_release_manifest.py --apply`:\n" + (proc.stdout or "") + (proc.stderr or "")
    )
