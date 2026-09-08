"""A10/DEC-02 (.367): mamey.workspace_root is the single home-path resolver.

Byte-identical fallback when no env var is set (the JOB-C constraint), and env precedence
SAPOTE_WORKSPACE_ROOT > SAPOTE_ROOT > historical literal.
"""
import os
import importlib
from pathlib import Path
import mamey.workspace_root as wr

_LITERAL = os.getcwd()


def _clear(monkeypatch):
    monkeypatch.delenv("SAPOTE_WORKSPACE_ROOT", raising=False)
    monkeypatch.delenv("SAPOTE_ROOT", raising=False)


def test_env_unset_returns_cwd(monkeypatch):
    # v9.7.381 generic-source: no personal-home fallback; env-unset -> cwd
    _clear(monkeypatch)
    assert wr.workspace_root() == Path.cwd()


def test_workspace_root_env_wins(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", "/tmp/ws")
    assert wr.workspace_root() == Path("/tmp/ws")


def test_sapote_root_is_honored_and_workspace_takes_precedence(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("SAPOTE_ROOT", "/tmp/legacy")
    assert wr.workspace_root() == Path("/tmp/legacy")
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", "/tmp/ws")
    assert wr.workspace_root() == Path("/tmp/ws")
