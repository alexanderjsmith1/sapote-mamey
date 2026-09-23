import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import gate_stem_aware as gate  # noqa: E402


def test_engine_gate_returns_the_existing_sibling_checker():
    assert gate._engine_gate() == (ROOT / "tools" / "tree_sanity_check.py").resolve()


def test_engine_gate_refuses_when_the_sibling_checker_is_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(gate, "__file__", str(tmp_path / "gate_stem_aware.py"))

    with pytest.raises(FileNotFoundError, match="GATE_UNAVAILABLE"):
        gate._engine_gate()
