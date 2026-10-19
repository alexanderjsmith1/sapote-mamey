"""Synthetic tarball routes work with GNU checksums and no shasum on PATH."""
from pathlib import Path
import hashlib
import importlib.util
import os
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
from ._python_fixture_launcher import write_python_fixture


def _path(tmp_path, checksum=True):
    bindir = tmp_path / "selected bin"
    bindir.mkdir()
    for name in ("bash", "mkdir", "tar", "cut", "dirname", "basename", "mktemp", "rm", "awk", "cat", "gzip"):
        found = shutil.which(name)
        assert found, f"fixture requires {name}"
        (bindir / name).symlink_to(found)
    if checksum:
        real = shutil.which("sha256sum")
        if real:
            (bindir / "sha256sum").symlink_to(real)
        else:
            # macOS simulation of the small coreutils CLI surface used by these routes.
            # Linux hosts use their actual sha256sum executable above.
            write_python_fixture(bindir / "sha256sum", r"""import hashlib,sys
from pathlib import Path
args=[a for a in sys.argv[1:] if a != '--']
if args[0]=='-c':
    digest,name=Path(args[1]).read_text().rstrip('\n').split('  ',1)
    ok=hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest
    sys.stdout.write(name+(': OK\n' if ok else ': FAILED\n'))
    raise SystemExit(0 if ok else 1)
p=Path(args[0]);sys.stdout.write(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p)+'\n')
""")
    env = dict(os.environ, PATH=str(bindir), PYTHON=sys.executable, TMPDIR=str(tmp_path), PYTHONDONTWRITEBYTECODE="1")
    return env


def test_producer_works_without_shasum_and_preserves_spaced_sidecar(tmp_path):
    source = tmp_path / "synthetic bundle"
    source.mkdir()
    (source / "BUILD_STAMP.txt").write_text("synthetic fixture\n")
    (source / "SOURCE_CHECKSUMS_SHA256.txt").write_text("")
    out = tmp_path / "synthetic output"
    env = _path(tmp_path)
    assert shutil.which("shasum", path=env["PATH"]) is None
    r = subprocess.run([shutil.which("bash"), str(ROOT / "tools/make_release_tarball.sh"), str(source), str(out)],
                       env=env, text=True, capture_output=True, timeout=30)
    assert r.returncode == 0, r.stdout + r.stderr
    artifact = out / (source.name + ".tar.gz")
    sidecar = artifact.with_name(artifact.name + ".sha256")
    digest, name = sidecar.read_text().rstrip("\n").split("  ", 1)
    assert digest == hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert name == artifact.name


def test_verified_route_works_without_shasum(tmp_path):
    spec = importlib.util.spec_from_file_location("verified_fixture", ROOT / "tests/test_442_make_verified_code_tarball_codex.py")
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    source, sealed_zip, receipt, out = fixture._inputs(tmp_path)
    result = fixture._route(source, sealed_zip, receipt, out, env=_path(tmp_path))
    assert result.returncode == 0, result.stdout + result.stderr
    artifact = out / (source.name + ".tar.gz")
    assert artifact.exists()
    assert artifact.with_name(artifact.name + ".sha256").read_text().split()[0] == hashlib.sha256(artifact.read_bytes()).hexdigest()


@pytest.mark.parametrize("script", ["make_release_tarball.sh", "make_verified_code_tarball.sh"])
def test_missing_checksum_tools_refuses_before_artifacts(tmp_path, script):
    source = tmp_path / "synthetic bundle"; source.mkdir()
    (source / "BUILD_STAMP.txt").write_text("fixture\n")
    (source / "SOURCE_CHECKSUMS_SHA256.txt").write_text("")
    sealed = tmp_path / "fixture.zip"; sealed.write_bytes(b"fixture only")
    receipt = tmp_path / "receipt.json"; receipt.write_text("{}")
    out = tmp_path / "output"
    args = [str(source), str(out)]
    if script == "make_verified_code_tarball.sh": args += [str(sealed), str(receipt)]
    result = subprocess.run([shutil.which("bash"), str(ROOT / "tools" / script), *args],
                            env=_path(tmp_path, checksum=False), text=True, capture_output=True, timeout=30)
    assert result.returncode == 2
    assert "sha256sum or shasum required" in result.stderr
    assert not out.exists()
