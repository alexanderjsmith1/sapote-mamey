"""Tarball verification must refuse duplicate member names."""
import io
import hashlib
import json
import subprocess
import sys
import tarfile
import warnings
import zipfile
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "verify_release_tarball.py"
TOP = "fixture"


def _run(tmp_path, tar_members, zip_members, *, receipt_sha=None,
         receipt_status="SEALED_LOCAL_CODE", receipt_schema="sapote-mamey.local-code-seal.v1",
         tar_name=TOP, zip_name=TOP):
    tar = tmp_path / f"{tar_name}.tar.gz"
    with tarfile.open(tar, "w:gz") as t:
        for name, data in tar_members:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))
    zp = tmp_path / f"{zip_name}.zip"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(zp, "w") as z:
            for name, data in zip_members:
                z.writestr(name, data)
    receipt = tmp_path / "SEAL_RECEIPT.json"
    receipt.write_text(json.dumps({
        "schema": receipt_schema, "status": receipt_status, "tier": "CODE",
        "archive": {"path": zp.name,
                    "sha256": receipt_sha or hashlib.sha256(zp.read_bytes()).hexdigest(),
                    "bytes": zp.stat().st_size},
    }))
    return subprocess.run(
        [sys.executable, str(TOOL), str(tar), "--zip", str(zp),
         "--seal-receipt", str(receipt)],
        capture_output=True, text=True,
    )


def test_changed_then_expected_duplicate_tar_member_refuses(tmp_path):
    r = _run(tmp_path, [(f"{TOP}/AGENTS.md", b"changed"),
                        (f"{TOP}/AGENTS.md", b"expected")],
             [("AGENTS.md", b"expected")])
    assert r.returncode == 2
    assert "duplicate tar member name" in r.stdout


def test_identical_duplicate_tar_member_refuses(tmp_path):
    r = _run(tmp_path, [(f"{TOP}/AGENTS.md", b"expected"),
                        (f"{TOP}/AGENTS.md", b"expected")],
             [("AGENTS.md", b"expected")])
    assert r.returncode == 2
    assert "duplicate tar member name" in r.stdout


def test_duplicate_sealed_zip_member_refuses(tmp_path):
    r = _run(tmp_path, [(f"{TOP}/AGENTS.md", b"expected")],
             [("AGENTS.md", b"changed"), ("AGENTS.md", b"expected")])
    assert r.returncode == 2
    assert "duplicate sealed ZIP member name" in r.stdout


def test_unique_members_pass(tmp_path):
    r = _run(tmp_path, [(f"{TOP}/AGENTS.md", b"expected")],
             [("AGENTS.md", b"expected")])
    assert r.returncode == 0, r.stdout + r.stderr


def test_supplied_zip_must_match_seal_receipt_sha(tmp_path):
    r = _run(tmp_path, [(f"{TOP}/AGENTS.md", b"expected")],
             [("AGENTS.md", b"expected")], receipt_sha="0" * 64)
    assert r.returncode == 2
    assert "supplied ZIP SHA-256 differs from seal receipt" in r.stdout


def test_unsealed_receipt_refuses_even_with_identical_files(tmp_path):
    r = _run(tmp_path, [(f"{TOP}/AGENTS.md", b"expected")],
             [("AGENTS.md", b"expected")], receipt_status="DRAFT")
    assert r.returncode == 2
    assert "sealed local CODE tier" in r.stdout


def test_unrecognized_receipt_schema_refuses(tmp_path):
    r = _run(tmp_path, [(f"{TOP}/AGENTS.md", b"expected")],
             [("AGENTS.md", b"expected")], receipt_schema="other")
    assert r.returncode == 2
    assert "seal receipt schema" in r.stdout


def test_tarball_bundle_name_must_match_sealed_zip(tmp_path):
    r = _run(tmp_path, [("wrong_bundle/AGENTS.md", b"expected")],
             [("AGENTS.md", b"expected")],
             tar_name="wrong_bundle", zip_name="sealed_bundle")
    assert r.returncode == 2
    assert "tarball bundle name" in r.stdout
