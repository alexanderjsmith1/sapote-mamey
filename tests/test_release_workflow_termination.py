"""Owned-child cancellation and serial recovery on tiny synthetic workflows.

Environment admission is a bound synthetic stub for state-machine tests; actual
watched stage execution, process monitoring, timeout and cleanup remain real.
No release shell, archive builder, runner or application code executes.
"""
import hashlib
import importlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(os.name != "posix", reason="watched release validation requires POSIX")


@pytest.fixture
def engine(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "tools"))
    return importlib.import_module("_release_workflow")


@pytest.mark.parametrize("code", [0, 7])
def test_child_result_and_prior_signal_policy_preserved(engine, tmp_path, code):
    previous = signal.getsignal(signal.SIGTERM)
    result = engine.support.run_watched([sys.executable, "-c", f"import sys;sys.stdout.write('retained evidence');sys.exit({code})"],
        cwd=tmp_path, log=tmp_path / "child.log", env=dict(os.environ), min_disk=0, timeout=3)
    assert result["exit_code"] == code and result["stop_reason"] is None
    assert (tmp_path / "child.log").read_text() == "retained evidence"
    assert signal.getsignal(signal.SIGTERM) == previous


def test_timeout_stops_owned_child_heartbeat(engine, tmp_path):
    heartbeat = tmp_path / "heartbeat"
    child = f"from pathlib import Path;import time\np=Path({str(heartbeat)!r})\nwhile True:\n p.write_text(str(time.monotonic()));time.sleep(0.02)"
    result = engine.support.run_watched([sys.executable, "-c", child], cwd=tmp_path,
        log=tmp_path / "timeout.log", env=dict(os.environ), min_disk=0, timeout=0.6, poll_interval=0.04)
    assert result["stop_reason"] == "TIME_LIMIT" and result["exit_code"] != 0
    first = heartbeat.read_text(); time.sleep(0.15)
    assert heartbeat.read_text() == first


