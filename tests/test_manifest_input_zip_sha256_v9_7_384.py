"""v9.7.384 (GOLDENROD): manifest.json records input_zip_sha256.

Completes source-archive provenance: the sealed manifest already records
`input_zip` (the path, cli.py F3 v9.7.198), but not the content digest — so
duplicate detection / "which bytes went in" could not be answered from the
manifest alone. This adds `input_zip_sha256` next to `input_zip`.

Fail-before / pass-after: on the sealed base `mamey.cli._input_zip_sha256`
does not exist (AttributeError at collection), and no manifest carries the key.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from mamey import cli


def test_input_zip_sha256_matches_hashlib(tmp_path: Path):
    z = tmp_path / "AS-TEST.zip"
    data = b"not a real zip, just deterministic bytes to hash\n" * 100
    z.write_bytes(data)
    expected = hashlib.sha256(data).hexdigest()
    assert cli._input_zip_sha256(z) == expected           # accepts a Path
    assert cli._input_zip_sha256(str(z)) == expected       # ...and a str
    assert len(expected) == 64


def test_input_zip_sha256_is_none_when_unavailable():
    assert cli._input_zip_sha256("/no/such/file.zip") is None
    assert cli._input_zip_sha256("") is None
    assert cli._input_zip_sha256(None) is None


def test_input_zip_sha256_round_trips_through_manifest_json(tmp_path: Path):
    z = tmp_path / "AS-TEST.zip"
    z.write_bytes(b"abc123")
    manifest = {
        "input_zip": str(z),
        "input_zip_sha256": cli._input_zip_sha256(z),
    }
    reloaded = json.loads(json.dumps(manifest, indent=2))
    assert reloaded["input_zip_sha256"] == hashlib.sha256(b"abc123").hexdigest()
    # a matching digest across two packages proves same source bytes — nothing more.
    assert isinstance(reloaded["input_zip_sha256"], str)
