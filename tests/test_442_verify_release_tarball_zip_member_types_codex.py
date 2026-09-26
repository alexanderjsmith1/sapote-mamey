"""ZIP member kinds must agree with the regular-file/directory tarball contract."""
import importlib.util
import io
from pathlib import Path
import stat
import tarfile
import zipfile

import pytest


def _verifier():
    path = Path(__file__).resolve().parents[1] / "tools/verify_release_tarball.py"
    spec = importlib.util.spec_from_file_location("verify_release_tarball_zip_types", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("kind", [stat.S_IFLNK, stat.S_IFIFO])
def test_zip_special_file_cannot_match_tar_regular_file(tmp_path, kind):
    zipped = tmp_path / "sealed_bundle.zip"
    tarred = tmp_path / "sealed_bundle.tar.gz"
    data = b"target.txt"
    member = zipfile.ZipInfo("link")
    member.create_system = 3
    member.external_attr = (kind | 0o777) << 16
    with zipfile.ZipFile(zipped, "w") as archive:
        archive.writestr(member, data)
    with tarfile.open(tarred, "w:gz") as archive:
        info = tarfile.TarInfo("sealed_bundle/link")
        info.mode = 0o644
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))
    assert any("non-regular sealed ZIP member" in reason
               for reason in _verifier().check(tarred, zipped))
