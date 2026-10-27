"""A pre-render compilation gate never licenses the _COMPENDIUM_ name.

Without --pdf, G3 (page floor) is deferred but was reported as True, printed as "G3: ✓", and the
gate printed "✓ may be named _COMPENDIUM_" with no page check at all.
"""
import subprocess
import sys
from pathlib import Path

import tools.compilation_gate as cg

ROOT = Path(__file__).resolve().parents[1]
FIX = Path(__file__).resolve().parent / "fixtures" / "compilation_gate"


def _receipt(pdf=None):
    return cg.run_gate(md_path=str(FIX / "full_compendium.md"), manifest=str(FIX / "manifest_pass.md"),
                       scorable_bgcs=5, pdf=pdf, mode="standard")


def test_pre_render_receipt_says_deferred_and_pending():
    r = _receipt()
    assert r["gate"] == "PASS" and r["checks"]["G3"] is True   # unchanged contract
    assert r["g3_state"] == "DEFERRED_PRE_RENDER"
    assert r["naming"] == "PENDING_RENDER"


def test_pre_render_printout_does_not_offer_the_compendium_name():
    out = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "compilation_gate.py"), "--md", str(FIX / "full_compendium.md"),
         "--manifest", str(FIX / "manifest_pass.md"), "--scorable-bgcs", "5"],
        capture_output=True, text=True, cwd=str(ROOT)).stdout
    assert "may be named _COMPENDIUM_" not in out
    assert "G3: – deferred (pre-render)" in out
    assert "rerun with --pdf" in out
