import importlib.util
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "patch_queue_relative_paths",
    ROOT / "tools" / "patch_queue_composition_audit.py",
)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


@pytest.mark.skipif(
    not shutil.which("git") or not shutil.which("patch"),
    reason="git and patch are required for apply-status comparison",
)
def test_relative_queue_and_base_paths_bind_to_the_caller_directory(
    tmp_path, monkeypatch
):
    base = tmp_path / "base"
    queue = tmp_path / "queue"
    card = queue / "card"
    base.mkdir()
    card.mkdir(parents=True)
    (base / "value.txt").write_text("old\n", encoding="utf-8")
    (card / "fix.patch").write_text(
        "--- a/value.txt\n"
        "+++ b/value.txt\n"
        "@@ -1 +1 @@\n"
        "-old\n"
        "+new\n",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    findings = audit.audit_queue(Path("queue"), Path("base"))

    assert len(findings) == 1
    assert findings[0]["code"] == audit.CODE_DIFF
    assert findings[0]["severity"] == "OK"


def test_any_git_rejection_is_reported_when_strict_patch_accepts(
    tmp_path, monkeypatch
):
    base = tmp_path / "base"
    base.mkdir()
    diff = tmp_path / "absolute-header.patch"
    diff.write_text("--- a/value.txt\n+++ /private/tmp/value.txt\n", encoding="utf-8")

    def fake_run(args, **kwargs):
        if args[0] == "git":
            return subprocess.CompletedProcess(
                args, 1, "", "error: invalid path '/private/tmp/value.txt'"
            )
        return subprocess.CompletedProcess(args, 0, b"", b"")

    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(subprocess, "run", fake_run)

    code, severity, note = audit._diff_apply_status(diff, base)

    assert (code, severity) == (audit.CODE_DIFF_GIT_INCOMPAT, "WARN")
    assert "git apply rejects" in note
