from pathlib import Path
from types import SimpleNamespace
import pytest
from tools import reference_bgc_structural_validator as mod

@pytest.mark.parametrize("destination", ["output", "failure_output"])
def test_structural_validator_cannot_replace_source_zip(tmp_path, monkeypatch, destination):
    archive = tmp_path / "source.zip"
    archive.write_bytes(b"source evidence")
    manifest = tmp_path / "manifest.tsv"
    manifest.write_text("synthetic")
    monkeypatch.setattr(mod, "load_reference_manifest", lambda *args: [SimpleNamespace(source_zip="source.zip")])
    monkeypatch.setattr(mod, "_load_engine", lambda: pytest.fail("engine must not load before path admission"))
    output = archive if destination == "output" else tmp_path / "table.csv"
    failure = archive if destination == "failure_output" else tmp_path / "holds.tsv"
    assert mod.run_panel(manifest, tmp_path, output, failure) == 2
    assert archive.read_bytes() == b"source evidence"
