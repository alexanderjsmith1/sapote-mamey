"""workflow --strict can pass: a mandatory step that reports N/A (W10, session close) is not incomplete.

Before the fix every mandatory step had to be PASS, but W10 always returns N/A, so --strict failed on
every package however complete it was.
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(__file__)
spec = importlib.util.spec_from_file_location("sapote_workflow_458", os.path.join(HERE, "..", "mamey", "sapote_workflow.py"))
wf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wf)


def _all_checkers_pass(monkeypatch):
    steps = []
    for sid, title, mand, pred, checker, hint in wf.STEPS:
        fake = checker if sid == "W10" else (lambda pkg, deliv, ctx: (wf.PASS, "fixture"))
        steps.append((sid, title, mand, pred, fake, hint))
    monkeypatch.setattr(wf, "STEPS", steps)


def test_w10_is_mandatory_and_reports_na():
    w10 = [s for s in wf.STEPS if s[0] == "W10"][0]
    assert w10[2] is True
    assert w10[4](None, None, {})[0] == wf.NA


def test_complete_package_has_no_incomplete_mandatory_step(tmp_path, monkeypatch):
    _all_checkers_pass(monkeypatch)
    ctx, results, order = wf.run(str(tmp_path), None, strict=True)
    assert results["W10"]["status"] == wf.NA
    assert ctx["mandatory_incomplete"] == []


def test_a_pending_mandatory_step_is_still_incomplete(tmp_path, monkeypatch):
    _all_checkers_pass(monkeypatch)
    steps = [(s[0], s[1], s[2], s[3], (lambda pkg, deliv, ctx: (wf.PENDING, "fixture")) if s[0] == "W6" else s[4], s[5])
             for s in wf.STEPS]
    monkeypatch.setattr(wf, "STEPS", steps)
    ctx, results, order = wf.run(str(tmp_path), None, strict=True)
    assert "W6" in ctx["mandatory_incomplete"]
