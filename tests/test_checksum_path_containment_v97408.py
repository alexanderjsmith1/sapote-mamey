"""Checksum records may address only regular files in the admitted package tree."""
import hashlib
from pathlib import Path

import pytest

from mamey.validate import verify_checksums


def _package(tmp_path):
    package = tmp_path / "package"
    package.mkdir()
    (package / "core.txt").write_bytes(b"contained payload")
    return package


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _checksums(package, records):
    lines = [f"{_digest(b'contained payload')}  core.txt"]
    lines.extend(f"{digest}  {path}" for digest, path in records)
    (package / "checksums_sha256.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.mark.parametrize("absolute", [False, True])
def test_external_checksum_record_is_rejected_without_reading_target(tmp_path, monkeypatch, absolute):
    package = _package(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"outside-only bytes")
    ref = str(outside) if absolute else "../outside.txt"
    _checksums(package, [(_digest(b"outside-only bytes"), ref)])
    prior = {p.name: p.read_bytes() for p in package.iterdir()}
    original_read = Path.read_bytes
    reads = []

    def watched_read(path):
        reads.append(path.resolve())
        return original_read(path)

    monkeypatch.setattr(Path, "read_bytes", watched_read)
    errors = verify_checksums(package)
    assert outside.resolve() not in reads
    assert any("unsafe checksum path" in error for error in errors)
    assert {p.name: original_read(p) for p in package.iterdir()} == prior


@pytest.mark.parametrize("ref", [
    "../issue_log.md", "../checksums_sha256.txt", "../missing_strain_brief.pdf",
    "../sample_judgment_register.json", "/issue_log.md",
    r"..\issue_log.md", r"C:\issue_log.md", "C:issue_log.md",
    r"\\server\share\issue_log.md", "nested/../issue_log.md", "bad\x00name",
])
def test_unsafe_paths_fail_before_mutable_and_presentation_exemptions(tmp_path, ref):
    package = _package(tmp_path)
    _checksums(package, [(_digest(b"anything"), ref)])
    errors = verify_checksums(package)
    assert any("unsafe checksum path" in error for error in errors)


@pytest.mark.parametrize("ref", ["nested", "."])
def test_directory_record_returns_error_instead_of_reading_directory(tmp_path, ref):
    package = _package(tmp_path)
    (package / "nested").mkdir()
    _checksums(package, [(_digest(b"anything"), ref)])
    assert verify_checksums(package)


@pytest.mark.parametrize("ref", ["nested/data file.txt", r"nested\data file.txt", "./nested/data file.txt"])
def test_contained_nested_paths_and_legacy_separators_still_verify(tmp_path, ref):
    package = _package(tmp_path)
    (package / "nested").mkdir()
    (package / "nested/data file.txt").write_bytes(b"nested payload")
    _checksums(package, [(_digest(b"nested payload"), ref)])
    assert verify_checksums(package) == []


def test_safe_missing_mutable_receipts_stay_exempt(tmp_path):
    package = _package(tmp_path)
    _checksums(package, [(_digest(b"old receipt"), "issue_log.md")])
    assert verify_checksums(package) == []


def test_missing_regular_file_and_wrong_digest_still_fail(tmp_path):
    package = _package(tmp_path)
    _checksums(package, [(_digest(b"missing"), "absent.txt")])
    assert any("missing absent.txt" in error for error in verify_checksums(package))
    (package / "core.txt").write_bytes(b"tampered")
    assert any("checksum mismatch for core.txt" in error for error in verify_checksums(package))


def test_package_validator_turns_checksum_escape_into_blocking_failure(tmp_path):
    from mamey.validate import validate_package
    from tests.test_v9_7_335_tier1_gates_known_bad_input import _make_min_package

    # Reuse the shipped generic extraction-gate fixture, not a real analysis package.
    package = _make_min_package(tmp_path)
    control = validate_package(package, enrichment_check=True)
    assert control["status"] == "MAMEY_COMPLETE"
    assert control["checksum_integrity"] == "PASS"
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"external checksum payload")
    checksums = package / "checksums_sha256.txt"
    checksums.write_text(checksums.read_text(encoding="utf-8")
                         + f"{_digest(outside.read_bytes())}  ../outside.txt\n", encoding="utf-8")

    result = validate_package(package, enrichment_check=True)
    assert result["checksum_integrity"] == "FAIL"
    assert result["status"] == "FAIL"
    assert any("unsafe checksum path" in error for error in result["checksum_errors"])
    assert outside.read_bytes() == b"external checksum payload"
