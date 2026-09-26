"""Common shell redirections must not become launch candidates or hide a launcher."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "hooks" / "blastp_launch_probe.py"
HOOK = ROOT / "hooks" / "block_blastp_overconcurrency.sh"
spec = importlib.util.spec_from_file_location("blastp_probe_redirection", PROBE)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


@pytest.mark.parametrize("command,expected", [
    ("./launch.sh > out.log 2>&1", ["./launch.sh"]),
    ("./launch.sh &>out.log", ["./launch.sh"]),
    ("./launch.sh &>>all.log", ["./launch.sh"]),
    (">out.log ./launch.sh", ["./launch.sh"]),
    ("2>/dev/null ./launch.sh", ["./launch.sh"]),
    ("&>out.log ./launch.sh", ["./launch.sh"]),
    ("./launch.sh 2>&-", ["./launch.sh"]),
    ("./launch.sh 0<&- 3>&1", ["./launch.sh"]),
    ("nohup python3 launch.sh > out.log 2>&1 &", ["launch.sh"]),
    ("./launch.sh & >out.log ./other.sh", ["./launch.sh", "./other.sh"]),
    ("./launch.sh |& tee out.log", ["./launch.sh", "tee"]),
    ("sleep 90 && bash launch.sh &>out.log", ["sleep", "launch.sh"]),
    ('python3 -c "print(1)"', []),
    ("./launch.sh $(whoami)", []),
])
def test_probe_redirection_and_separator_tokens(command, expected):
    assert probe.candidates(command) == expected


@pytest.mark.parametrize("prefix", [">out.log", "2>/dev/null", "&>out.log"])
def test_hook_denies_runner_reached_after_prefix_redirect(tmp_path, prefix):
    launcher = tmp_path / "launch.sh"
    launcher.write_text("#!/bin/sh\npython3 nr_rid_runner.py run --lane 3\n")
    launcher.chmod(0o755)
    stub = tmp_path / "stub"
    stub.mkdir()
    ps = stub / "ps"
    ps.write_text("#!/bin/sh\nprintf '%s\\n' 'python3 /fixture/nr_rid_runner.py run --lane 1' "
                  "'python3 /fixture/nr_rid_runner.py run --lane 2'\n")
    ps.chmod(0o755)
    env = dict(os.environ, PATH=f"{stub}{os.pathsep}{os.environ['PATH']}",
               SAPOTE_BLASTP_MAX_LANES="2")
    command = f"{prefix} bash {launcher}"
    subprocess.run(["bash", "-n", "-c", command], check=True, capture_output=True)
    run = subprocess.run(["bash", str(HOOK)],
                         input=json.dumps({"tool_input": {"command": command}}),
                         text=True, capture_output=True, cwd=tmp_path, env=env, timeout=30)
    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout)["hookSpecificOutput"]["permissionDecision"].upper() == "DENY"
