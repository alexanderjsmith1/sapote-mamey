"""A CODE tarball route must verify against a selected seal receipt before delivery."""
import hashlib
import json
import subprocess
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTE = ROOT / "tools/make_verified_code_tarball.sh"
PRODUCER = ROOT / "tools/make_release_tarball.sh"


def _inputs(tmp_path, extra=False, bad_receipt=False):
    name = "sapote-mamey-v0-CODE-fixture"
    source = tmp_path / name
    source.mkdir()
    files = {"BUILD_STAMP.txt": b"fixture\n", "SOURCE_CHECKSUMS_SHA256.txt": b"fixture\n",
             "mamey_run.py": b"# fixture\n"}
    for rel, data in files.items():
        (source / rel).write_bytes(data)
    sealed_zip = tmp_path / (name + ".zip")
    with zipfile.ZipFile(sealed_zip, "w") as archive:
        for rel, data in files.items():
            archive.writestr(rel, data)
    receipt = tmp_path / "SEAL_RECEIPT.json"
    receipt.write_text(json.dumps({"schema": "sapote-mamey.local-code-seal.v1",
                                   "status": "SEALED_LOCAL_CODE", "tier": "CODE",
                                   "archive": {"path": sealed_zip.name,
                                               "sha256": "0" * 64 if bad_receipt else hashlib.sha256(sealed_zip.read_bytes()).hexdigest(),
                                               "bytes": sealed_zip.stat().st_size}}))
    if extra:
        (source / "unsealed_extra.txt").write_text("extra\n")
    return source, sealed_zip, receipt, tmp_path / "dist"


def _route(source, sealed_zip, receipt, out):
    return subprocess.run(["bash", str(ROUTE), str(source), str(out), str(sealed_zip), str(receipt)],
                          capture_output=True, text=True, timeout=30)


def test_verified_code_route_delivers_matching_pair(tmp_path):
    source, sealed_zip, receipt, out = _inputs(tmp_path)
    result = _route(source, sealed_zip, receipt, out)
    assert result.returncode == 0, result.stdout + result.stderr
    archive = out / (source.name + ".tar.gz")
    sidecar = out / (source.name + ".tar.gz.sha256")
    assert archive.is_file() and sidecar.is_file()
    assert sidecar.read_text().split()[0] == hashlib.sha256(archive.read_bytes()).hexdigest()
    with tarfile.open(archive, "r:gz") as tar:
        assert source.name + "/mamey_run.py" in tar.getnames()


def test_verified_code_route_withholds_extra_source_file(tmp_path):
    source, sealed_zip, receipt, out = _inputs(tmp_path, extra=True)
    # The current generic producer can create a tarball and sidecar from this tree.
    direct = subprocess.run(["bash", str(PRODUCER), str(source), str(tmp_path / "direct")],
                            capture_output=True, text=True, timeout=30)
    assert direct.returncode == 0, direct.stdout + direct.stderr
    result = _route(source, sealed_zip, receipt, out)
    assert result.returncode == 2, result.stdout + result.stderr
    assert result.stdout == ""
    assert not (out / (source.name + ".tar.gz")).exists()
    assert not (out / (source.name + ".tar.gz.sha256")).exists()


def test_verified_code_route_withholds_bad_receipt(tmp_path):
    source, sealed_zip, receipt, out = _inputs(tmp_path, bad_receipt=True)
    result = _route(source, sealed_zip, receipt, out)
    assert result.returncode == 2, result.stdout + result.stderr
    assert result.stdout == ""
    assert not (out / (source.name + ".tar.gz")).exists()
    assert not (out / (source.name + ".tar.gz.sha256")).exists()


def test_verified_code_route_does_not_overwrite_existing_pair(tmp_path):
    source, sealed_zip, receipt, out = _inputs(tmp_path)
    out.mkdir()
    archive = out / (source.name + ".tar.gz")
    sidecar = out / (source.name + ".tar.gz.sha256")
    archive.write_bytes(b"existing archive")
    sidecar.write_text("existing sidecar\n")
    result = _route(source, sealed_zip, receipt, out)
    assert result.returncode == 2, result.stdout + result.stderr
    assert result.stdout == ""
    assert archive.read_bytes() == b"existing archive"
    assert sidecar.read_text() == "existing sidecar\n"
