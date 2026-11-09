# Synthetic regression inputs only.
"""The release watcher's `nice` probe warns by default, never blocks, and never wraps a job in a
`nice` it has just seen fail (ruling 16).

- A probe that cannot start is NOT_APPLIED with a warning; a refusal only under strict.
- When the probe shows the policy did not take effect, the job runs without the wrapper.
- A probe that floods stderr cannot deadlock; a probe that hangs is killed at its timeout.
- When the wrapper is used, the launched child's own niceness is checked.
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import signal
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX only")


def load():
    spec = importlib.util.spec_from_file_location("watch_probe_464r3f", ROOT / "tools/_release_validation.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _lowest():
    if os.getpriority(os.PRIO_PROCESS, 0) >= 19:
        pytest.skip("already at the lowest priority")


def _script(tmp_path, name, body):
    path = tmp_path / name
    path.write_text(body)
    path.chmod(0o755)
    return str(path)


@pytest.fixture
def alarm():
    """Fail instead of hanging the suite if the probe blocks."""
    def _raise(*_a):
        raise TimeoutError("probe blocked")
    old = signal.signal(signal.SIGALRM, _raise)
    signal.alarm(30)
    yield
    signal.alarm(0)
    signal.signal(signal.SIGALRM, old)


def _watch(module, tmp_path, monkeypatch, fake, command=None, **kw):
    real_which = shutil.which
    monkeypatch.setattr(module.shutil, "which",
                        lambda name, *a, **k: fake if name == "nice" else real_which(name, *a, **k))
    marker = tmp_path / "ran"
    command = command or [sys.executable, "-c", f"open({str(marker)!r}, 'w').close()"]
    receipt = module.run_watched(command, cwd=tmp_path, log=tmp_path / "logs" / "watch.log",
                                 env=dict(os.environ), sampler=lambda pid: 0, timeout=30, **kw)
    return receipt, marker


def test_probe_spawn_failure_warns_by_default_and_refuses_when_strict(tmp_path, capsys):
    module = load()
    fake = _script(tmp_path, "nice", "#!/nonexistent/interpreter\n")
    record = module.verify_nice(fake)
    assert record["status"] == "NOT_APPLIED" and "could not start" in record["message"]
    assert "WARNING: priority policy not applied" in capsys.readouterr().err
    with pytest.raises(module.ValidationRefused, match="RESOURCE_POLICY_HOLD"):
        module.verify_nice(fake, strict=True)


def test_a_failed_wrapper_is_not_used_to_launch_the_job(tmp_path, monkeypatch, alarm):
    _lowest()
    module = load()
    fake = _script(tmp_path, "nice", '#!/bin/sh\necho "nice: failed" >&2\nexit 1\n')
    receipt, marker = _watch(module, tmp_path, monkeypatch, fake)
    assert receipt["priority"]["status"] == "NOT_APPLIED"
    assert receipt["priority"]["wrapper"] == "none"
    assert receipt["argv"][0] != fake
    assert receipt["exit_code"] == 0 and marker.exists()


def test_a_flood_of_probe_stderr_does_not_deadlock(tmp_path, alarm):
    module = load()
    fake = _script(tmp_path, "nice",
                   '#!/bin/sh\nhead -c 300000 /dev/zero | tr "\\0" x >&2\nshift 2\nexec "$@"\n')
    started = time.monotonic()
    record = module.verify_nice(fake)
    assert time.monotonic() - started < 15
    assert record["probe_timed_out"] is False
    assert record["status"] in {"APPLIED", "NOT_APPLIED"}


def test_a_hung_probe_is_killed_at_its_timeout(tmp_path, alarm, capsys):
    module = load()
    pidfile = tmp_path / "probe.pid"
    fake = _script(tmp_path, "nice", f'#!/bin/sh\necho $$ > "{pidfile}"\nexec sleep 60\n')
    started = time.monotonic()
    record = module.verify_nice(fake, timeout=0.5)
    assert time.monotonic() - started < 10
    assert record["status"] == "NOT_APPLIED" and record["probe_timed_out"] is True
    assert "did not finish" in record["message"]
    assert "WARNING: priority policy not applied" in capsys.readouterr().err
    with pytest.raises(ProcessLookupError):
        os.kill(int(pidfile.read_text()), 0)
    with pytest.raises(module.ValidationRefused, match="RESOURCE_POLICY_HOLD"):
        module.verify_nice(fake, strict=True, timeout=0.5)


def test_child_niceness_is_checked_when_the_wrapper_is_used(tmp_path, monkeypatch, alarm, capsys):
    _lowest()
    real = shutil.which("nice")
    if not real or load().verify_nice(real)["status"] != "APPLIED":
        pytest.skip("real nice cannot lower priority here")
    module = load()
    # Renices the probe (its argv has -I) but not the watched job.
    fake = _script(tmp_path, "nice",
                   f'#!/bin/sh\ncase " $* " in *" -I "*) exec "{real}" "$@";; esac\nshift 2\nexec "$@"\n')
    command = [sys.executable, "-c", "import time; time.sleep(1.5)"]
    receipt, _marker = _watch(module, tmp_path, monkeypatch, fake, command=command, poll_interval=0.2)
    priority = receipt["priority"]
    assert priority["wrapper"] == "nice -n 15"
    assert priority["child_check"] == "BELOW_EXPECTED_NICENESS"
    assert priority["status"] == "NOT_APPLIED"
    assert "launched child" in capsys.readouterr().err
    assert receipt["stop_reason"] is None and receipt["exit_code"] == 0


def test_child_niceness_below_expected_stops_the_job_under_strict(tmp_path, monkeypatch, alarm):
    _lowest()
    real = shutil.which("nice")
    if not real or load().verify_nice(real)["status"] != "APPLIED":
        pytest.skip("real nice cannot lower priority here")
    module = load()
    fake = _script(tmp_path, "nice",
                   f'#!/bin/sh\ncase " $* " in *" -I "*) exec "{real}" "$@";; esac\nshift 2\nexec "$@"\n')
    command = [sys.executable, "-c", "import time; time.sleep(5)"]
    receipt, _marker = _watch(module, tmp_path, monkeypatch, fake, command=command,
                              poll_interval=0.2, strict_priority=True)
    assert str(receipt["stop_reason"]).startswith("RESOURCE_POLICY_HOLD")
