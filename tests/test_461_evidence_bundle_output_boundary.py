"""Post-seal reader outputs must stay outside the source package."""
import importlib.util
from pathlib import Path
import pytest

_SPEC = importlib.util.spec_from_file_location("eb461out", Path(__file__).resolve().parents[1] / "tools/evidence_bundle.py")
eb = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(eb)


@pytest.mark.parametrize("destination", ["same", "child", "symlink"])
def test_source_package_output_is_refused_without_writes(tmp_path, destination):
    source = tmp_path / "source package"; source.mkdir()
    (source / "sentinel.txt").write_text("preserve original bytes\n")
    bundle = {"strain": "PUBLIC", "package_dir": str(source), "bgc_count": 0, "bgcs": {}}
    out = source if destination == "same" else source / "reports"
    if destination == "symlink":
        out = tmp_path / "source alias"; out.symlink_to(source, target_is_directory=True)
    before = {str(p.relative_to(source)): p.read_bytes() for p in source.rglob("*") if p.is_file()}
    with pytest.raises(ValueError, match="EVIDENCE_OUTPUT_INSIDE_SOURCE"):
        eb.write_evidence_bundle(bundle, out)
    after = {str(p.relative_to(source)): p.read_bytes() for p in source.rglob("*") if p.is_file()}
    assert after == before
    assert not (source / "reports").exists()


def test_external_output_with_spaces_is_supported(tmp_path):
    source = tmp_path / "source package"; source.mkdir()
    bundle = {"strain": "PUBLIC", "package_dir": str(source), "bgc_count": 0, "bgcs": {}}
    out = tmp_path / "reader output"
    result = eb.write_evidence_bundle(bundle, out)
    assert (out / result["json"]).is_file()
    assert list(source.iterdir()) == []


def test_cli_refuses_source_output_cleanly(tmp_path, monkeypatch, capsys):
    source = tmp_path / "source package"; source.mkdir()
    bundle = {"strain": "PUBLIC", "package_dir": str(source), "bgc_count": 0, "bgcs": {}}
    monkeypatch.setattr(eb, "build_evidence_bundle", lambda *args: bundle)
    assert eb.main([str(source), "--out", str(source)]) == 2
    assert "EVIDENCE_OUTPUT_INSIDE_SOURCE" in capsys.readouterr().err
    assert list(source.iterdir()) == []
