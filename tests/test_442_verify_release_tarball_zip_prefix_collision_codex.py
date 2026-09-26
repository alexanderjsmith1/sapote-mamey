"""A sealed ZIP cannot describe a regular file that is also a directory parent."""
import importlib.util
import io
import tarfile
import zipfile
from pathlib import Path

import pytest


def _verifier():
    path = Path(__file__).resolve().parents[1] / "tools/verify_release_tarball.py"
    spec = importlib.util.spec_from_file_location("verify_release_tarball_zip_prefix", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("descendant", ["a/b", "a/"])
def test_zip_regular_file_cannot_be_directory_parent(tmp_path, descendant):
    zipped = tmp_path / "sealed_bundle.zip"
    tarred = tmp_path / "sealed_bundle.tar.gz"
    files = [("a", b"file\n")]
    with zipfile.ZipFile(zipped, "w") as archive:
        archive.writestr("a", b"file\n")
        archive.writestr(descendant, b"child\n" if not descendant.endswith("/") else b"")
    if not descendant.endswith("/"):
        files.append((descendant, b"child\n"))
    with tarfile.open(tarred, "w:gz") as archive:
        for name, data in files:
            info = tarfile.TarInfo("sealed_bundle/" + name)
            info.mode = 0o644
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    assert any("sealed ZIP file/directory collision" in problem
               for problem in _verifier().check(tarred, zipped))
