import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from contextlib import nullcontext
import pytest

spec = importlib.util.spec_from_file_location("atlas_binding_candidate", Path(__file__).resolve().parents[1] / "tools/build_siderophore_atlas.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

@pytest.mark.parametrize("census_first", [False, True])
def test_architecture_binding_cannot_be_skipped_by_config_order(tmp_path, monkeypatch, census_first):
    root = tmp_path / "output"
    root.mkdir()
    rules = root / "FAMILY_RULES.json"
    rules.write_text("{}")
    reader = tmp_path / "reader.py"
    reader.write_text("synthetic reader")
    handback = tmp_path / "handback.json"
    handback.write_text(json.dumps({"primary_deliverables": [{"strain_id": "SYN-A", "governance": "IN_SCOPE"}], "scope_note": "synthetic"}))
    code_root = Path(__file__).resolve().parents[1]
    identity = "SYN-A / contig1 / region001 / BGC001"
    locus = {"locus_key": "locus1", "exact_identity": identity, "source_member_sha256": "a" * 64, "strain": "SYN-A", "products_json": "[]"}
    class Connection:
        def __init__(self, name): self.name = name
        def execute(self, query, *args):
            if "from locus" in query:
                return [dict(locus, source_member_sha256=("b" * 64 if self.name == "architecture" else "a" * 64))]
            if "from strain" in query:
                return [{"strain": "SYN-A", "source_sha256": "c" * 64, "state": "COMPLETE", "selection_state": "SELECTED"}]
            if "from architecture" in query:
                return [{"locus_key": "locus1", "capacity_json": "{}"}]
            return []
        def close(self): pass
    ordered = ["census", "architecture", "transport", "cassette", "reference"] if census_first else ["architecture", "census", "transport", "cassette", "reference"]
    sources = {name: {"kind": name, "manifest": str(reader), "manifest_sha256": "synthetic", "database": str(reader), "sha256": "synthetic", "bytes": reader.stat().st_size} for name in ordered}
    reference = Connection("reference")
    monkeypatch.setattr(mod, "readonly", lambda pin: Connection(pin["kind"]))
    monkeypatch.setattr(mod, "module", lambda *args: SimpleNamespace(read=lambda *a, **k: None, admit=lambda *a, **k: nullcontext(reference)))
    from mamey import class_architecture, tool_database_reader
    monkeypatch.setattr(class_architecture, "siderophore_evidence_projection", lambda *args: {})
    monkeypatch.setattr(tool_database_reader, "inspect_tool_database", lambda *a, **k: None)
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"output_root": str(root), "rules_sha256": mod.sha(rules), "reference_reader": str(reader), "architecture_reader": str(reader), "reference_reader_sha256": mod.sha(reader), "architecture_reader_sha256": mod.sha(reader), "code_root": str(code_root), "projection_sha256": mod.sha(code_root / "mamey/class_architecture.py"), "sources": sources, "population": "synthetic", "current_handback": {"path": str(handback), "sha256": mod.sha(handback)}}))
    with pytest.raises(ValueError, match="architecture:LOCUS_SOURCE_HOLD"):
        mod.build(config, tmp_path, expected_config_sha256=mod.sha(config))
    assert not (root / "ATLAS.json").exists()
