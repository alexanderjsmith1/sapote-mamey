"""Member hashing must keep reads bounded for both archive formats."""
import importlib.util
import io
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOP = "sapote-mamey-vX-CODE-fixture"


def _tool():
    spec = importlib.util.spec_from_file_location("verify_release_tarball_stream_probe", ROOT / "tools/verify_release_tarball.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _archives(tmp_path):
    data = b"abc123" * 400_000
    zip_path = tmp_path / f"{TOP}.zip"
    tar_path = tmp_path / f"{TOP}.tar.gz"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("payload.bin", data)
    with tarfile.open(tar_path, "w:gz") as archive:
        info = tarfile.TarInfo(f"{TOP}/payload.bin")
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))
    return zip_path, tar_path


def test_zip_member_hash_uses_bounded_reads(tmp_path, monkeypatch):
    zip_path, _ = _archives(tmp_path)
    tool = _tool()
    calls = []
    original_open = zipfile.ZipFile.open

    def forbidden_whole_read(self, *args, **kwargs):
        raise AssertionError("ZipFile.read materializes a whole member")

    def guarded_open(self, *args, **kwargs):
        stream = original_open(self, *args, **kwargs)
        original_read = stream.read

        def guarded_read(size=-1):
            assert 0 < size <= 1024 * 1024
            calls.append(size)
            return original_read(size)

        stream.read = guarded_read
        return stream

    monkeypatch.setattr(zipfile.ZipFile, "read", forbidden_whole_read)
    monkeypatch.setattr(zipfile.ZipFile, "open", guarded_open)
    assert list(tool.zip_digests(zip_path)) == ["payload.bin"]
    assert len(calls) >= 3


def test_tar_member_hash_uses_bounded_reads(tmp_path, monkeypatch):
    zip_path, tar_path = _archives(tmp_path)
    tool = _tool()
    calls = []
    original_extractfile = tarfile.TarFile.extractfile

    def guarded_extractfile(self, *args, **kwargs):
        stream = original_extractfile(self, *args, **kwargs)
        original_read = stream.read

        def guarded_read(size=-1):
            assert 0 < size <= 1024 * 1024
            calls.append(size)
            return original_read(size)

        stream.read = guarded_read
        return stream

    monkeypatch.setattr(tarfile.TarFile, "extractfile", guarded_extractfile)
    assert tool.check(tar_path, zip_path) == []
    assert len(calls) >= 3
