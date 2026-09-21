"""Guardrail: patch_queue_composition_audit must verify a diff APPLIES and that git-apply
and patch agree. A patch git rejects ('corrupt patch') while patch -p1 accepts silently
divided 'applies' by tool — this test pins that such a patch is surfaced, never OK."""
import sys, subprocess, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import patch_queue_composition_audit as m

def _base(tmp_path):
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "x.py").write_text("a = 1\nb = 2\nc = 3\n")
    return tmp_path

def _write(p, text):
    p.write_text(text); return p

def test_clean_diff_is_ok(tmp_path):
    base = _base(tmp_path)
    d = _write(tmp_path / "clean.diff",
               "--- a/tools/x.py\n+++ b/tools/x.py\n@@ -1,3 +1,3 @@\n a = 1\n-b = 2\n+b = 20\n c = 3\n")
    code, sev, _ = m._diff_apply_status(d, base)
    assert (code, sev) == (m.CODE_DIFF, "OK")

def test_nonapplying_diff_is_advisory_info(tmp_path):
    base = _base(tmp_path)
    d = _write(tmp_path / "wrongctx.diff",
               "--- a/tools/x.py\n+++ b/tools/x.py\n@@ -1,3 +1,3 @@\n z = 9\n-b = 2\n+b = 20\n c = 3\n")
    code, sev, _ = m._diff_apply_status(d, base)
    assert code == m.CODE_DIFF_NEEDS_ORDER and sev == "INFO"

def test_git_rejected_patch_is_warned_not_ok(tmp_path):
    base = _base(tmp_path)
    # Hunk header claims 4 context lines but the body supplies a truncated hunk -> git 'corrupt patch'.
    d = _write(tmp_path / "bad.diff",
               "--- a/tools/x.py\n+++ b/tools/x.py\n@@ -1,4 +1,4 @@\n a = 1\n")
    g = subprocess.run(["git","apply","--check",str(d)], cwd=base, capture_output=True, text=True)
    assert "corrupt patch" in (g.stderr or ""), "fixture must be a git-corrupt patch: " + g.stderr
    code, sev, _ = m._diff_apply_status(d, base)
    assert sev == "WARN" and code in {m.CODE_DIFF_GIT_INCOMPAT, m.CODE_DIFF_MALFORMED}

def test_skips_gracefully_without_tools(tmp_path, monkeypatch):
    base = _base(tmp_path)
    d = _write(tmp_path / "clean.diff",
               "--- a/tools/x.py\n+++ b/tools/x.py\n@@ -1,3 +1,3 @@\n a = 1\n-b = 2\n+b = 20\n c = 3\n")
    monkeypatch.setattr(shutil, "which", lambda name: None)
    code, sev, note = m._diff_apply_status(d, base)
    assert (code, sev) == (m.CODE_DIFF, "OK") and "skipped" in note


def test_git_ok_patch_reject_is_warned(tmp_path, monkeypatch):
    base = _base(tmp_path)
    d = _write(tmp_path / "tool_disagreement.diff", "--- a/tools/x.py\n+++ b/tools/x.py\n")
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0 if args[0] == "git" else 1, "", "")

    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(subprocess, "run", fake_run)
    code, sev, note = m._diff_apply_status(d, base)
    assert (code, sev) == (m.CODE_DIFF_PATCH_INCOMPAT, "WARN")
    assert "disagree" in note
    patch_call = next(args for args in calls if args[0] == "patch")
    assert "--fuzz=0" in patch_call and "--batch" in patch_call
