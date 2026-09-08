"""v9.7.198 F3 — the .197 suffix-strip keying works; the bug was that no automated path supplied the
source ZIP to domain-level, so every delivered module summary read 0. Resolver: explicit > manifest
input_zip > basename-beside-package > None (honest 0)."""
import json
import tempfile
from pathlib import Path

from mamey.render_all_figures import _resolve_source_zip

_ZIP = "/mnt/user-data/uploads/AS-421_loose.zip"
import os
_HAVE = os.path.exists(_ZIP)


def test_no_input_zip_returns_none():
    d = Path(tempfile.mkdtemp())
    (d / "manifest.json").write_text(json.dumps({}))
    assert _resolve_source_zip(d) is None  # honest 0, no crash


def test_missing_manifest_returns_none():
    assert _resolve_source_zip(Path(tempfile.mkdtemp())) is None


import pytest
@pytest.mark.skipif(not _HAVE, reason="AS-421 zip absent")
def test_manifest_input_zip_resolves():
    d = Path(tempfile.mkdtemp())
    (d / "manifest.json").write_text(json.dumps({"input_zip": _ZIP}))
    assert _resolve_source_zip(d) == _ZIP


@pytest.mark.skipif(not _HAVE, reason="AS-421 zip absent")
def test_explicit_override():
    d = Path(tempfile.mkdtemp())
    assert _resolve_source_zip(d, _ZIP) == _ZIP
