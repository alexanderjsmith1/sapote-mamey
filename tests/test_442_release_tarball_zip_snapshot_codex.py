"""The receipt and tar member comparison must use one verified ZIP snapshot."""

import hashlib
import importlib.util
import io
import json
import tarfile
import zipfile
from pathlib import Path


def _verifier():
    path = Path(__file__).resolve().parents[1] / "tools" / "verify_release_tarball.py"
    spec = importlib.util.spec_from_file_location("verify_release_tarball_snapshot", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _zip(path, content):
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("AGENTS.md", content)


def test_zip_swap_after_receipt_check_cannot_change_comparison_input(tmp_path, monkeypatch, capsys):
    zipped = tmp_path / "sealed_bundle.zip"
    tarred = tmp_path / "sealed_bundle.tar.gz"
    receipt = tmp_path / "SEAL_RECEIPT.json"
    _zip(zipped, b"old")
    receipt.write_text(json.dumps({
        "schema": "sapote-mamey.local-code-seal.v1", "status": "SEALED_LOCAL_CODE",
        "tier": "CODE", "archive": {"path": zipped.name,
            "sha256": hashlib.sha256(zipped.read_bytes()).hexdigest(), "bytes": zipped.stat().st_size},
    }), encoding="utf-8")
    with tarfile.open(tarred, "w:gz") as archive:
        member = tarfile.TarInfo("sealed_bundle/AGENTS.md")
        member.mode = 0o644
        member.size = len(b"new")
        archive.addfile(member, io.BytesIO(b"new"))
    verifier = _verifier()
    original = verifier.check_seal_receipt

    def swap_original_after_receipt_check(path, sealed_zip):
        problems = original(path, sealed_zip)
        assert not problems
        _zip(zipped, b"new")
        return problems

    monkeypatch.setattr(verifier, "check_seal_receipt", swap_original_after_receipt_check)
    result = verifier.main([str(tarred), "--zip", str(zipped), "--seal-receipt", str(receipt)])
    assert result == 2
    assert "file(s) differ from the sealed ZIP" in capsys.readouterr().out
