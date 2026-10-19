"""Required cut-audit inputs fail closed; archive hashing stays opt-in.

All inputs are synthetic. Mocked children may record calls but never run source
tools; the final subprocess checks execute only our tiny synthetic version tool.
"""
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def tool():
    spec = importlib.util.spec_from_file_location("required_cut_audit", ROOT / "tools/cut_audit.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def source(tmp_path):
    root = tmp_path / "sealed fixture with spaces"
    (root / "tools").mkdir(parents=True)
    (root / "SOURCE_CHECKSUMS_SHA256.txt").write_text("opaque checksum fixture; subprocess mocked\n")
    (root / "tools/sync_version.py").write_text("# opaque version source; subprocess mocked\n")
    return root


def forbid_children(tool, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("invalid required input must refuse before any child")
    monkeypatch.setattr(tool, "_run", forbidden)


@pytest.mark.parametrize("kind", ["absent", "empty", "file"])
def test_invalid_tree_is_refused_before_any_child(tool, tmp_path, monkeypatch, capsys, kind):
    root = tmp_path / "tree"
    if kind == "empty":
        root.mkdir()
    elif kind == "file":
        root.write_text("a file is not a tree\n")
    forbid_children(tool, monkeypatch)
    assert tool.main(["verify", "--tree", str(root)]) == 1
    text = capsys.readouterr().out
    assert "VERIFY: FAIL" in text and "VERIFY: PASS" not in text


@pytest.mark.parametrize("relative", ["SOURCE_CHECKSUMS_SHA256.txt", "tools/sync_version.py"])
@pytest.mark.parametrize("kind", ["missing", "empty", "directory", "external-link"])
def test_invalid_required_artifact_refuses_before_children(tool, source, tmp_path, monkeypatch, capsys, relative, kind):
    path = source / relative
    # Replace only this test's generated fixture; no source evidence is removed.
    path.unlink()
    if kind == "empty":
        path.write_text("")
    elif kind == "directory":
        path.mkdir()
    elif kind == "external-link":
        outside = tmp_path / "outside source"
        outside.write_text("opaque fixture\n")
        path.symlink_to(outside)
    forbid_children(tool, monkeypatch)
    assert tool.main(["verify", "--tree", str(source)]) == 1
    assert "VERIFY: FAIL" in capsys.readouterr().out


def test_unreadable_required_artifact_refuses_before_children(tool, source, monkeypatch, capsys):
    original = Path.open
    def denied(path, *args, **kwargs):
        if path == source / "SOURCE_CHECKSUMS_SHA256.txt":
            raise PermissionError("synthetic unreadable input")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", denied)
    forbid_children(tool, monkeypatch)
    assert tool.main(["verify", "--tree", str(source)]) == 1
    assert "synthetic unreadable input" in capsys.readouterr().out


@pytest.mark.parametrize("argument", ["--zip", "--sha256"])
def test_partial_archive_selection_is_refused(tool, source, tmp_path, monkeypatch, capsys, argument):
    selected = tmp_path / "selected artifact"
    selected.write_text("inert fixture\n")
    forbid_children(tool, monkeypatch)
    assert tool.main(["verify", "--tree", str(source), argument, str(selected)]) == 1
    assert "--zip and --sha256 must be supplied together" in capsys.readouterr().out


def test_omitted_optional_archive_keeps_explicit_skip(tool, source, monkeypatch, capsys):
    monkeypatch.setattr(tool.shutil, "which", lambda name: "/synthetic/sha256sum" if name == "sha256sum" else None)
    calls = []
    def run(command, cwd=None, timeout=None):
        calls.append(command)
        return (0, "fixture: OK\n") if len(calls) == 1 else (0, "version check OK\n")
    monkeypatch.setattr(tool, "_run", run)
    assert tool.main(["verify", "--tree", str(source)]) == 0
    text = capsys.readouterr().out
    assert "[zip     ] not selected -> SKIP (optional)" in text
    assert "VERIFY: PASS" in text
    assert len(calls) == 2


def test_zero_verified_checksum_rows_cannot_pass(tool, source, monkeypatch, capsys):
    monkeypatch.setattr(tool.shutil, "which", lambda name: "/synthetic/sha256sum")
    monkeypatch.setattr(tool, "_run", lambda *a, **k: (0, ""))
    assert tool.main(["verify", "--tree", str(source)]) == 1
    assert "[checksums] 0 OK, 0 FAILED  -> FAIL" in capsys.readouterr().out


@pytest.mark.parametrize("corrupt", [False, True])
def test_verify_cli_with_real_checker_and_synthetic_version_tool(source, corrupt):
    if not (shutil.which("sha256sum") or shutil.which("shasum")):
        pytest.skip("native SHA-256 checker unavailable")
    payload = source / "payload.txt"
    payload.write_text("synthetic public-safe payload\n")
    version = source / "tools/sync_version.py"
    version.write_text('import sys\nassert sys.argv[1:] == ["--check"]\nsys.stdout.write("synthetic version OK\\n")\n')
    (source / "SOURCE_CHECKSUMS_SHA256.txt").write_text("".join(
        hashlib.sha256(path.read_bytes()).hexdigest() + "  ./" + path.relative_to(source).as_posix() + "\n"
        for path in (payload, version)))
    if corrupt:
        payload.write_text("changed synthetic payload\n")
    before = {p.relative_to(source): p.read_bytes() for p in source.rglob("*") if p.is_file()}
    result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/cut_audit.py"), "verify", "--tree", str(source)],
                            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), text=True, capture_output=True, timeout=10)
    assert result.returncode == (1 if corrupt else 0), result.stdout + result.stderr
    assert ("VERIFY: FAIL" if corrupt else "VERIFY: PASS") in result.stdout
    assert {p.relative_to(source): p.read_bytes() for p in source.rglob("*") if p.is_file()} == before