def test_sigterm_of_watcher_stops_child_session(tmp_path):
    heartbeat = tmp_path / "heartbeat"; pidfile = tmp_path / "pid"
    child = f'''from pathlib import Path
import os,time
Path({str(pidfile)!r}).write_text(str(os.getpid()))
p=Path({str(heartbeat)!r});until=time.monotonic()+8
while time.monotonic()<until:
 p.write_text(str(time.monotonic()));time.sleep(0.02)
'''
    launcher = tmp_path / "launcher.py"
    launcher.write_text(f'''import os,sys
from pathlib import Path
sys.path.insert(0,{str(ROOT / 'tools')!r})
import _release_validation as support
support.run_watched([sys.executable,"-c",{child!r}],cwd=Path({str(tmp_path)!r}),log=Path({str(tmp_path / 'child.log')!r}),env=dict(os.environ),min_disk=0,timeout=10,poll_interval=0.04)
''')
    with (tmp_path / "launcher.log").open("w") as log:
        process = subprocess.Popen([sys.executable, "-B", str(launcher)], stdout=log, stderr=subprocess.STDOUT,
                                   env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        try:
            deadline = time.monotonic() + 4
            while not heartbeat.exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            assert heartbeat.exists(), (tmp_path / "launcher.log").read_text()
            time.sleep(0.1)
            process.terminate()
            assert process.wait(timeout=5) == 128 + signal.SIGTERM
            first = heartbeat.read_text(); time.sleep(0.15)
            assert heartbeat.read_text() == first, "owned child survived watcher termination"
        finally:
            if process.poll() is None:
                process.kill(); process.wait(timeout=5)
            if pidfile.exists():
                try: os.killpg(int(pidfile.read_text()), signal.SIGKILL)
                except ProcessLookupError: pass


@pytest.fixture
def synthetic_admission(engine, monkeypatch):
    support = engine.support
    def admit(python, *, output, env, **kwargs):
        output.mkdir(parents=True)
        steps = []
        for index in range(3):
            log = output / f"synthetic-admission-{index}.log"
            log.write_text("explicit synthetic environment fixture; not real admission\n")
            steps.append({"log": str(log), "log_sha256": support.sha256_file(log), "exit_code": 0,
                          "stop_reason": None, "started_utc": support.utc_now(), "completed_utc": support.utc_now()})
        payload = {"executable_sha256": support.sha256_file(Path(python)), "identity": {"fixture": "synthetic"},
                   "test_environment_sha256": hashlib.sha256(support.canonical_json(env)).hexdigest()}
        report = dict(payload, status="READY", resolved_executable=python, steps=steps,
                      identity_sha256=hashlib.sha256(support.canonical_json(payload)).hexdigest())
        support.atomic_json(output / "environment.json", report)
        return report
    monkeypatch.setattr(support, "admit_environment", admit)


@pytest.mark.parametrize("termination", ["failure", "timeout"])
def test_failed_or_timed_out_stage_resumes_without_repeating_green_stage(engine, synthetic_admission, tmp_path, termination):
    source = tmp_path / "source"; source.mkdir(); (source / "input.txt").write_text("source fixture\n")
    output = tmp_path / "workflow"; ready = tmp_path / "ready"
    prepare = engine.Stage("prepare", ("{PYTHON}", "-c", 'from pathlib import Path;Path(r"{OUT}/prepared.txt").write_text("prepared once")'), outputs=("prepared.txt",))
    gate_code = f"from pathlib import Path;import time\np=Path({str(ready)!r})\n"
    gate_code += ('assert p.exists(), "synthetic gate not ready"\n' if termination == "failure"
                  else 'while not p.exists(): time.sleep(0.02)\n')
    gate_code += 'Path(r"{OUT}/passed.txt").write_text("passed")'
    plan = (prepare, engine.Stage("gate", ("{PYTHON}", "-c", gate_code), outputs=("passed.txt",)))
    options = dict(env=dict(os.environ), timeout=0.6 if termination == "timeout" else 3, min_disk=0)
    def workflow(): return engine.Workflow(source, output, plan, sys.executable, **options)
    with pytest.raises(ValueError, match="stage failed"):
        workflow().run()
    original = json.loads((output / "workflow.json").read_text())
    assert original["status"] == "FAILED"
    assert original["stages"][0]["status"] == "PASS" and original["stages"][1]["status"] == "FAILED"
    failed = original["stages"][1]["attempts"][0]["receipt"]
    failed_bytes = (output / failed["path"]).read_bytes()
    attempt = json.loads(failed_bytes)
    assert attempt["watch"]["stop_reason"] == ("TIME_LIMIT" if termination == "timeout" else None)
    ready.write_text("external prerequisite ready; no source changes\n")
    with pytest.raises(ValueError, match="requires a retry reason"):
        workflow().run(resume=True)
    after = workflow().run(resume=True, retry={"gate": "Synthetic external prerequisite repaired"})
    assert after["status"] == "STAGES_COMPLETE"
    assert after["stages"][0]["active"] == original["stages"][0]["active"]
    assert len(after["stages"][0]["attempts"]) == 1 and len(after["stages"][1]["attempts"]) == 2
    assert (output / failed["path"]).read_bytes() == failed_bytes


def test_termination_records_interrupted_attempt_and_requires_explicit_retry(engine, synthetic_admission, monkeypatch, tmp_path):
    source = tmp_path / "source"; source.mkdir(); (source / "fixture.txt").write_text("unchanged\n")
    output = tmp_path / "workflow"
    plan = (engine.Stage("stage", ("{PYTHON}", "-c", "pass")),)
    real = engine.support.run_watched
    def terminate(*args, **kwargs): raise engine.support.WatchedTermination(signal.SIGTERM)
    monkeypatch.setattr(engine.support, "run_watched", terminate)
    def workflow(): return engine.Workflow(source, output, plan, sys.executable, env=dict(os.environ), min_disk=0, timeout=3)
    with pytest.raises(engine.support.WatchedTermination): workflow().run()
    before = json.loads((output / "workflow.json").read_text())
    assert before["status"] == "FAILED" and before["stages"][0]["status"] == "INTERRUPTED"
    assert "SIGTERM" in before["reason"]
    monkeypatch.setattr(engine.support, "run_watched", real)
    with pytest.raises(ValueError, match="requires a retry reason"): workflow().run(resume=True)
    result = workflow().run(resume=True, retry={"stage": "Explicit cancellation recovery with unchanged source"})
    assert result["status"] == "STAGES_COMPLETE" and len(result["stages"][0]["attempts"]) == 2
