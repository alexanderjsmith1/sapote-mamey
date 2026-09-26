"""A sealed-looking directory basename must be handled as data, not tar options."""
import hashlib
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/make_release_tarball.sh"


def test_leading_dash_bundle_basename_is_not_tar_option(tmp_path):
    src = tmp_path / "-fixture"
    src.mkdir()
    (src / "BUILD_STAMP.txt").write_text("fixture\n")
    (src / "SOURCE_CHECKSUMS_SHA256.txt").write_text("fixture\n")
    (src / "payload.txt").write_text("payload\n")
    out = tmp_path / "dist"
    result = subprocess.run(["bash", str(TOOL), str(src), str(out)],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    archive = out / "-fixture.tar.gz"
    sidecar = out / "-fixture.tar.gz.sha256"
    assert archive.is_file() and sidecar.is_file()
    with tarfile.open(archive, "r:gz") as tar:
        assert "-fixture/payload.txt" in tar.getnames()
    assert sidecar.read_text().split()[0] == hashlib.sha256(archive.read_bytes()).hexdigest()
    check = subprocess.run(["shasum", "-c", "--", sidecar.name], cwd=out,
                           capture_output=True, text=True, timeout=30)
    assert check.returncode == 0, check.stdout + check.stderr
