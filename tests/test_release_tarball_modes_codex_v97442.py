"""Release archives must not change safe extraction permissions while retaining bytes."""

import importlib.util
import io
import tarfile
import zipfile
from pathlib import Path

import pytest


def _verifier():
    path = Path(__file__).resolve().parents[1] / "tools" / "verify_release_tarball.py"
    spec = importlib.util.spec_from_file_location("verify_release_tarball_modes", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _archives(tmp_path, *, file_mode=0o644, directory_mode=0o755):
    zipped = tmp_path / "sealed_bundle.zip"
    tarred = tmp_path / "sealed_bundle.tar.gz"
    with zipfile.ZipFile(zipped, "w") as z:
        z.writestr("tools/runner.sh", b"#!/bin/sh\nexit 0\n")
    with tarfile.open(tarred, "w:gz") as t:
        directory = tarfile.TarInfo("sealed_bundle/tools")
        directory.type = tarfile.DIRTYPE
        directory.mode = directory_mode
        t.addfile(directory)
        content = b"#!/bin/sh\nexit 0\n"
        member = tarfile.TarInfo("sealed_bundle/tools/runner.sh")
        member.size = len(content)
        member.mode = file_mode
        t.addfile(member, io.BytesIO(content))
    return tarred, zipped


@pytest.mark.parametrize("mode", [0o666, 0o4755, 0o000])
def test_unsafe_regular_file_mode_refused_even_when_bytes_match(tmp_path, mode):
    tarred, zipped = _archives(tmp_path, file_mode=mode)
    assert any("unsafe file mode" in issue for issue in _verifier().check(tarred, zipped))


@pytest.mark.parametrize("mode", [0o777, 0o000])
def test_unsafe_directory_mode_refused(tmp_path, mode):
    tarred, zipped = _archives(tmp_path, directory_mode=mode)
    assert any("unsafe directory mode" in issue for issue in _verifier().check(tarred, zipped))


@pytest.mark.parametrize("mode", [0o644, 0o755])
def test_safe_file_and_directory_modes_pass(tmp_path, mode):
    tarred, zipped = _archives(tmp_path, file_mode=mode)
    assert _verifier().check(tarred, zipped) == []
