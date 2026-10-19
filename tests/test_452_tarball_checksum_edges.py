"""Native synthetic checksum fallback and refusal checks for both tarball routes."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from . import test_452_linux_tarball_checksum as checksum_fixture
from . import test_442_make_verified_code_tarball_codex as verified_fixture
from ._python_fixture_launcher import write_python_fixture

ROOT = Path(__file__).resolve().parents[1]


def _run(source, sealed_zip, receipt, out, env, verified):
    name = "make_verified_code_tarball.sh" if verified else "make_release_tarball.sh"
    args = [str(source), str(out)]
    if verified:
        args += [str(sealed_zip), str(receipt)]
    return subprocess.run([shutil.which("bash"), str(ROOT / "tools" / name), *args],
                          env=env, capture_output=True, text=True, timeout=30)


@pytest.mark.parametrize("verified", [False, True], ids=["producer", "verified"])
@pytest.mark.parametrize("force_fixture", [False, True], ids=["available-provider", "fixture-provider"])
def test_shasum_interface_only_fallback_delivers_digest_bound_pair(tmp_path, verified, force_fixture):
    source, sealed_zip, receipt, out = verified_fixture._inputs(tmp_path)
    env = checksum_fixture._path(tmp_path, checksum=False)
    native = None if force_fixture else shutil.which("shasum")
    if native:
        (Path(env["PATH"]) / "shasum").symlink_to(native)
    else:
        # The fallback contract can be checked on GNU-only hosts without Perl.
        body = r'''import hashlib,sys
from pathlib import Path
args=sys.argv[1:]
assert args[:2]==['-a','256']
args=[a for a in args[2:] if a!='--']
if args[0]=='-c':
    digest,name=Path(args[1]).read_text().rstrip('\n').split('  ',1)
    ok=hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest
    raise SystemExit(0 if ok else 1)
p=Path(args[0]);sys.stdout.write(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p)+'\n')
'''
        write_python_fixture(Path(env["PATH"]) / "shasum", body)
    assert shutil.which("sha256sum", path=env["PATH"]) is None
    result = _run(source, sealed_zip, receipt, out, env, verified)
    assert result.returncode == 0, result.stdout + result.stderr
    archive = out / (source.name + ".tar.gz")
    sidecar = archive.with_name(archive.name + ".sha256")
    digest, name = sidecar.read_text().rstrip("\n").split("  ", 1)
    assert digest == hashlib.sha256(archive.read_bytes()).hexdigest()
    assert name == archive.name


@pytest.mark.parametrize("verified", [False, True], ids=["producer", "verified"])
def test_selected_sha256sum_failure_never_falls_back_to_another_provider(tmp_path, verified):
    source, sealed_zip, receipt, out = verified_fixture._inputs(tmp_path)
    env = checksum_fixture._path(tmp_path, checksum=False)
    bindir = Path(env["PATH"])
    marker = tmp_path / "unexpected fallback"
    write_python_fixture(bindir / "sha256sum", "raise SystemExit(9)\n")
    write_python_fixture(bindir / "shasum", "from pathlib import Path\nPath(" + repr(str(marker)) + ").write_text('called')\nraise SystemExit(7)\n")
    result = _run(source, sealed_zip, receipt, out, env, verified)
    assert result.returncode != 0, result.stdout + result.stderr
    assert not marker.exists(), "a failing selected checksum provider must not silently change"
    if verified:
        assert not out.exists(), "failed production cannot publish a verified pair"


@pytest.mark.parametrize("force_fixture", [False, True], ids=["available-provider", "fixture-provider"])
def test_failed_sidecar_check_refuses_before_verified_publication(tmp_path, force_fixture):
    source, sealed_zip, receipt, out = verified_fixture._inputs(tmp_path)
    env = checksum_fixture._path(tmp_path, checksum=False)
    native = None if force_fixture else shutil.which("sha256sum")
    body = ("import os,sys,hashlib\nfrom pathlib import Path\n"
            "if '-c' in sys.argv[1:]: raise SystemExit(9)\n")
    if native:
        body += "native=" + repr(native) + "\nos.execv(native, [native, *sys.argv[1:]])\n"
    else:
        body += "args=[a for a in sys.argv[1:] if a!='--']\np=Path(args[0])\nsys.stdout.write(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p)+'\\n')\n"
    write_python_fixture(Path(env["PATH"]) / "sha256sum", body)
    result = _run(source, sealed_zip, receipt, out, env, True)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "SHA-256 sidecar failed" in result.stderr
    assert not out.exists(), "a failed checksum verification cannot publish either name"
