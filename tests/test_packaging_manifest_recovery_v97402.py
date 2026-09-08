"""v9.7.402 candidate: manifest recovery and portable locator boundaries."""
from __future__ import annotations

import json

import pytest

from mamey.packaging import ManifestRecoveryRequired, write_manifest


def _package(tmp_path):
    package = tmp_path / "package"
    package.mkdir()
    (package / "core.txt").write_text("generic sealed payload\n", encoding="utf-8")
    return package


def test_manifest_uses_portable_package_root_locator(tmp_path):
    package = _package(tmp_path)

    result = write_manifest(package)

    persisted = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    assert result["package_dir"] == "."
    assert persisted["package_dir"] == "."
    assert str(package) not in (package / "manifest.json").read_text(encoding="utf-8")


@pytest.mark.parametrize("prior", [b'{"strain_id": ', b"[]\n"])
def test_unreadable_or_nonobject_manifest_is_not_replaced(tmp_path, prior):
    package = _package(tmp_path)
    manifest_path = package / "manifest.json"
    manifest_path.write_bytes(prior)

    with pytest.raises(ManifestRecoveryRequired, match="refusing to replace"):
        write_manifest(package)

    assert manifest_path.read_bytes() == prior
    assert not (package / "checksums_sha256.txt").exists()
    assert not (package / "package_status.json").exists()
    assert not (package / "claim_safety_status.json").exists()
    assert not (package / "repro_fingerprint.json").exists()
