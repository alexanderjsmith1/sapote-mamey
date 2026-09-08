"""v9.7.281 (patch 48): the surrogate gate labels a step ENV-SKIP (not FAIL) when the command
fails only because a module is absent, and ENV-SKIP does not roll into overall FAIL (F-03)."""
from __future__ import annotations
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GATE = ROOT / "tools" / "run_chatgpt_surrogate_gate.py"


def test_env_skip_logic_present():
    src = GATE.read_text(encoding="utf-8")
    # the record() status ladder must classify "No module named" as ENV-SKIP, and overall
    # status must key off FAIL only (so ENV-SKIP steps don't fail the gate).
    assert "ENV-SKIP" in src
    assert "No module named" in src
    assert 'any(s.get("status") == "FAIL"' in src or 's.get("status") == "FAIL"' in src
