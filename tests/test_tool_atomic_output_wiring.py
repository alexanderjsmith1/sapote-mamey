"""Regression guards for authoritative tool outputs routed through tools._wbio.

The shared helper's temp-sibling/replace semantics are tested separately.  These tests guard
the integration point: each gate/reviewer must call the helper rather than truncating its
destination directly with Path.write_text/open(..., 'w').
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TOOLS))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_public_cut_report_uses_atomic_writer(monkeypatch, tmp_path):
    apc = _load("audit_public_cut")
    calls = []
    monkeypatch.setattr(apc, "atomic_write_text", lambda path, text: calls.append((path, text)))
    context = {
        "reconciliation": None,
        "invariants": None,
        "release_rows_checked": 0,
        "public_cohorts": {},
        "public_strain_count": 0,
        "held_cohorts": [],
    }
    out = tmp_path / "audit.md"
    assert apc.write_report([], context, "public.xlsx", out) is True
    assert calls and calls[0][0] == out
    assert "Verdict:" in calls[0][1]


def test_bgc_reconcile_cli_uses_atomic_writer(monkeypatch, tmp_path):
    br = _load("bgc_reconcile")
    calls = []
    out = tmp_path / "reconcile.md"
    monkeypatch.setattr(br, "atomic_write_text", lambda path, text: calls.append((path, text)))
    monkeypatch.setattr(br, "reconcile", lambda *a, **k: ([], {"n_with_block": 0}))
    monkeypatch.setattr(br, "render_md", lambda *a, **k: "reconcile report")
    monkeypatch.setattr(br, "_self_lint", lambda text: [])
    monkeypatch.setattr(sys, "argv", ["bgc_reconcile.py", "--package", str(tmp_path),
                                      "--map", str(tmp_path / "missing.json"), "--out", str(out)])
    br.main()
    assert calls == [(str(out), "reconcile report")]


def test_citation_audit_cli_uses_atomic_writer(monkeypatch, tmp_path):
    dca = _load("deliverable_citation_audit")
    calls = []
    out = tmp_path / "citations.md"
    monkeypatch.setattr(dca, "atomic_write_text", lambda path, text: calls.append((path, text)))
    monkeypatch.setattr(dca, "audit", lambda inputs: ([], [], [], {}, []))
    monkeypatch.setattr(dca, "render_md", lambda *a, **k: "citation report")
    monkeypatch.setattr(dca, "_self_lint", lambda text: [])
    monkeypatch.setattr(sys, "argv", ["deliverable_citation_audit.py", str(tmp_path),
                                      "--out", str(out)])
    dca.main()
    assert calls == [(str(out), "citation report")]


def test_compilation_gate_receipt_uses_atomic_writer(monkeypatch, tmp_path):
    cg = _load("compilation_gate")
    calls = []
    out = tmp_path / "receipt.json"
    receipt = {
        "gate": "PASS", "mode_b_cards": 1, "scorable_bgcs": 1,
        "page_count": None, "page_floor": 30, "checks": {}, "findings": [],
    }
    monkeypatch.setattr(cg, "atomic_write_text", lambda path, text: calls.append((path, text)))
    monkeypatch.setattr(cg, "run_gate", lambda *a, **k: dict(receipt))
    monkeypatch.setattr(sys, "argv", ["compilation_gate.py", "--md", "input.md",
                                      "--scorable-bgcs", "1", "--receipt", str(out)])
    with pytest.raises(SystemExit) as exc:
        cg.main()
    assert exc.value.code == 0
    assert len(calls) == 1 and calls[0][0] == str(out)
    assert '"gate": "PASS"' in calls[0][1]
