"""Workspace discovery: explicit environment overrides, then verified ancestor markers.

The no-marker fallback is the current directory. Marker discovery itself is covered
by test_441_workspace_root_walks_to_marker.py with generic workspace fixtures.
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
    # Exercise the no-marker fallback independently of the host ancestor layout.
    monkeypatch.setattr(wr, "WORKSPACE_MARKERS", ())
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
