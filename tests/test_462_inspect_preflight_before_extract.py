"""DREL-047: inspect never recommends extracting a package ZIP with an unsafe member."""
import argparse
import json
import zipfile

import pytest

from mamey.package_inspector import inspect_command
from mamey.ziputil import safe_extract_all

MANIFEST = {"workflow_version": "Mamey v1.0", "strain_id": "SYN-1", "bgcs": [], "bgc_counts": {}}


def _package_zip(path, extra=()):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("SYN-1/manifest.json", json.dumps(MANIFEST))
        z.writestr("SYN-1/OPEN_ME_FIRST.html", "<html></html>")
        for name in extra:
            z.writestr(name, "x")
    return path


def test_safe_package_is_recognized_with_extraction_advice(tmp_path, capsys):
    zp = _package_zip(tmp_path / "pkg.zip")
    assert inspect_command(argparse.Namespace(zip=str(zp))) == 0
    assert "Extract the ZIP" in capsys.readouterr().out


def test_traversal_member_blocks_extraction_advice(tmp_path, capsys):
    zp = _package_zip(tmp_path / "pkg.zip", extra=("../outside.txt",))
    before = zp.read_bytes()
    assert inspect_command(argparse.Namespace(zip=str(zp))) == 1
    captured = capsys.readouterr()
    assert "DO NOT EXTRACT" in captured.err
    assert "Extract the ZIP" not in captured.out
    assert zp.read_bytes() == before
    assert not (tmp_path / "outside.txt").exists()


def test_dry_run_writes_nothing_and_still_refuses(tmp_path):
    zp = _package_zip(tmp_path / "pkg.zip", extra=("../outside.txt",))
    dest = tmp_path / "dest"
    with zipfile.ZipFile(zp) as z:
        with pytest.raises(ValueError, match="unsafe zip member path"):
            safe_extract_all(z, dest, dry_run=True)
    assert not dest.exists()


def test_dry_run_on_safe_archive_writes_nothing(tmp_path):
    zp = _package_zip(tmp_path / "pkg.zip")
    dest = tmp_path / "dest"
    with zipfile.ZipFile(zp) as z:
        safe_extract_all(z, dest, dry_run=True)
    assert not dest.exists()
