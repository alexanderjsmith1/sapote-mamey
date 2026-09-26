"""Reject tar member counts impossible for the sealed ZIP before scanning the tail."""
import importlib.util
import io
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOP = "sapote-mamey-vX-CODE-fixture"


def test_impossible_tar_member_count_stops_before_unbounded_tail(tmp_path, monkeypatch):
    zip_path = tmp_path / f"{TOP}.zip"
    tar_path = tmp_path / f"{TOP}.tar.gz"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("payload.bin", b"good")
    with tarfile.open(tar_path, "w:gz") as archive:
        for name, data in [(f"{TOP}/payload.bin", b"good")] + [
            (f"{TOP}/._junk_{n}", b"x") for n in range(20)
        ]:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    spec = importlib.util.spec_from_file_location("verify_release_tarball_member_bound_probe", ROOT / "tools/verify_release_tarball.py")
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    original_iter = tarfile.TarFile.__iter__

    def guarded_iter(self):
        for index, member in enumerate(original_iter(self), 1):
            if index > 4:  # one sealed file + root allowance + one diagnostic extra
                raise AssertionError("verifier kept scanning an impossible tar tail")
            yield member

    monkeypatch.setattr(tarfile.TarFile, "__iter__", guarded_iter)
    problems = tool.check(tar_path, zip_path)
    assert any("member count exceeds sealed ZIP allowance" in p for p in problems)
