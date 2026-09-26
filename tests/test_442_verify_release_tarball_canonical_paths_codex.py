"""Archive names with path aliases cannot establish extraction-equivalent membership."""
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/verify_release_tarball.py"
TOP = "sapote-mamey-vX-CODE-fixture"


@pytest.mark.parametrize("alias", ["tools//a.py", "tools/./a.py"])
def test_zip_tar_path_aliases_are_refused(tmp_path, alias):
    files = [(alias, b"alias\n"), ("tools/a.py", b"canonical\n")]
    sealed_zip = tmp_path / (TOP + ".zip")
    tarball = tmp_path / (TOP + ".tar.gz")
    with zipfile.ZipFile(sealed_zip, "w") as archive:
        for name, data in files:
            archive.writestr(name, data)
    with tarfile.open(tarball, "w:gz") as archive:
        for name, data in files:
            info = tarfile.TarInfo(TOP + "/" + name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    receipt = tmp_path / "SEAL_RECEIPT.json"
    receipt.write_text(json.dumps({
        "schema": "sapote-mamey.local-code-seal.v1", "status": "SEALED_LOCAL_CODE", "tier": "CODE",
        "archive": {"path": sealed_zip.name,
                    "sha256": hashlib.sha256(sealed_zip.read_bytes()).hexdigest(),
                    "bytes": sealed_zip.stat().st_size},
    }))
    result = subprocess.run([sys.executable, str(TOOL), str(tarball), "--zip", str(sealed_zip),
                             "--seal-receipt", str(receipt)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "noncanonical sealed ZIP member" in result.stdout


def test_tar_file_alias_is_refused_with_canonical_zip(tmp_path):
    sealed_zip = tmp_path / (TOP + ".zip")
    tarball = tmp_path / (TOP + ".tar.gz")
    with zipfile.ZipFile(sealed_zip, "w") as archive:
        archive.writestr("tools/a.py", b"canonical\n")
    with tarfile.open(tarball, "w:gz") as archive:
        info = tarfile.TarInfo(TOP + "/tools/./a.py")
        data = b"canonical\n"
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))
    receipt = tmp_path / "SEAL_RECEIPT.json"
    receipt.write_text(json.dumps({
        "schema": "sapote-mamey.local-code-seal.v1", "status": "SEALED_LOCAL_CODE", "tier": "CODE",
        "archive": {"path": sealed_zip.name,
                    "sha256": hashlib.sha256(sealed_zip.read_bytes()).hexdigest(),
                    "bytes": sealed_zip.stat().st_size},
    }))
    result = subprocess.run([sys.executable, str(TOOL), str(tarball), "--zip", str(sealed_zip),
                             "--seal-receipt", str(receipt)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "noncanonical tar file" in result.stdout
