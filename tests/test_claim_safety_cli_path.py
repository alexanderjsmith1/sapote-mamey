"""v9.7.217 (#3 reopen): the CLI `claim-safety` runs tools/claim_safety_linter.py::lint_claim_safety_report
(the robust cnames path), NOT mamey/claim_safety_gate.py::lint_text. The .216 fix patched the latter, so
denied §14 productions still flagged end-to-end. This tests the ACTUAL CLI path with the audit's battery."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
from claim_safety_linter import lint_claim_safety_report

_CN = {"colibrimycin", "bombyxamycin"}
_ANCHOR = " The KCB is a similarity anchor, not identity; capacity consistent with a class precedent."

def _ident(txt):
    return [r for r in lint_claim_safety_report(txt, card_id="BGC010", compound_names=_CN)
            if r["violation_type"] == "identity_overclaim"]

def test_denied_production_not_flagged():
    assert _ident("This card does not assert that BGC010 produces colibrimycin." + _ANCHOR) == []

def test_does_not_support_not_flagged():
    assert _ident("The evidence does not support that BGC010 produces colibrimycin." + _ANCHOR) == []

def test_genuine_overclaim_still_flagged():
    assert _ident("BGC010 produces colibrimycin at high titer." + _ANCHOR)

def test_rather_than_not_flagged():
    assert _ident("Resembles colibrimycin rather than produces colibrimycin." + _ANCHOR) == []
