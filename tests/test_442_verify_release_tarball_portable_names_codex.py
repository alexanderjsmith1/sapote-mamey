"""Distinct archive names must not alias on common case/Unicode-folding filesystems."""
import importlib.util
import io
from pathlib import Path
import tarfile
import zipfile

import pytest


def _verifier():
    path = Path(__file__).resolve().parents[1] / "tools/verify_release_tarball.py"
    spec = importlib.util.spec_from_file_location("verify_release_tarball_portable_names", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("first,second", [
    ("a", "A"),
    ("é", "e\u0301"),
    ("A/x", "a/y"),
])
def test_sealed_zip_portable_path_alias_is_refused(tmp_path, first, second):
    zipped = tmp_path / "sealed_bundle.zip"
    tarred = tmp_path / "sealed_bundle.tar.gz"
    files = [(first, b"first"), (second, b"second")]
    with zipfile.ZipFile(zipped, "w") as archive:
        for name, data in files:
            archive.writestr(name, data)
    with tarfile.open(tarred, "w:gz") as archive:
        for name, data in files:
            info = tarfile.TarInfo("sealed_bundle/" + name)
            info.mode = 0o644
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    assert any("portable sealed ZIP path alias" in reason
               for reason in _verifier().check(tarred, zipped))
