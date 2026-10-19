"""Acceptance regressions for environment admission and resource-stop behavior."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import sysconfig
import time
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
SUPPORT = ROOT / "tools/_release_validation.py"
spec = importlib.util.spec_from_file_location("candidate_release_validation", SUPPORT)
rv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rv)
PYTHON = str(Path(sys.executable).absolute())


def test_support_import_has_no_execution_or_filesystem_side_effects(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    before = dict(os.environ)
    def refuse(*args, **kwargs):
        raise AssertionError("import attempted execution")
    monkeypatch.setattr(subprocess, "run", refuse)
    monkeypatch.setattr(subprocess, "Popen", refuse)
    fresh_spec = importlib.util.spec_from_file_location("fresh_release_validation", SUPPORT)
    fresh = importlib.util.module_from_spec(fresh_spec)
    fresh_spec.loader.exec_module(fresh)
    assert dict(os.environ) == before
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("locator", ["definitely-no-such-python-450", "/missing/interpreter"])
def test_missing_interpreter_is_a_typed_refusal(locator):
    with pytest.raises(rv.ValidationRefused, match="unavailable"):
        rv.resolve_interpreter(locator)


def test_alias_invocation_is_preserved_and_identity_binds_locator(tmp_path):
    # A Python symlink outside a venv does not inherit that venv's packages.
    # Reproduce an alias environment using a temporary layout and read-only
    # site-packages link, without installing or copying dependencies.
    alias_root = tmp_path / "alias environment"
    alias = alias_root / "bin/python3"
    alias.parent.mkdir(parents=True); alias.symlink_to(Path(PYTHON).resolve())
    (alias_root / "pyvenv.cfg").write_text(
        f"home = {Path(sys.base_prefix) / 'bin'}\ninclude-system-site-packages = false\n"
        f"version = {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}\n")
    alias_site = alias_root / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
    alias_site.parent.mkdir(parents=True)
    alias_site.symlink_to(Path(sysconfig.get_path("purelib")), target_is_directory=True)
    env = dict(os.environ)
    env.pop("PYTHONOPTIMIZE", None); env.pop("PYTEST_ADDOPTS", None)
    aliased = rv.admit_environment(alias, output=tmp_path / "alias evidence", env=env)
    canonical = rv.admit_environment(PYTHON, output=tmp_path / "canonical evidence", env=env)
    assert aliased["status"] == canonical["status"] == "READY"
    assert aliased["resolved_executable"] == str(alias)
    assert aliased["executable_target"] == str(Path(PYTHON).resolve())
    assert aliased["identity_sha256"] != canonical["identity_sha256"]
    assert aliased["executable_sha256"] == canonical["executable_sha256"]
    assert aliased["identity"]["invocation_executable"] == str(alias)
    assert aliased["venv_probe"]["isolated"] is True
    home = next(line for line in aliased["pyvenv_cfg"].splitlines() if line.startswith("home = "))
    assert Path(home.split(" = ", 1)[1]).resolve() == Path(PYTHON).resolve().parent
    assert str(alias.parent) not in home
    assert not (tmp_path / "alias evidence/venv probe").exists()
    assert not (tmp_path / "canonical evidence/venv probe").exists()
    saved = json.loads((tmp_path / "alias evidence/environment.json").read_text())
    assert saved["status"] == "READY" and len(saved["steps"]) == 3
    assert all(step["exit_code"] == 0 and step["stop_reason"] is None for step in saved["steps"])
    assert all(rv.sha256_file(Path(step["log"])) == step["log_sha256"] for step in saved["steps"])


def test_preflight_does_not_overwrite_existing_evidence(tmp_path):
    out = tmp_path / "evidence"; out.mkdir(); marker = out / "environment.json"
    marker.write_text("previous attempt")
    with pytest.raises(rv.ValidationRefused, match="occupied"):
        rv.admit_environment(PYTHON, output=out)
    assert marker.read_text() == "previous attempt"


@pytest.mark.parametrize("key,value,reason", [
    ("PYTHONOPTIMIZE", "1", "Optimized"),
    ("PYTHONOPTIMIZE", "2", "Optimized"),
    ("PYTEST_ADDOPTS", "-k only_easy_tests", "PYTEST_ADDOPTS"),
])
def test_ambient_test_weakening_is_refused_before_execution(tmp_path, monkeypatch, key, value, reason):
    def refuse(*args, **kwargs):
        raise AssertionError("a refused environment started a command")
    monkeypatch.setattr(rv, "run_watched", refuse)
    env = dict(os.environ); env[key] = value
    result = rv.admit_environment(PYTHON, output=tmp_path / "evidence", env=env)
    assert result["status"] == "REFUSED" and reason in result["reason"]
    assert result["steps"] == []
    assert json.loads((tmp_path / "evidence/environment.json").read_text())["status"] == "REFUSED"


def test_non_python_executable_is_not_admitted(tmp_path):
    report = rv.admit_environment("false", output=tmp_path / "evidence")
    assert report["status"] == "REFUSED"
    assert report["steps"][0]["exit_code"] != 0
    assert (tmp_path / "evidence/identity.log").is_file()


def test_monitor_is_admitted_before_starting_a_child(tmp_path):
    marker = tmp_path / "must-not-exist"
    def broken(pid):
        raise rv.ValidationRefused("monitor unavailable")
    with pytest.raises(rv.ValidationRefused, match="monitor unavailable"):
        rv.run_watched([PYTHON, "-c", f"open({str(marker)!r}, 'w').write('started')"],
                       cwd=tmp_path, log=tmp_path / "command.log", env=dict(os.environ), sampler=broken)
    assert not marker.exists() and not (tmp_path / "command.log").exists()


def test_low_disk_refuses_before_starting_a_child(tmp_path, monkeypatch):
    monkeypatch.setattr(rv.shutil, "disk_usage", lambda _: SimpleNamespace(free=1))
    marker = tmp_path / "must-not-exist"
    with pytest.raises(rv.ValidationRefused, match="free disk"):
        rv.run_watched([PYTHON, "-c", f"open({str(marker)!r}, 'w').write('started')"],
                       cwd=tmp_path, log=tmp_path / "command.log", env=dict(os.environ), sampler=lambda _: 0)
    assert not marker.exists()


def test_failed_command_preserves_exit_and_log(tmp_path):
    result = rv.run_watched([PYTHON, "-c", "import sys;sys.stderr.write('failure evidence');sys.exit(7)"],
                            cwd=tmp_path, log=tmp_path / "failure.log", env=dict(os.environ))
    assert result["exit_code"] == 7 and result["stop_reason"] is None
    assert (tmp_path / "failure.log").read_text() == "failure evidence"
    assert result["log_sha256"] == rv.sha256_file(tmp_path / "failure.log")


def test_occupied_log_never_launches_the_command(tmp_path):
    log = tmp_path / "existing.log"; log.write_text("old evidence")
    marker = tmp_path / "must-not-exist"
    with pytest.raises(FileExistsError):
        rv.run_watched([PYTHON, "-c", f"open({str(marker)!r}, 'w').write('started')"],
                       cwd=tmp_path, log=log, env=dict(os.environ), sampler=lambda _: 0)
    assert log.read_text() == "old evidence" and not marker.exists()


def test_forced_memory_stop_is_not_a_success(tmp_path):
    current = os.getpid()
    result = rv.run_watched([PYTHON, "-c", "import time;time.sleep(30)"], cwd=tmp_path,
                            log=tmp_path / "memory.log", env=dict(os.environ), rss_limit=100,
                            sampler=lambda pid: 0 if pid == current else 100)
    assert result["stop_reason"] == "MEMORY_LIMIT" and result["exit_code"] != 0
    assert result["peak_process_tree_rss"] == 100


def test_monitor_failure_after_launch_stops_the_child(tmp_path):
    current = os.getpid()
    def sampler(pid):
        if pid == current: return 0
        raise rv.ValidationRefused("snapshot disappeared")
    result = rv.run_watched([PYTHON, "-c", "import time;time.sleep(30)"], cwd=tmp_path,
                            log=tmp_path / "monitor.log", env=dict(os.environ), sampler=sampler)
    assert result["stop_reason"].startswith("MONITOR_ERROR")
    assert result["exit_code"] != 0


def test_timeout_terminates_child_process_group(tmp_path):
    heartbeat = tmp_path / "heartbeat"
    child = f"from pathlib import Path;import time\np=Path({str(heartbeat)!r})\nwhile True:\n p.write_text(str(time.monotonic()));time.sleep(0.03)"
    root = "import subprocess,sys,time;subprocess.Popen([sys.executable,'-c'," + repr(child) + "]);time.sleep(30)"
    result = rv.run_watched([PYTHON, "-c", root], cwd=tmp_path, log=tmp_path / "timeout.log",
                            env=dict(os.environ), timeout=0.8, poll_interval=0.05)
    assert result["stop_reason"] == "TIME_LIMIT" and heartbeat.exists()
    first = heartbeat.read_text(); time.sleep(0.2)
    assert heartbeat.read_text() == first


def test_cli_help_works_without_probing_an_environment(tmp_path):
    baseline_tools = ROOT / "tools"  # Current bundle helpers, no campaign dependency.
    assert (baseline_tools / "_console.py").is_file()
    env = dict(os.environ); env["PYTHONPATH"] = str(baseline_tools)
    result = subprocess.run([PYTHON, str(ROOT / "tools/release_validate.py"), "--help"],
                            cwd=tmp_path, env=env, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0 and "preflight" in result.stdout
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('termination', ['timeout', 'memory', 'normal_exit'])
def test_detached_descendant_is_stopped_and_not_left_running(tmp_path, termination):
    import signal
    heartbeat = tmp_path / 'detached-heartbeat'
    pidfile = tmp_path / 'detached-pid'
    child = f'''from pathlib import Path
import os,time
Path({str(pidfile)!r}).write_text(str(os.getpid()))
p=Path({str(heartbeat)!r})
while True:
 p.write_text(str(time.monotonic()));time.sleep(0.02)
'''
    root = ('import subprocess,sys,time;subprocess.Popen([sys.executable,"-c",'
            + repr(child) + '],start_new_session=True);time.sleep('
            + ('0.5' if termination == 'normal_exit' else '30') + ')')
    parent = os.getpid()
    def delayed_memory(pid):
        return 100 if pid != parent and heartbeat.exists() else 0
    options = {'timeout': 0.8, 'poll_interval': 0.04}
    if termination == 'memory':
        options.update(sampler=delayed_memory, rss_limit=100)
    try:
        result = rv.run_watched([PYTHON, '-c', root], cwd=tmp_path,
                                log=tmp_path/'detached.log', env=dict(os.environ), **options)
        assert heartbeat.exists()
        assert result['observed_owned_processes'] >= 2
        assert result['cleanup_error'] is None
        if termination == 'normal_exit':
            assert result['exit_code'] == 0 and result['stop_reason'] is None
        else:
            assert result['stop_reason'] == ('MEMORY_LIMIT' if termination == 'memory' else 'TIME_LIMIT')
        first = heartbeat.read_text();time.sleep(0.2)
        assert heartbeat.read_text() == first, 'owned detached process survived watched command'
    finally:
        # Explicit cleanup of this fixture's own session, including a failing control.
        if pidfile.exists():
            try: os.killpg(int(pidfile.read_text()), signal.SIGKILL)
            except ProcessLookupError: pass


def test_reused_pid_does_not_inherit_descendant_ownership(monkeypatch):
    tree = rv._OwnedProcessTree(1234567)
    tree.known[7654321] = (7654321, 'Fri Oct 9 18:00:00 2026')
    monkeypatch.setattr(rv, '_process_snapshot', lambda: {
        7654321: (1, 7654321, 2048, 'Fri Oct 9 18:00:01 2026')})
    assert tree.refresh() == {}


def test_cleanup_races_and_term_timeout_are_retained(monkeypatch):
    tree = rv._OwnedProcessTree(12345)
    state = {'live': True, 'clock': 0, 'waits': 0}
    monkeypatch.setattr(rv, '_process_snapshot', lambda: {12345:(1,12345,0,'fixture')} if state['live'] else {})
    def tick():
        state['clock'] += 1
        return state['clock']
    monkeypatch.setattr(rv.time, 'monotonic', tick)
    monkeypatch.setattr(rv.time, 'sleep', lambda _: None)
    def gone(pid, sig):
        if sig == rv.signal.SIGKILL: state['live'] = False
        raise ProcessLookupError('fixture concurrent exit')
    monkeypatch.setattr(rv.os, 'kill', gone)
    monkeypatch.setattr(rv.os, 'killpg', gone)
    class Process:
        pid = 12345
        def poll(self): return None if state['live'] else 0
        def wait(self, timeout=None):
            state['waits'] += 1
            raise subprocess.TimeoutExpired('fixture', timeout)
    assert tree.stop(Process()) is None
    statuses = {row['status'] for row in tree.cleanup_events}
    assert {'ALREADY_EXITED', 'TERM_WAIT_EXPIRED_ESCALATING_TO_KILL'} <= statuses
    assert {row.get('signal') for row in tree.cleanup_events if row['status']=='ALREADY_EXITED'} == {'SIGTERM','SIGKILL'}
    assert state['waits'] == 1 and not state['live'] and tree.last_owned == {}


def test_resolver_preserves_relative_venv_symlink_and_validates_target(tmp_path, monkeypatch):
    target = tmp_path / "base-python"
    target.write_text("synthetic executable")
    target.chmod(0o700)
    alias = tmp_path / "venv/bin/python"
    alias.parent.mkdir(parents=True)
    alias.symlink_to(target)
    monkeypatch.chdir(tmp_path)
    assert rv.resolve_interpreter("venv/bin/python") == alias
    assert rv.sha256_file(rv.resolve_interpreter(alias)) == rv.sha256_file(target)


def test_resolver_preserves_path_lookup_alias(tmp_path, monkeypatch):
    target = tmp_path / "base-python"
    target.write_text("synthetic executable")
    target.chmod(0o700)
    alias = tmp_path / "python"
    alias.symlink_to(target)
    monkeypatch.setenv("PATH", str(tmp_path))
    assert rv.resolve_interpreter("python") == alias


def test_resolver_rejects_dangling_symlink(tmp_path):
    alias = tmp_path / "python"
    alias.symlink_to(tmp_path / "missing")
    with pytest.raises(rv.ValidationRefused, match="unavailable"):
        rv.resolve_interpreter(alias)
