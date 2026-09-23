"""The manifest's health metric must be the number the shipped tool reports on the shipped tree.

`tools/gen_release_manifest.py` exists because "RELEASE_MANIFEST.md is hand-maintained: each
release bumps the header and the body rots" -- its own words, after v9.7.95 shipped a body
describing v9.7.57. It derives the version, stamp and test counts. It does **not** derive the
strict-repository-health line, and in v9.7.439 that line rotted the same way: it reported 1324
direct print calls while `tools/repo_health.py` reported 1305 on the sealed tree, because the J5
emit-coalescing that landed in .439 removed 19 of them.

1324 is the waiver's *signed* baseline, which is a different fact from what this cut observes. The
manifest is the public validation record for a released archive, so a count in it that disagrees
with the tool shipped beside it is the kind of small thing that costs trust.
"""
import re
import subprocess
import sys
from pathlib import Path

import pytest

BUNDLE = Path(__file__).resolve().parents[1]
MANIFEST = BUNDLE / "RELEASE_MANIFEST.md"


def _manifest_print_calls() -> int:
    line = next((l for l in MANIFEST.read_text(encoding="utf-8").splitlines()
                 if "Strict repository health" in l), "")
    assert line, "RELEASE_MANIFEST.md has no 'Strict repository health' row"
    match = re.search(r"(\d+) observed direct print calls", line)
    assert match, f"could not read an observed count from: {line.strip()}"
    return int(match.group(1))


def _repo_health_print_calls() -> int:
    result = subprocess.run([sys.executable, str(BUNDLE / "tools" / "repo_health.py")],
                            capture_output=True, text=True, cwd=BUNDLE, timeout=600)
    match = re.search(r"print_calls\s+(\d+) direct terminal-emission calls",
                      result.stdout + result.stderr)
    if not match:
        pytest.skip("repo_health.py did not report a print_calls line in this environment")
    return int(match.group(1))


def test_the_manifest_reports_the_count_the_tool_measures():
    manifest, measured = _manifest_print_calls(), _repo_health_print_calls()
    assert manifest == measured, (
        f"RELEASE_MANIFEST.md says {manifest} observed direct print calls; tools/repo_health.py "
        f"measures {measured} on this tree. The manifest is the released archive's public "
        "validation record -- a stale count there is a claim the shipped tool contradicts.")
