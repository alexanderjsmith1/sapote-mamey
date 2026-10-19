"""Portable parser/gate regressions; no cut, source preparation or suite runs.

Only the shell's declaration prefix or post-test gate function executes, on a
synthetic tmp_path root. Gate children are an inert executable that records calls.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None, reason="release shell checks require bash")


def shell_text():
    return (ROOT / "tools/release_cut.sh").read_text(encoding="utf-8")


def shell_environment(**extra):
    # Ambient release switches must not choose a different parser/phase route.
    env = {k: v for k, v in os.environ.items() if not k.startswith("RELEASE_")}
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHON=sys.executable)
    env.update(extra)
    return env


@pytest.mark.parametrize("arguments, parsed, error", [
    (["--skip-tests"], "PARSED letter=a skip=1", None),
    (["b", "--skip-tests"], "PARSED letter=b skip=1", None),
    ([], "PARSED letter=a skip=0", None),
    (["a", "--skip-test"], None, "unknown cut option"),
    (["a", "--skip-tests", "unexpected"], None, "unknown cut option"),
    (["a", "--skip-tests", "--skip-tests"], None, "duplicate --skip-tests"),
    (["aa"], None, "build letter must be one lowercase letter"),
])
def test_release_arguments(tmp_path, arguments, parsed, error):
    source = tmp_path / "synthetic source with spaces"
    source.mkdir()
    harness = tmp_path / "parser.sh"
    # Stop before phase dispatch, source/preflight and any preparation or test.
    prefix = shell_text().split("\nPHASE=", 1)[0]
    harness.write_text(prefix + '\nprintf "PARSED letter=%s skip=%s\\n" "$LETTER" "$SKIP_TESTS"\n')
    result = subprocess.run([BASH, str(harness), "8.8.8", str(source), str(tmp_path / "output"), *arguments],
                            env=shell_environment(), text=True, capture_output=True, timeout=10)
    if parsed is not None:
        assert result.returncode == 0, result.stderr
        assert parsed in result.stdout
    else:
        assert result.returncode != 0
        assert error in result.stderr
    assert not (tmp_path / "output").exists()
    assert not list(source.iterdir())


@pytest.mark.parametrize("identity, fails, succeeds", [(False, False, False), (True, False, True), (True, True, False)])
def test_identity_gate(tmp_path, identity, fails, succeeds):
    tools = tmp_path / "tools"
    tools.mkdir()
    if identity:
        (tools / "verify_release_identity.py").write_text("# inert synthetic identity owner\n")
    binary = tmp_path / "bin"
    binary.mkdir()
    fake = binary / "python3"
    fake.write_text('#!/usr/bin/env bash\nprintf "%s\\n" "$*" >> "$GATE_LOG"\n'
                    'if [[ "$1" == tools/verify_release_identity.py && "$FAIL_IDENTITY" == 1 ]]; then exit 7; fi\n'
                    'printf "OK\\n"\n')
    fake.chmod(0o755)
    text = shell_text()
    function = text[text.index("post_test_gates(){"):text.index("\nbuild_tiers(){")]
    harness = tmp_path / "gates.sh"
    harness.write_text('set -euo pipefail\nsay(){ :; }; die(){ echo "ABORT: $*" >&2; exit 1; }\n'
                       'assert_no_backup_debris(){ :; }\nVER=8.8.8; STAMP=20000101v888a\n'
                       + function + "\npost_test_gates\n")
    log = tmp_path / "gate_calls.log"
    result = subprocess.run([BASH, str(harness)], cwd=tmp_path,
        env=shell_environment(PATH=str(binary) + os.pathsep + os.environ.get("PATH", ""),
                              GATE_LOG=str(log), PYTHON=str(fake), FAIL_IDENTITY="1" if fails else "0"),
        text=True, capture_output=True, timeout=10)
    assert (result.returncode == 0) is succeeds, result.stdout + result.stderr
    calls = log.read_text()
    if not identity:
        assert "release identity verifier is missing" in result.stderr
        assert "verify_release_identity.py" not in calls
    else:
        assert "verify_release_identity.py --strict-membership" in calls
    assert ("repo_health.py --strict" in calls) is succeeds
