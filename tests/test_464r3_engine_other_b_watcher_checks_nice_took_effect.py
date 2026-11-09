# Synthetic regression inputs only.
"""The release watcher checks that `nice -n 15` actually lowered the child's priority (ruling 16).

`nice` can print a permission warning and still run the command at the old priority, so the argv
alone does not show the resource policy applied. By default the miss is recorded in the receipt's
`priority` field and warned on stderr; with `strict_priority=True` (a caller's --strict-priority)
it is a RESOURCE_POLICY_HOLD refusal before launch.
"""
from __future__ import annotations

import ast
import importlib.util
import os
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
posix = pytest.mark.skipif(os.name != "posix", reason="POSIX only")


def load():
    spec = importlib.util.spec_from_file_location("watch_nice_464r3b", ROOT / "tools/_release_validation.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _lowest():
    if os.getpriority(os.PRIO_PROCESS, 0) >= 19:
        pytest.skip("already at the lowest priority")


def _fake_nice(tmp_path):
    """A `nice` that warns and runs the command unchanged."""
    fake = tmp_path / "nice"
    fake.write_text('#!/bin/sh\necho "nice: setpriority: Operation not permitted" >&2\nshift 2\nexec "$@"\n')
    fake.chmod(0o755)
    return str(fake)


def _watch(module, tmp_path, monkeypatch, fake, **kw):
    real_which = shutil.which
    monkeypatch.setattr(module.shutil, "which", lambda name, *a, **k: fake if name == "nice" else real_which(name, *a, **k))
    marker = tmp_path / "ran"
    call = lambda: module.run_watched([sys.executable, "-c", f"open({str(marker)!r}, 'w').close()"],
                                      cwd=tmp_path, log=tmp_path / "logs" / "watch.log", env=dict(os.environ),
                                      sampler=lambda pid: 0, timeout=30, **kw)
    return call, marker


@posix
def test_real_nice_is_applied_and_recorded():
    _lowest()
    record = load().verify_nice(shutil.which("nice"))
    assert record["status"] == "APPLIED"
    assert record["probe_niceness"] >= record["expected_niceness"]


@posix
def test_default_records_and_warns_when_nice_has_no_effect(tmp_path, monkeypatch, capsys):
    _lowest()
    module = load()
    call, marker = _watch(module, tmp_path, monkeypatch, _fake_nice(tmp_path))
    receipt = call()
    assert receipt["exit_code"] == 0 and marker.exists()
    assert receipt["priority"]["status"] == "NOT_APPLIED"
    assert "did not take effect" in receipt["priority"]["message"]
    assert "WARNING: priority policy not applied" in capsys.readouterr().err


@posix
def test_strict_priority_refuses_before_launch(tmp_path, monkeypatch):
    _lowest()
    module = load()
    call, marker = _watch(module, tmp_path, monkeypatch, _fake_nice(tmp_path), strict_priority=True)
    with pytest.raises(module.ValidationRefused, match="RESOURCE_POLICY_HOLD"):
        call()
    assert not marker.exists()


def test_missing_nice_warns_by_default_and_refuses_when_strict(capsys):
    module = load()
    record = module.verify_nice(None)
    assert record["status"] == "NOT_APPLIED" and "no `nice`" in record["message"]
    assert "WARNING: priority policy not applied" in capsys.readouterr().err
    with pytest.raises(module.ValidationRefused, match="RESOURCE_POLICY_HOLD: no `nice`"):
        module.verify_nice(None, strict=True)


@posix
def test_pipe_close_error_is_recorded_not_swallowed(monkeypatch):
    _lowest()
    module = load()
    real_close = os.close
    state = {"calls": 0}

    def flaky_close(fd):
        # calls 1-2 close the write ends after spawn; call 3 is the first cleanup close
        real_close(fd)
        state["calls"] += 1
        if state["calls"] == 3:
            raise OSError(9, "Bad file descriptor")

    monkeypatch.setattr(module.os, "close", flaky_close)
    record = module.verify_nice(shutil.which("nice"))
    assert record["probe_pipe_close_errors"] and "Bad file descriptor" in record["probe_pipe_close_errors"][0]


def test_no_silent_swallow_in_the_watcher():
    tree = ast.parse((ROOT / "tools/_release_validation.py").read_text(encoding="utf-8"))
    swallows = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler)
                and len(n.body) == 1 and isinstance(n.body[0], ast.Pass)]
    assert swallows == []
