"""Source-release checksum records may address only admitted regular in-root files."""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import check_release_manifest as crm  # noqa: E402
import verify_release_identity as identity  # noqa: E402


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _record(root: Path, digest: str, rel: str) -> None:
    (root / "SOURCE_CHECKSUMS_SHA256.txt").write_text(
        f"{digest}  {rel}\n", encoding="utf-8"
    )


@pytest.mark.parametrize("kind", ["absolute", "parent"])
def test_lexical_escape_is_rejected_before_external_digest(tmp_path, monkeypatch, kind):
    root = tmp_path / "bundle"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"external payload")
    rel = str(outside) if kind == "absolute" else "../outside.txt"
    _record(root, _digest(outside.read_bytes()), rel)

    reads = []
    original = crm._digest

    def spy(path):
        reads.append(path)
        return original(path)

    monkeypatch.setattr(crm, "_digest", spy)
    problems, stats = crm.checksum_problems(root)

    assert any("unsafe checksum path" in problem for problem in problems)
    assert reads == [], "unsafe records must be refused before reading the external target"
    assert stats == {"n_ok": 0, "n_bad": 0, "n_missing": 0}


@pytest.mark.parametrize("through_parent", [False, True])
def test_symlink_target_is_rejected_before_digest(tmp_path, monkeypatch, through_parent):
    root = tmp_path / "bundle"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"external payload")
    if through_parent:
        (root / "linked").symlink_to(tmp_path, target_is_directory=True)
        rel = "linked/outside.txt"
    else:
        (root / "linked.txt").symlink_to(outside)
        rel = "linked.txt"
    _record(root, _digest(outside.read_bytes()), rel)

    monkeypatch.setattr(
        crm, "_digest", lambda path: pytest.fail(f"must not digest symlink target: {path}")
    )
    problems, stats = crm.checksum_problems(root)

    assert any("unsafe checksum symlink" in problem for problem in problems)
    assert stats == {"n_ok": 0, "n_bad": 0, "n_missing": 0}


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO unsupported on this platform")
def test_nonregular_target_is_rejected_without_opening(tmp_path, monkeypatch):
    root = tmp_path / "bundle"
    root.mkdir()
    fifo = root / "payload.pipe"
    os.mkfifo(fifo)
    _record(root, _digest(b"unused"), "payload.pipe")

    monkeypatch.setattr(
        crm, "_digest", lambda path: pytest.fail(f"must not open nonregular target: {path}")
    )
    problems, stats = crm.checksum_problems(root)

    assert any("unsafe non-regular checksum target" in problem for problem in problems)
    assert stats == {"n_ok": 0, "n_bad": 0, "n_missing": 0}


def test_valid_mismatch_missing_and_malformed_diagnostics_are_preserved(tmp_path):
    root = tmp_path / "bundle"
    root.mkdir()
    payload = root / "payload.txt"
    payload.write_bytes(b"payload")

    _record(root, _digest(b"payload"), "payload.txt")
    problems, stats = crm.checksum_problems(root)
    assert problems == []
    assert stats == {"n_ok": 1, "n_bad": 0, "n_missing": 0}

    _record(root, "0" * 64, "payload.txt")
    problems, stats = crm.checksum_problems(root)
    assert any("checksum mismatch" in problem for problem in problems)
    assert stats["n_bad"] == 1

    _record(root, "0" * 64, "missing.txt")
    problems, stats = crm.checksum_problems(root)
    assert any("does not exist" in problem for problem in problems)
    assert stats["n_missing"] == 1

    (root / "SOURCE_CHECKSUMS_SHA256.txt").write_text("truncated\n", encoding="utf-8")
    problems, _stats = crm.checksum_problems(root)
    assert any("malformed/unparseable" in problem for problem in problems)


