"""Tar directory members must belong to the receipt-bound ZIP tree."""

import importlib.util
import io
import tarfile
import zipfile
from pathlib import Path


def _verifier():
    path = Path(__file__).resolve().parents[1] / "tools" / "verify_release_tarball.py"
    spec = importlib.util.spec_from_file_location("verify_release_tarball_directories", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _archives(tmp_path, directory):
    zipped = tmp_path / "sealed_bundle.zip"
    tarred = tmp_path / "sealed_bundle.tar.gz"
    with zipfile.ZipFile(zipped, "w") as z:
        z.writestr("AGENTS.md", b"expected")
    with tarfile.open(tarred, "w:gz") as t:
        root = tarfile.TarInfo("sealed_bundle/")
        root.type = tarfile.DIRTYPE
        root.mode = 0o755
        t.addfile(root)
        member = tarfile.TarInfo("sealed_bundle/AGENTS.md")
        member.mode = 0o644
        member.size = len(b"expected")
        t.addfile(member, io.BytesIO(b"expected"))
        extra = tarfile.TarInfo(directory)
        extra.type = tarfile.DIRTYPE
        extra.mode = 0o755
        t.addfile(extra)
    return tarred, zipped


def test_directory_cannot_collide_with_a_sealed_regular_file(tmp_path):
    tarred, zipped = _archives(tmp_path, "sealed_bundle/AGENTS.md/.")
    assert any("directory collides with sealed file" in problem
               for problem in _verifier().check(tarred, zipped))


def test_untracked_empty_directory_is_refused(tmp_path):
    tarred, zipped = _archives(tmp_path, "sealed_bundle/untracked_empty/")
    assert any("untracked tar directory" in problem
               for problem in _verifier().check(tarred, zipped))


def test_empty_directory_explicitly_present_in_zip_is_allowed(tmp_path):
    zipped = tmp_path / "sealed_bundle.zip"
    tarred = tmp_path / "sealed_bundle.tar.gz"
    with zipfile.ZipFile(zipped, "w") as z:
        z.writestr("empty/", b"")
    with tarfile.open(tarred, "w:gz") as t:
        for name in ("sealed_bundle/", "sealed_bundle/empty/"):
            member = tarfile.TarInfo(name)
            member.type = tarfile.DIRTYPE
            member.mode = 0o755
            t.addfile(member)
    assert _verifier().check(tarred, zipped) == []
