"""Nonfinite watcher policy refuses before monitoring/allocation; no native child or PID probe."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load():
    spec = importlib.util.spec_from_file_location("finite_watch_452", ROOT / "tools/_release_validation.py")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


class MonitorReached(RuntimeError):
    pass


@pytest.mark.parametrize("field", ["rss_limit", "min_disk", "timeout", "poll_interval"])
@pytest.mark.parametrize("value", [float("nan"), float("inf")], ids=["nan", "infinity"])
def test_nonfinite_policy_refuses_before_any_monitor_or_output(tmp_path, monkeypatch, field, value):
    module = load(); calls = []; refused = False
    def barrier(pid):
        calls.append(pid); raise MonitorReached("invalid policy reached monitor")
    def forbidden(*args, **kwargs):
        raise AssertionError("invalid policy launched a process")
    monkeypatch.setattr(module.subprocess, "Popen", forbidden)
    monkeypatch.setattr(module.subprocess, "run", forbidden)
    log = tmp_path / "not-created" / "watch.log"
    try:
        module.run_watched(["NEVER_EXECUTED"], cwd=tmp_path, log=log, env={}, sampler=barrier, **{field: value})
    except module.ValidationRefused as exc:
        assert "Invalid watched-command resource policy" in str(exc); refused = True
    except MonitorReached:
        pass
    assert refused and calls == [], "nonfinite " + field + " was admitted past the resource-policy gate"
    assert not log.parent.exists()


@pytest.mark.parametrize("options", [
    {"rss_limit": 100, "min_disk": 0, "timeout": 0.5, "poll_interval": 0.1},
    {"rss_limit": 100.0, "min_disk": 0.0, "timeout": 0.5, "poll_interval": 0.1},
    {"rss_limit": 10**400, "min_disk": 0, "timeout": 0.5, "poll_interval": 0.1},
], ids=["integers-zero-disk", "existing-finite-floats", "finite-large-integer"])
def test_existing_finite_policy_reaches_the_same_monitor_gate(tmp_path, monkeypatch, options):
    module = load(); calls = []
    def barrier(pid): calls.append(pid); raise MonitorReached("synthetic stop before child")
    monkeypatch.setattr(module.subprocess, "Popen", lambda *a, **k: pytest.fail("unexpected child"))
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **k: pytest.fail("unexpected native probe"))
    with pytest.raises(MonitorReached):
        module.run_watched(["NEVER_EXECUTED"], cwd=tmp_path, log=tmp_path / "watch.log", env={}, sampler=barrier, **options)
    assert len(calls) == 1 and not (tmp_path / "watch.log").exists()
