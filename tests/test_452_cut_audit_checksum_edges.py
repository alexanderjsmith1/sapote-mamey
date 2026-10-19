"""Synthetic checksum-helper compatibility; no native checker or nested suite."""
import hashlib
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def tool(monkeypatch):
    spec = importlib.util.spec_from_file_location("cut_checksum_edges", ROOT / "tools/cut_audit.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module.shutil, "which", lambda name: "/synthetic/sha256sum" if name == "sha256sum" else None)
    def forbidden(*args, **kwargs):
        raise AssertionError("No uninspected checker, version tool, nested pytest or other child")
    monkeypatch.setattr(module, "_run", forbidden)
    return module


def source(tmp_path):
    root = tmp_path / "toy source with spaces"
    root.mkdir()
    (root / "SOURCE_CHECKSUMS_SHA256.txt").write_text("synthetic manifest text; dispatch is mocked\n")
    (root / "tools").mkdir()
    (root / "tools/sync_version.py").write_text("# opaque version source; dispatch is mocked\n")
    return root


@pytest.mark.parametrize("rc, output", [(1, "fixture: OK\n"), (0, "fixture: FAILED\n")])
def test_checksum_failure_cannot_become_verify_success(tool, tmp_path, monkeypatch, capsys, rc, output):
    root = source(tmp_path)
    monkeypatch.setattr(tool, "_run", lambda *a, **k: (rc, output))
    assert tool.main(["verify", "--tree", str(root)]) == 1
    assert "VERIFY: FAIL" in capsys.readouterr().out


def test_public_verify_binds_checker_working_directory(tool, tmp_path, monkeypatch):
    root = source(tmp_path)
    calls = []
    def run(command, cwd=None, timeout=None):
        calls.append((command, cwd))
        assert cwd == str(root.resolve())
        assert command[-1] in {"SOURCE_CHECKSUMS_SHA256.txt", "--check"}
        return 0, "fixture: OK\n"
    monkeypatch.setattr(tool, "_run", run)
    assert tool.main(["verify", "--tree", str(root)]) == 0
    assert len(calls) == 2
    assert calls[0][0][-1] == "SOURCE_CHECKSUMS_SHA256.txt"
    assert calls[1][0][-2:] == ["tools/sync_version.py", "--check"]


@pytest.mark.parametrize("version_rc, expected", [(0, 0), (2, 1)])
def test_public_verify_retains_version_check_and_its_failure(tool, tmp_path, monkeypatch, version_rc, expected):
    root = source(tmp_path)
    (root / "tools/sync_version.py").write_text("opaque source text; never executed\n")
    calls = []
    def run(command, cwd=None, timeout=None):
        calls.append((command, cwd))
        return (version_rc, "synthetic version check\n") if len(calls) == 2 else (0, "fixture: OK\n")
    monkeypatch.setattr(tool, "_run", run)
    assert tool.main(["verify", "--tree", str(root), "--python", "synthetic-python"]) == expected
    assert calls[1] == (["synthetic-python", "tools/sync_version.py", "--check"], str(root.resolve()))
    assert len(calls) == 2


@pytest.mark.parametrize("matches, expected", [(True, 0), (False, 1)])
def test_optional_archive_hash_keeps_matching_and_mismatch_states(tool, tmp_path, monkeypatch, matches, expected):
    root = source(tmp_path)
    archive = tmp_path / "toy.code.zip"
    data = b"inert hash-only bytes, not a claim of a valid ZIP"
    archive.write_bytes(data)
    sums = tmp_path / "archive.sha256"
    sums.write_text((hashlib.sha256(data).hexdigest() if matches else "0" * 64) + "  " + archive.name + "\n")
    monkeypatch.setattr(tool, "_run", lambda *a, **k: (0, "fixture: OK\n"))
    assert tool.main(["verify", "--tree", str(root), "--zip", str(archive), "--sha256", str(sums)]) == expected


def test_absent_tree_cannot_become_all_skipped_verify_success(tool, tmp_path, capsys):
    assert tool.main(["verify", "--tree", str(tmp_path / "absent")]) == 1
    text = capsys.readouterr().out
    assert "VERIFY: FAIL" in text
    assert "VERIFY: PASS" not in text
