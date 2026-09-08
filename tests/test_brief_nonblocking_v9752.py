"""v9.7.52 — audit v9.7.49 fix: a strain-brief render failure or matplotlib/font-manager STALL
must never block the package seal. The brief render is now timeboxed + catch-all.
v9.7.80 P0 patch: subprocess path is the default; tests use MAMEY_BRIEF_FORCE_INPROCESS=1
to exercise the in-process fallback path, which preserves the original contract under mocks.
"""
import os
import time
import mamey.cli as cli


def _force_inprocess(monkeypatch_or_none=None):
    """Helper: set env var so _render_brief_nonblocking uses in-process path (testable with mocks)."""
    os.environ["MAMEY_BRIEF_FORCE_INPROCESS"] = "1"
    return lambda: os.environ.pop("MAMEY_BRIEF_FORCE_INPROCESS", None)


def test_brief_exception_is_nonfatal(tmp_path):
    cleanup = _force_inprocess()
    orig = cli.render_brief
    cli.render_brief = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("matplotlib exploded"))
    try:
        logs = []
        res = cli._render_brief_nonblocking(tmp_path, "standard", logs.append)
    finally:
        cli.render_brief = orig
        cleanup()
    assert res["status"] == "SKIPPED"
    assert any(kw in res["reason"] for kw in ("render error", "timed out", "subprocess"))
    assert any("skipped" in m for m in logs)


def test_brief_timeout_is_nonfatal(tmp_path):
    import signal as _s
    if not hasattr(_s, "SIGALRM"):
        return
    cleanup = _force_inprocess()
    orig = cli.render_brief
    cli.render_brief = lambda *a, **k: time.sleep(4)
    try:
        res = cli._render_brief_nonblocking(tmp_path, "standard", lambda m: None, timeout_s=1)
    finally:
        cli.render_brief = orig
        cleanup()
    assert res["status"] == "SKIPPED"
    assert "timed out" in res["reason"]


def test_brief_success_passes_through(tmp_path):
    """Success path: subprocess unavailable, fallback to in-process which succeeds."""
    cleanup = _force_inprocess()
    orig = cli.render_brief
    cli.render_brief = lambda *a, **k: {"status": "COMPLETE", "tier": "standard", "files": ["x.png"]}
    try:
        res = cli._render_brief_nonblocking(tmp_path, "standard", lambda m: None)
    finally:
        cli.render_brief = orig
        cleanup()
    assert res["status"] == "COMPLETE" and res["files"] == ["x.png"]
