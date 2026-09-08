"""Package sealing admits only a physical directory root and regular files."""
from __future__ import annotations

import hashlib
import os

import pytest

from mamey import packaging
from mamey.validate import validate_package, verify_checksums


def _sealed_minimal(root):
    root.mkdir()
    payload = root / "core.txt"
    payload.write_bytes(b"contained")
    (root / "checksums_sha256.txt").write_text(
        f"{hashlib.sha256(payload.read_bytes()).hexdigest()}  core.txt\n",
        encoding="utf-8",
    )
    return root


def test_package_root_symlink_is_refused_before_target_enumeration(tmp_path):
    real = _sealed_minimal(tmp_path / "real-package")
    alias = tmp_path / "package-link"
    try:
        alias.symlink_to(real, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"directory symlink unavailable: {exc}")

    with pytest.raises(packaging.PackageContainmentError, match="package root symlink"):
        packaging._package_files_fail_closed(alias)
    assert verify_checksums(alias)[0].startswith("package containment failure")
    result = validate_package(alias, write_status_receipt=False)
    assert result["status"] == "FAIL"
    assert result["package_containment"] == "FAIL"


def test_fifo_inside_package_is_refused_instead_of_silently_omitted(tmp_path):
    package = _sealed_minimal(tmp_path / "package")
    fifo = package / "untracked.pipe"
    if not hasattr(os, "mkfifo"):
        pytest.skip("FIFO creation unavailable")
    try:
        os.mkfifo(fifo)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"FIFO creation unavailable: {exc}")
    try:
        with pytest.raises(packaging.PackageContainmentError, match=r"non-regular package entry: untracked\.pipe"):
            packaging._package_files_fail_closed(package)
        errors = verify_checksums(package)
        assert len(errors) == 1
        assert "non-regular package entry: untracked.pipe" in errors[0]
    finally:
        fifo.unlink(missing_ok=True)


def test_regular_directories_and_files_remain_admitted(tmp_path):
    package = _sealed_minimal(tmp_path / "package")
    nested = package / "nested"
    nested.mkdir()
    (nested / "data.txt").write_text("data", encoding="utf-8")
    rels = [p.relative_to(package).as_posix()
            for p in packaging._package_files_fail_closed(package)]
    assert rels == ["checksums_sha256.txt", "core.txt", "nested/data.txt"]
