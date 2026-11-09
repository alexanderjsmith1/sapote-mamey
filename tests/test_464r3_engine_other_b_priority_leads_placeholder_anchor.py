# Synthetic regression inputs only.
"""Ruling 15: a placeholder KCB_anchor earns no KCB bonus and no Class C KCB flag."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load():
    sys.path.insert(0, str(ROOT / "tools"))
    spec = importlib.util.spec_from_file_location("build_priority_leads_464r3b", ROOT / "tools/build_priority_leads.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _row(anchor):
    # Tier-1 + DasR + anchor: Class C exactly when the KCB flag is set
    return {"ModeB_Status": "", "SARP_support": "", "Regulators": "DasR", "KCB_anchor": anchor,
            "Tier": "1", "signals": ""}


@pytest.mark.parametrize("anchor", ["UNRESOLVED", "unresolved", "NA", "n/a", "None", "null", "-", "", "  "])
def test_placeholder_anchor_gets_no_bonus_and_no_class_c(anchor):
    mod = _load()
    score, axes = mod.score(_row(anchor))
    assert "KCB" not in axes
    assert mod.confidence_class(_row(anchor), axes) == ""
    assert score == round(mod._W_DASR + mod._W_TIER1, 2)


def test_recorded_anchor_still_counts():
    mod = _load()
    score, axes = mod.score(_row("BGC0000001 | example compound"))
    assert "KCB" in axes and mod.confidence_class(_row("x"), axes) == "C"
    assert score == round(mod._W_DASR + mod._W_TIER1 + mod._W_KCB_ANCHOR, 2)
