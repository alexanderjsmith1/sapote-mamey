"""Regression test for tools/cut_audit.py's rebase-verify pytest invocation.

BC2-407: without --run-slow, any card touching a test file whose name matches
conftest.py's _SLOW_FILE_HINTS (e.g. "figure", "atlas", "render_fig") is silently
SKIPPED on both the base and patched sides -- so "0 failures both sides" reads as a
clean REBASE-VERIFY: PASS when in fact none of those tests ever ran. CI's own full
job always adds --run-slow (see tests/conftest.py); this harness's whole job is to
reproduce that full verification, so it must too. --run-network is deliberately NOT
asserted as present -- it requires live network, a materially different resource
this offline, read-only harness should never enable on its own.
"""
from __future__ import annotations
import importlib.util
from pathlib import Path
from types import SimpleNamespace

PATH = Path(__file__).resolve().parents[1] / "tools" / "cut_audit.py"
_spec = importlib.util.spec_from_file_location("cut_audit", PATH)
cut_audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cut_audit)


def test_rebase_verify_pytest_invocation_includes_run_slow(tmp_path, monkeypatch):
    base = tmp_path / "base"
    (base / "tests").mkdir(parents=True)
    card = tmp_path / "card"
    card.mkdir()  # no *.diff/*.patch, no test_*.py -- exercises the pytest step in isolation

    captured: list[tuple[list[str], object]] = []

    def _fake_run(cmd, cwd=None, timeout=None):
        captured.append((list(cmd), cwd))
        return 0, "1 passed in 0.01s\n"

    monkeypatch.setattr(cut_audit, "_run", _fake_run)
    args = SimpleNamespace(
        base=str(base), card=str(card), tests=None,
        python="python3", timeout=60, keep=False,
    )
    rc = cut_audit.rebase_verify(args)
    assert rc == 0

    pytest_calls = [cmd for cmd, _cwd in captured if "-m" in cmd and "pytest" in cmd]
    assert len(pytest_calls) == 2, f"expected one pytest invocation per tree (base + patched), got {pytest_calls}"
    for cmd in pytest_calls:
        assert "--run-slow" in cmd, (
            "pytest invocation is missing --run-slow -- figure/render/atlas-named test "
            f"files will be silently skipped, not verified: {cmd}"
        )
        assert "--run-network" not in cmd, f"must not silently enable live-network tests: {cmd}"


def test_rebase_verify_honors_explicit_tests_scope_alongside_run_slow(tmp_path, monkeypatch):
    base = tmp_path / "base"
    (base / "tests").mkdir(parents=True)
    card = tmp_path / "card"
    card.mkdir()

    captured: list[list[str]] = []

    def _fake_run(cmd, cwd=None, timeout=None):
        captured.append(list(cmd))
        return 0, "2 passed in 0.02s\n"

    monkeypatch.setattr(cut_audit, "_run", _fake_run)
    args = SimpleNamespace(
        base=str(base), card=str(card),
        tests=["tests/test_figure_readiness_board_v97406.py"],
        python="python3", timeout=60, keep=False,
    )
    assert cut_audit.rebase_verify(args) == 0

    pytest_calls = [cmd for cmd in captured if "-m" in cmd and "pytest" in cmd]
    assert len(pytest_calls) == 2
    for cmd in pytest_calls:
        assert "tests/test_figure_readiness_board_v97406.py" in cmd
        assert "--run-slow" in cmd
