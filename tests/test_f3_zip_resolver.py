from tests._uploads_fixture import UPLOADS as _UPLOADS, OUTPUTS as _OUTPUTS  # v9.7.416
"""F3 source-ZIP routing controls.

Resolver order is explicit > manifest locator > portable basename fallback. Any
resolved bytes are content-bound to manifest input_zip_sha256; unavailable bytes
route to the domain-level producer's separately receipted LIMITED mode.
"""
import json
import hashlib
import tempfile
from pathlib import Path

from mamey.render_all_figures import _resolve_source_zip

_ZIP = (_UPLOADS + "/AS-421_loose.zip")
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
    digest = hashlib.sha256(Path(_ZIP).read_bytes()).hexdigest()
    (d / "manifest.json").write_text(json.dumps({"input_zip": _ZIP, "input_zip_sha256": digest}))
    assert _resolve_source_zip(d) == _ZIP


@pytest.mark.skipif(not _HAVE, reason="AS-421 zip absent")
def test_explicit_override():
    d = Path(tempfile.mkdtemp())
    digest = hashlib.sha256(Path(_ZIP).read_bytes()).hexdigest()
    (d / "manifest.json").write_text(json.dumps({"input_zip": _ZIP, "input_zip_sha256": digest}))
    assert _resolve_source_zip(d, _ZIP) == _ZIP
