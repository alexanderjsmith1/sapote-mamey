"""`deliverables availability` needs a real ZIP for an antiSMASH-ZIP requirement.

Any regular file used to count, so `--input-zip README.md` reported `C01: READY`.
"""
from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

from mamey.deliverables_registry import _requirement_available

BUNDLE = Path(__file__).resolve().parents[1]


def _avail(path):
    return _requirement_available("antismash_zip", package=None, runs_dir=None,
                                  input_zip=str(path), locus=None)


def test_a_markdown_file_is_not_an_antismash_zip(tmp_path):
    md = tmp_path / "notes.md"
    md.write_text("# not a zip\n", encoding="utf-8")
    assert _avail(md) is False


def test_a_zip_archive_counts_and_a_missing_path_does_not(tmp_path):
    z = tmp_path / "EXAMPLE.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("EXAMPLE.region001.gbk", "LOCUS x\n")
    assert _avail(z) is True
    assert _avail(tmp_path / "missing.zip") is False


def test_the_command_does_not_say_ready_for_a_markdown_file(tmp_path):
    md = tmp_path / "notes.md"
    md.write_text("# not a zip\n", encoding="utf-8")
    out = subprocess.run([sys.executable, "mamey_run.py", "deliverables", "availability", "#1",
                          "--input-zip", str(md)], cwd=BUNDLE, capture_output=True, text=True,
                         timeout=120).stdout
    assert "C01: READY" not in out
    assert "C01: INPUT_OR_LOCAL_DEPENDENCY_REQUIRED" in out


def _real(tmp_path):
    z = tmp_path / "EXAMPLE.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("EXAMPLE.region001.gbk", "LOCUS x\n")
    return z


def test_zip_shaped_files_that_are_not_antismash_results_do_not_count(tmp_path):
    good = _real(tmp_path)
    empty = tmp_path / "empty.zip"
    zipfile.ZipFile(empty, "w").close()
    eocd = tmp_path / "eocd.zip"
    eocd.write_bytes(b"PK\x05\x06" + b"\x00" * 18)
    xlsx = tmp_path / "book.xlsx"
    with zipfile.ZipFile(xlsx, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
    png = tmp_path / "image.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"junk" * 50 + good.read_bytes())
    corrupt = tmp_path / "corrupt.zip"
    data = bytearray(good.read_bytes())
    data[40:60] = b"\x00" * 20
    corrupt.write_bytes(bytes(data))
    for path in (empty, eocd, xlsx, png, corrupt, tmp_path):
        assert _avail(path) is False, path
    renamed = tmp_path / "renamed.dat"
    renamed.write_bytes(good.read_bytes())
    assert _avail(renamed) is True
