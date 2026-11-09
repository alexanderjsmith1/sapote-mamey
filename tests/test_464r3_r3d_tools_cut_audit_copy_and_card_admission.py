"""rebase-verify cannot pass when a tree copy failed or was incomplete, or when the card holds no patch."""
from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path
from types import SimpleNamespace

PATH = Path(__file__).resolve().parents[1] / "tools" / "cut_audit.py"
_spec = importlib.util.spec_from_file_location("cut_audit_r3d", PATH)
cut_audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cut_audit)

PASSING = "3 passed in 0.01s\n"


def _setup(tmp_path, with_diff=True):
    base = tmp_path / "base"
    (base / "tests").mkdir(parents=True)
    (base / "tools").mkdir()
    (base / "tools" / "x.py").write_text("x = 1\n")
    card = tmp_path / "card"
    card.mkdir()
    if with_diff:
        (card / "card.diff").write_text("")
    return SimpleNamespace(base=str(base), card=str(card), tests=["tests/"], python="python3",
                           timeout=60, keep=False)


def _fake(rsync):
    calls = []

    def run(cmd, cwd=None, timeout=None):
        calls.append(list(cmd))
        if cmd[0] == "rsync":
            return rsync(cmd[-2], cmd[-1])
        return 0, PASSING
    return run, calls


def _copy(src, dst):
    shutil.copytree(src, dst, dirs_exist_ok=True)
    return 0, ""


def test_complete_copies_and_a_patch_can_pass(tmp_path, monkeypatch):
    run, _ = _fake(_copy)
    monkeypatch.setattr(cut_audit, "_run", run)
    assert cut_audit.rebase_verify(_setup(tmp_path)) == 0


def test_failed_rsync_is_inconclusive_not_pass(tmp_path, monkeypatch, capsys):
    run, calls = _fake(lambda src, dst: (23, "rsync error: some files could not be transferred"))
    monkeypatch.setattr(cut_audit, "_run", run)
    assert cut_audit.rebase_verify(_setup(tmp_path)) == 2
    assert "INCONCLUSIVE (incomplete copy" in capsys.readouterr().out
    assert not any("pytest" in c for c in calls)


def test_partial_copy_with_rc_zero_is_inconclusive(tmp_path, monkeypatch, capsys):
    def partial(src, dst):
        shutil.copytree(src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns("x.py"))
        return 0, ""
    run, calls = _fake(partial)
    monkeypatch.setattr(cut_audit, "_run", run)
    assert cut_audit.rebase_verify(_setup(tmp_path)) == 2
    assert "differs from" in capsys.readouterr().out
    assert not any("pytest" in c for c in calls)


def test_card_without_a_patch_is_inconclusive(tmp_path, monkeypatch, capsys):
    run, calls = _fake(_copy)
    monkeypatch.setattr(cut_audit, "_run", run)
    assert cut_audit.rebase_verify(_setup(tmp_path, with_diff=False)) == 2
    assert "nothing was applied" in capsys.readouterr().out
    assert not any("pytest" in c for c in calls)