def test_direct_script_reports_unsafe_target_without_traceback(tmp_path):
    root = tmp_path / "bundle"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"external payload")
    _record(root, _digest(outside.read_bytes()), str(outside))

    result = subprocess.run(
        [sys.executable, str(TOOLS / "check_release_manifest.py"), "--root", str(root)],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )

    assert result.returncode == 1
    assert "unsafe checksum path" in result.stdout
    assert "Traceback" not in result.stderr


def test_verify_release_identity_content_path_inherits_typed_failure(tmp_path):
    root = tmp_path / "bundle"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"external payload")
    _record(root, _digest(outside.read_bytes()), "../outside.txt")

    errors = identity.check_content(root)

    assert any(error.startswith("content:") for error in errors)
    assert any("unsafe checksum path" in error for error in errors)


def test_checksum_manifest_symlink_is_rejected_before_read(tmp_path, monkeypatch):
    root = tmp_path / "bundle"
    root.mkdir()
    payload = root / "payload.txt"
    payload.write_bytes(b"payload")
    external_manifest = tmp_path / "external-manifest.txt"
    external_manifest.write_text(
        f"{_digest(b'payload')}  payload.txt\n", encoding="utf-8"
    )
    sums = root / "SOURCE_CHECKSUMS_SHA256.txt"
    sums.symlink_to(external_manifest)

    original = Path.read_text

    def spy(path, *args, **kwargs):
        if path == sums:
            pytest.fail("external checksum manifest must not be read")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", spy)
    problems, stats = crm.checksum_problems(root)

    assert any("unsafe checksum symlink" in problem for problem in problems)
    assert stats == {"n_ok": 0, "n_bad": 0, "n_missing": 0}


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO unsupported on this platform")
def test_nonregular_checksum_manifest_is_typed_without_opening(tmp_path):
    root = tmp_path / "bundle"
    root.mkdir()
    os.mkfifo(root / "SOURCE_CHECKSUMS_SHA256.txt")

    problems, stats = crm.checksum_problems(root)

    assert any("unsafe non-regular checksum target" in problem for problem in problems)
    assert stats == {"n_ok": 0, "n_bad": 0, "n_missing": 0}


def test_invalid_utf8_checksum_manifest_is_reported(tmp_path):
    root = tmp_path / "bundle"
    root.mkdir()
    (root / "SOURCE_CHECKSUMS_SHA256.txt").write_bytes(b"\xff\n")

    problems, stats = crm.checksum_problems(root)

    assert any("strict UTF-8" in problem for problem in problems)
    assert stats == {"n_ok": 0, "n_bad": 0, "n_missing": 0}


def test_unreadable_checksum_manifest_is_reported_not_raised(tmp_path, monkeypatch):
    root = tmp_path / "bundle"
    root.mkdir()
    sums = root / "SOURCE_CHECKSUMS_SHA256.txt"
    sums.write_text("placeholder\n", encoding="utf-8")
    original = Path.read_text

    def refuse(path, *args, **kwargs):
        if path == sums:
            raise PermissionError("fixture denies manifest read")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", refuse)
    problems, stats = crm.checksum_problems(root)

    assert any("could not read SOURCE_CHECKSUMS_SHA256.txt" in problem for problem in problems)
    assert stats == {"n_ok": 0, "n_bad": 0, "n_missing": 0}


def test_direct_script_rejects_external_manifest_symlink(tmp_path):
    root = tmp_path / "bundle"
    root.mkdir()
    payload = root / "payload.txt"
    payload.write_bytes(b"payload")
    external_manifest = tmp_path / "external-manifest.txt"
    external_manifest.write_text(
        f"{_digest(b'payload')}  payload.txt\n", encoding="utf-8"
    )
    (root / "SOURCE_CHECKSUMS_SHA256.txt").symlink_to(external_manifest)

    result = subprocess.run(
        [sys.executable, str(TOOLS / "check_release_manifest.py"), "--root", str(root)],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )

    assert result.returncode == 1
    assert "unsafe checksum symlink" in result.stdout
    assert "Traceback" not in result.stderr
