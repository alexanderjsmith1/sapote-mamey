"""Regression coverage for malformed package metadata and optional version probing."""

from __future__ import annotations

import argparse
import json
import zipfile

import pytest

from mamey.package_addons import write_open_me_first
from mamey.package_inspector import inspect_command


def test_open_me_first_preserves_missing_optional_metadata_fallback(tmp_path):
    """Both optional metadata files may legitimately be unavailable."""
    output = write_open_me_first(tmp_path)

    assert output.exists()
    assert "Mamey Package" in output.read_text(encoding="utf-8")


def test_open_me_first_accepts_valid_metadata(tmp_path):
    """Valid metadata remains rendered rather than treated as an error."""
    (tmp_path / "manifest.json").write_text(json.dumps({"strain_id": "GENERIC-TEST"}), encoding="utf-8")

    output = write_open_me_first(tmp_path)

    assert "GENERIC-TEST" in output.read_text(encoding="utf-8")


def test_open_me_first_rejects_malformed_manifest_instead_of_rendering_absent_metadata(tmp_path):
    """A present-but-invalid manifest is not equivalent to an unavailable optional file."""
    (tmp_path / "manifest.json").write_text("{ malformed", encoding="utf-8")

    with pytest.raises(ValueError, match="manifest.json is unreadable"):
        write_open_me_first(tmp_path)


def test_inspect_warns_when_optional_version_fallback_cannot_read_metadata(tmp_path, monkeypatch):
    """Missing version remains allowed; a failing fallback is surfaced as a warning."""
    archive = tmp_path / "input.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("NODE_1.region001.gbk", "LOCUS       NODE_1\\n")

    import mamey.parsers as parsers
    monkeypatch.setattr(parsers, "extract_antismash_version",
                        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("metadata unreadable")))

    with pytest.warns(RuntimeWarning, match="ANTISMASH_VERSION_FALLBACK_UNAVAILABLE"):
        assert inspect_command(argparse.Namespace(zip=str(archive))) == 0
