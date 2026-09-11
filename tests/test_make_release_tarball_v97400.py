"""Regression for tools/make_release_tarball.sh (v9.7.400): a sealed-looking directory yields
a .tar.gz + .sha256 pair whose digest matches; an unsealed-looking directory is REFUSED (exit 2)
before any archive is written. Fixture is synthetic; nothing outside tmp_path is touched."""
from __future__ import annotations

import hashlib
import os
import subprocess

TOOL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "tools", "make_release_tarball.sh")


def _run(*args):
    return subprocess.run(["bash", TOOL, *args], capture_output=True, text=True, timeout=120)


def test_sealed_dir_yields_matching_tarball_and_sha(tmp_path):
    src = tmp_path / "sapote-mamey-v0.0.0-CODE-testseal"
    src.mkdir()
    (src / "BUILD_STAMP.txt").write_text("version=0.0.0\n")
    (src / "SOURCE_CHECKSUMS_SHA256.txt").write_text("")
    (src / "mamey_run.py").write_text("# stub\n")
    out = tmp_path / "dist"
    r = _run(str(src), str(out))
    assert r.returncode == 0, r.stderr
    tarball = out / (src.name + ".tar.gz")
    sha_file = out / (src.name + ".tar.gz.sha256")
    assert tarball.is_file() and sha_file.is_file()
    digest = hashlib.sha256(tarball.read_bytes()).hexdigest()
    assert sha_file.read_text().split()[0] == digest, "sha256 sidecar must match the tarball"


def test_spaced_outdir_sidecar_verifies_with_shasum_c(tmp_path):
    """BC4 seal-gate finding: the sidecar must survive `shasum -c` when the outdir path
    contains a space (the workspace's release folders do). Relative-name sidecar required."""
    src = tmp_path / "sapote-mamey-v0.0.0-CODE-testseal"
    src.mkdir()
    (src / "BUILD_STAMP.txt").write_text("version=0.0.0\n")
    (src / "SOURCE_CHECKSUMS_SHA256.txt").write_text("")
    out = tmp_path / "Sapote Mamey dist"
    r = _run(str(src), str(out))
    assert r.returncode == 0, r.stderr
    sha_file = out / (src.name + ".tar.gz.sha256")
    recorded = sha_file.read_text().split(None, 1)[1].strip()
    assert recorded == src.name + ".tar.gz", (
        "sidecar must record the RELATIVE tarball name (space-safe, portable): %r" % recorded)
    chk = subprocess.run(["shasum", "-c", sha_file.name], cwd=str(out),
                         capture_output=True, text=True, timeout=120)
    assert chk.returncode == 0, "shasum -c must verify the sidecar in place: " + chk.stdout + chk.stderr


def test_unsealed_dir_is_refused_with_no_artifact(tmp_path):
    src = tmp_path / "not-a-bundle"
    src.mkdir()
    (src / "random.txt").write_text("x")
    out = tmp_path / "dist"
    r = _run(str(src), str(out))
    assert r.returncode == 2, "unsealed-looking tree must be REFUSED (exit 2)"
    assert "REFUSED" in r.stderr
    assert not (out / (src.name + ".tar.gz")).exists()
