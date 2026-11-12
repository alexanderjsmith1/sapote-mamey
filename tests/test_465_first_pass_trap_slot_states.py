"""The first-pass trap section separates a missing trap field from an empty one, and neither reads as a clean check."""
from __future__ import annotations
import importlib.util
from pathlib import Path

_TOOL = Path(__file__).resolve().parent.parent / "tools" / "build_first_pass_scans.py"
_spec = importlib.util.spec_from_file_location("build_first_pass_scans_465", _TOOL)
_m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_m)


def test_missing_field_reads_not_recorded():
    text = _m._hallucination({})
    assert "Not recorded" in text
    assert "No traps triggered" not in text


def test_empty_slot_is_not_a_clean_check():
    text = _m._hallucination({"hallucination_traps_triggered": []})
    assert "None recorded" in text
    assert "does not show that every BGC was checked" in text
    assert "Not recorded" not in text


def test_recorded_traps_still_render_as_rows():
    text = _m._hallucination({"hallucination_traps_triggered": [
        {"trap_id": "T1", "bgc": "BGC01", "label": "x", "resolution": "y"}]})
    assert "| T1 | BGC01 | x | y |" in text
    assert "None recorded" not in text
