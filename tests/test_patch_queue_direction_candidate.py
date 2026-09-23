"""Already-applied patches must not masquerade as missing apply-order dependencies."""
import importlib.util
from pathlib import Path


def load():
    path = Path(__file__).resolve().parents[1] / "tools/patch_queue_composition_audit.py"
    spec = importlib.util.spec_from_file_location("queue_direction", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_already_applied_is_explicit_and_read_only(tmp_path):
    m = load()
    base = tmp_path / "base"
    (base / "tools").mkdir(parents=True)
    target = base / "tools/example.py"
    target.write_text("a = 1\nb = 20\nc = 3\n")
    diff = tmp_path / "candidate.patch"
    diff.write_text("--- a/tools/example.py\n+++ b/tools/example.py\n@@ -1,3 +1,3 @@\n a = 1\n-b = 2\n+b = 20\n c = 3\n")
    before = target.read_bytes()
    code, severity, note = m._diff_apply_status(diff, base)
    assert code == "DIFF_ALREADY_APPLIED"
    assert severity == "WARN"
    assert target.read_bytes() == before
    assert not list(base.rglob("*.orig")) and not list(base.rglob("*.rej"))


def test_forward_patch_check_is_explicit(tmp_path, monkeypatch):
    import subprocess
    m = load()
    diff = tmp_path / "candidate.patch"
    diff.write_text("placeholder")
    calls = []
    def run(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, "", "")
    monkeypatch.setattr(m.shutil, "which", lambda name: name)
    monkeypatch.setattr(m.subprocess, "run", run)
    m._diff_apply_status(diff, tmp_path)
    assert "--forward" in next(args for args in calls if args[0] == "patch")
