"""A skipped patch applicability check is shown as unverified, never as OK.

Missing apply tools, a start failure or a timeout must produce DIFF_APPLY_NOT_CHECKED with
WARN severity, and the default text report must display it.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import patch_queue_composition_audit as m  # noqa: E402

CLEAN = "--- a/tools/x.py\n+++ b/tools/x.py\n@@ -1,3 +1,3 @@\n a = 1\n-b = 2\n+b = 20\n c = 3\n"


def _trees(tmp_path):
    base = tmp_path / "base"
    (base / "tools").mkdir(parents=True)
    (base / "tools" / "x.py").write_text("a = 1\nb = 2\nc = 3\n")
    queue = tmp_path / "queue"
    (queue / "card").mkdir(parents=True)
    (queue / "card" / "card.diff").write_text(CLEAN)
    return base, queue


def test_missing_tools_are_not_checked(tmp_path, monkeypatch):
    base, queue = _trees(tmp_path)
    monkeypatch.setattr(m.shutil, "which", lambda name: None)
    code, severity, note = m._diff_apply_status(queue / "card" / "card.diff", base)
    assert (code, severity) == ("DIFF_APPLY_NOT_CHECKED", "WARN") and "skipped" in note


def test_timeout_is_not_checked(tmp_path, monkeypatch):
    base, queue = _trees(tmp_path)
    monkeypatch.setattr(m.shutil, "which", lambda name: f"/usr/bin/{name}")

    def timeout(args, **kwargs):
        raise subprocess.TimeoutExpired(args, 60)

    monkeypatch.setattr(m.subprocess, "run", timeout)
    code, severity, _ = m._diff_apply_status(queue / "card" / "card.diff", base)
    assert (code, severity) == ("DIFF_APPLY_NOT_CHECKED", "WARN")


def test_text_report_shows_the_unchecked_diff(tmp_path, monkeypatch, capsys):
    base, queue = _trees(tmp_path)
    monkeypatch.setattr(m.shutil, "which", lambda name: None)
    assert m.main([str(queue), "--base", str(base)]) == 0
    text = capsys.readouterr().out
    assert "[WARN] DIFF_APPLY_NOT_CHECKED: card -> card.diff" in text
    assert "apply-check skipped" in text
