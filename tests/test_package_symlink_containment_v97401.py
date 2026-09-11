"""Package seals must never follow symlinks outside the package tree.

The package writers historically admitted entries with ``Path.is_file()``, which
follows symlinks.  A link inside an otherwise valid package was therefore hashed,
validated, and copied into the sealed ZIP using the external target's bytes.
"""
from __future__ import annotations

import hashlib
import os
import zipfile
from pathlib import Path

import pytest

from mamey import packaging
from mamey.handoff import build_handoff
from mamey.seal_package import seal_package
from mamey.validate import validate_package, verify_checksums


def _add_external_symlink(package: Path, tmp_path: Path, rel: str = "figures/external.txt") -> Path:
    outside = tmp_path / "outside.txt"
    outside.write_text("outside-only bytes", encoding="utf-8")
    link = package / rel
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink creation unavailable on this platform: {exc}")
    return link


def _minimal_package(tmp_path: Path) -> Path:
    package = tmp_path / "package"
    package.mkdir()
    (package / "core.txt").write_text("contained bytes", encoding="utf-8")
    return package


def test_manifest_and_checksum_writers_refuse_symlink_without_replacing_prior_seal(tmp_path):
    package = _minimal_package(tmp_path)
    prior_manifest = b'{"prior": true}\n'
    prior_checksums = b"prior checksum bytes\n"
    (package / "manifest.json").write_bytes(prior_manifest)
    (package / "checksums_sha256.txt").write_bytes(prior_checksums)
    _add_external_symlink(package, tmp_path)

    with pytest.raises(RuntimeError, match=r"figures/external\.txt"):
        packaging.write_manifest(package)
    assert (package / "manifest.json").read_bytes() == prior_manifest
    assert (package / "checksums_sha256.txt").read_bytes() == prior_checksums

    with pytest.raises(RuntimeError, match=r"figures/external\.txt"):
        packaging.write_checksums(package)
    assert (package / "checksums_sha256.txt").read_bytes() == prior_checksums


def test_fingerprint_refuses_symlink_instead_of_hashing_external_bytes(tmp_path):
    package = _minimal_package(tmp_path)
    _add_external_symlink(package, tmp_path, "sample_2_inventory.csv")

    with pytest.raises(RuntimeError, match=r"sample_2_inventory\.csv"):
        packaging.repro_fingerprint(package)


def test_checksum_validator_rejects_symlink_even_under_exempt_postseal_tree(tmp_path):
    package = _minimal_package(tmp_path)
    content = (package / "core.txt").read_bytes()
    (package / "checksums_sha256.txt").write_text(
        f"{hashlib.sha256(content).hexdigest()}  core.txt\n", encoding="utf-8"
    )
    _add_external_symlink(package, tmp_path)

    errors = verify_checksums(package)
    assert len(errors) == 1
    assert "package containment failure" in errors[0]
    assert "figures/external.txt" in errors[0]


def test_package_validation_refuses_before_parsing_symlinked_artifacts(tmp_path):
    package = _minimal_package(tmp_path)
    _add_external_symlink(package, tmp_path, "manifest.json")

    result = validate_package(package)
    assert result["status"] == "FAIL"
    assert result["package_containment"] == "FAIL"
    assert result["containment_errors"] == [
        "package containment failure: package symlink is prohibited: manifest.json"
    ]


def test_qc_seal_refuses_before_reading_symlinked_package_tables(tmp_path):
    package = _minimal_package(tmp_path)
    _add_external_symlink(package, tmp_path, "sample_4_triage_board.csv")

    result = seal_package(package)
    assert result["overall"] == "FAIL"
    assert result["exit_code"] == 1
    assert [gate["name"] for gate in result["gates"]] == ["package_containment"]


def test_handoff_refuses_symlink_before_touching_existing_archive_or_temp(tmp_path):
    package = _minimal_package(tmp_path)
    _add_external_symlink(package, tmp_path)
    archive = tmp_path / "handoff.zip"
    archive.write_bytes(b"prior handoff bytes")

    with pytest.raises(RuntimeError, match=r"figures/external\.txt"):
        build_handoff(package, None, archive)

    assert archive.read_bytes() == b"prior handoff bytes"
    assert not Path(str(archive) + ".tmp").exists()


def test_zip_refuses_symlink_before_touching_existing_archive_or_temp(tmp_path):
    package = _minimal_package(tmp_path)
    _add_external_symlink(package, tmp_path)
    archive = tmp_path / "sealed.zip"
    archive.write_bytes(b"prior archive bytes")

    with pytest.raises(RuntimeError, match=r"figures/external\.txt"):
        packaging.zip_package(package, archive)

    assert archive.read_bytes() == b"prior archive bytes"
    assert not Path(str(archive) + ".tmp").exists()


def test_regular_package_still_manifests_validates_and_zips(tmp_path):
    package = _minimal_package(tmp_path)
    manifest = packaging.write_manifest(package)
    assert {row["path"] for row in manifest["files"]} == {"core.txt"}
    assert verify_checksums(package) == []

    archive = tmp_path / "sealed.zip"
    packaging.zip_package(package, archive)
    with zipfile.ZipFile(archive) as zf:
        assert zf.read("package/core.txt") == b"contained bytes"


def test_broken_symlink_is_also_refused(tmp_path):
    package = _minimal_package(tmp_path)
    link = package / "broken.txt"
    try:
        os.symlink(tmp_path / "does-not-exist", link)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink creation unavailable on this platform: {exc}")

    with pytest.raises(RuntimeError, match=r"broken\.txt"):
        packaging.write_checksums(package)
