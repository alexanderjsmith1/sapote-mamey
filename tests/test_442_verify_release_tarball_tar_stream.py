"""The verifier must not preload a tarball's entire member table."""
import importlib.util
import io
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOP = "sapote-mamey-vX-CODE-fixture"


def test_tar_header_iteration_does_not_getmembers(tmp_path, monkeypatch):
    zip_path = tmp_path / f"{TOP}.zip"
    tar_path = tmp_path / f"{TOP}.tar.gz"
    data = b"abc" * 400_000
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("payload.bin", data)
    with tarfile.open(tar_path, "w:gz") as archive:
        info = tarfile.TarInfo(f"{TOP}/payload.bin")
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))
    spec = importlib.util.spec_from_file_location("verify_release_tarball_tar_stream_probe", ROOT / "tools/verify_release_tarball.py")
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)

    def forbidden_getmembers(self):
        raise AssertionError("getmembers preloads every tar header")

    monkeypatch.setattr(tarfile.TarFile, "getmembers", forbidden_getmembers)
    assert tool.check(tar_path, zip_path) == []
