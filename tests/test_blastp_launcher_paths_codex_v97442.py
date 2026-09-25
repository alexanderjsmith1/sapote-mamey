"""Guard runner launches reached through common shell wrapper forms."""
import json
import os
from pathlib import Path
import subprocess

import pytest


HOOK = Path(__file__).resolve().parents[1] / "hooks/block_blastp_overconcurrency.sh"


def _decision(tmp_path, command, live=2, cap=2):
    stub = tmp_path / "stub"
    stub.mkdir(exist_ok=True)
    rows = "\n".join(f"python3 /fixture/nr_rid_runner.py run --lane {i}" for i in range(live))
    ps = stub / "ps"
    ps.write_text("#!/bin/sh\ncat <<'ROWS'\n" + rows + "\nROWS\n")
    ps.chmod(0o755)
    env = {**os.environ, "PATH": f"{stub}{os.pathsep}{os.environ['PATH']}",
           "SAPOTE_BLASTP_MAX_LANES": str(cap)}
    result = subprocess.run(["bash", str(HOOK)], input=json.dumps({"tool_input": {"command": command}}),
                            text=True, capture_output=True, cwd=tmp_path, env=env, timeout=30)
    assert result.returncode == 0, result.stderr
    if not result.stdout.strip():
        return "ALLOW", result.stderr
    return json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"].upper(), result.stderr


@pytest.fixture
def launcher(tmp_path):
    path = tmp_path / "launch.sh"
    path.write_text("#!/bin/sh\npython3 nr_rid_runner.py run --lane 3\n")
    path.chmod(0o755)
    return path


@pytest.mark.parametrize("form", [
    "{script} fixture", "bash {script} fixture", "env bash {script} fixture",
    "bash -e {script} fixture", "nohup bash {script} fixture",
    "sleep 90 && bash {script} fixture",
])
def test_launcher_forms_are_denied_at_cap(tmp_path, launcher, form):
    decision, stderr = _decision(tmp_path, form.format(script=launcher))
    assert decision == "DENY"
    assert str(launcher) in stderr


def test_staggered_shell_launcher_allowed_below_cap(tmp_path, launcher):
    decision, _ = _decision(tmp_path, f"sleep 90 && bash {launcher}", live=1, cap=2)
    assert decision == "ALLOW"


def test_inspection_and_unrelated_script_stay_out_of_scope(tmp_path, launcher):
    ordinary = tmp_path / "ordinary.sh"
    ordinary.write_text("#!/bin/sh\necho fixture\n")
    for command in (f"cat {launcher}", f"env bash {ordinary}", "ls -la"):
        decision, stderr = _decision(tmp_path, command)
        assert decision == "ALLOW"
        assert "evaluating" not in stderr
