"""An archive appearing during staging must survive export publication."""
import importlib.util
from pathlib import Path

import pytest

import mamey.project_catalog as pc

_spec = importlib.util.spec_from_file_location(
    "handoff_source_fixture", Path(__file__).with_name("test_458_project_handoff_export_no_overwrite.py"))
_fixture = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fixture)


def test_archive_created_during_staging_is_preserved(tmp_path, monkeypatch):
    source = _fixture._source(tmp_path)
    output = tmp_path / "handoff.zip"
    original_dumps = pc.json.dumps

    def competing_publication(value, *args, **kwargs):
        if isinstance(value, dict) and value.get("schema") == pc.HANDOFF_SCHEMA:
            output.write_bytes(b"other completed handoff")
        return original_dumps(value, *args, **kwargs)

    monkeypatch.setattr(pc.json, "dumps", competing_publication)
    with pytest.raises(ValueError, match="already exists"):
        pc.export_private_project_handoff(source, output)
    assert output.read_bytes() == b"other completed handoff"
    assert not list(tmp_path.glob(".handoff.zip.*"))
