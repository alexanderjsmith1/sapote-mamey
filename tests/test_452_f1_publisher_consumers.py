"""Publication-only main-entrypoint controls; opaque inputs, scientific helpers fenced."""
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest
from mamey import output_transaction


def load_tool(name, monkeypatch):
    root = Path(output_transaction.__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("f1_consumer_" + name, root / "tools" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return module


def normalized_root(tmp_path, spelling):
    out = tmp_path / "out"
    if spelling == "parent":
        (tmp_path / "guard").mkdir()
        return tmp_path / "guard" / ".." / "out", out
    if spelling == "symlink":
        out.mkdir()
        alias = tmp_path / "alias"
        alias.symlink_to(out, target_is_directory=True)
        return alias, out
    return out, out


def observe_publisher(monkeypatch):
    original = output_transaction.publish_payloads
    seen = []
    def publish(payloads, **kwargs):
        seen.append(dict(payloads))
        return original(payloads, **kwargs)
    monkeypatch.setattr(output_transaction, "publish_payloads", publish)
    return seen


def adapter(tmp_path, monkeypatch):
    tool = load_tool("bioassay_to_activity_channel", monkeypatch)
    source = tmp_path / "opaque_input.txt"
    source.write_bytes(b"opaque input; no assay interpretation\n")
    calls = []
    def build(*args):
        calls.append("build")
        return {"Fixture": {"metadata_state": "SUPPLIED_UNKNOWN", "assays": []}}
    monkeypatch.setattr(tool, "build", build)
    monkeypatch.setattr(tool, "build_af_dossier", lambda *args: [])
    monkeypatch.setattr(tool, "_adjudicate", lambda *args: pytest.fail("scientific adjudication reached"))
    monkeypatch.setattr(tool, "validate", lambda *args: pytest.fail("external validation reached"))
    return tool, source, calls


@pytest.mark.parametrize("slot", ["manifest", "record", "ancestor"])
def test_adapter_casefold_output_roster_refuses_before_publication(tmp_path, monkeypatch, capsys, slot):
    tool, source, calls = adapter(tmp_path, monkeypatch)
    original = source.read_bytes()
    out = tmp_path / "out"
    dossier = {"manifest": out / "manifest.json", "record": out / "fixture_bioactivity_metadata.json",
               "ancestor": tmp_path / "OUT"}[slot]
    if slot != "ancestor":
        out.mkdir()  # The caller requires the dossier's parent before serialization.
    seen = observe_publisher(monkeypatch)
    with pytest.raises(ValueError, match="output paths collide"):
        tool.main(["--recon", str(source), "--out", str(out), "--af-dossier-csv", str(dossier)])
    assert calls == ["build"] and len(seen) == 1
    assert source.read_bytes() == original
    assert out.is_dir() and list(out.iterdir()) == []
    assert "wrote" not in capsys.readouterr().out


@pytest.mark.parametrize("spelling", ["parent", "symlink"])
def test_adapter_normalizes_owned_output_root(tmp_path, monkeypatch, spelling):
    tool, source, calls = adapter(tmp_path, monkeypatch)
    original = source.read_bytes()
    supplied, actual = normalized_root(tmp_path, spelling)
    dossier = tmp_path / "dossier.csv"
    seen = observe_publisher(monkeypatch)
    assert tool.main(["--recon", str(source), "--out", str(supplied), "--af-dossier-csv", str(dossier)]) == 0
    assert calls == ["build"] and len(seen) == 1
    assert all(path == path.resolve() for path in seen[0])
    assert sorted(p.name for p in actual.iterdir()) == ["Fixture_bioactivity_metadata.json", "MANIFEST.json"]
    assert dossier.is_file() and source.read_bytes() == original


def extraction(tmp_path, monkeypatch, with_record):
    tool = load_tool("extract_cluster", monkeypatch)
    inputs = [tmp_path / "opaque_input.txt", tmp_path / "opaque_markers.txt"]
    for path in inputs:
        path.write_bytes(b"opaque fixture; no sequence parsing\n")
    original = {path: path.read_bytes() for path in inputs}
    sentinel = object()
    calls = []
    def parse(path, fmt):
        calls.append("parse_stub")
        return []
    def write(record, buffer, fmt):
        assert record is sentinel and fmt == "genbank"
        calls.append("serialize_stub")
        buffer.write("opaque serialized fixture\n")
        return 1
    fake = ModuleType("Bio")
    fake.SeqIO = SimpleNamespace(parse=parse, write=write)
    monkeypatch.setitem(sys.modules, "Bio", fake)
    def run(*args, **kwargs):
        calls.append("run_stub")
        return {"present": False, "n_cds_extracted": 0, "fixture_only": True}, sentinel if with_record else None
    monkeypatch.setattr(tool, "run", run)
    def forbidden(*args, **kwargs):
        pytest.fail("scientific extraction helper reached")
    for name in ["genecall", "find_cluster", "extract_gbk"]:
        monkeypatch.setattr(tool, name, forbidden)
    return tool, inputs, original, calls


@pytest.mark.parametrize("with_record,spelling", [(False, "plain"), (True, "plain"), (True, "parent"), (True, "symlink")])
def test_extraction_publishes_only_stubbed_serialized_roster(tmp_path, monkeypatch, with_record, spelling):
    tool, inputs, original, calls = extraction(tmp_path, monkeypatch, with_record)
    supplied, actual = normalized_root(tmp_path, spelling)
    seen = observe_publisher(monkeypatch)
    assert tool.main(["--genome", str(inputs[0]), "--marker", str(inputs[1]), "--label", "Fixture", "--outdir", str(supplied)]) == 0
    assert calls == ["parse_stub", "run_stub"] + (["serialize_stub"] if with_record else [])
    expected = ["Fixture_extract.json", "Fixture_cluster.gbk"] if with_record else ["Fixture_extract.json"]
    assert {p.name for p in actual.iterdir()} == set(expected)
    assert len(seen) == 1 and all(path == path.resolve() and path.parent == actual.resolve() for path in seen[0])
    assert json.loads((actual / "Fixture_extract.json").read_text())["fixture_only"] is True
    if with_record:
        assert (actual / "Fixture_cluster.gbk").read_bytes() == b"opaque serialized fixture\n"
    assert {path: path.read_bytes() for path in inputs} == original


def test_extraction_second_fsync_fault_rolls_back_owned_roster(tmp_path, monkeypatch, capsys):
    tool, inputs, original, calls = extraction(tmp_path, monkeypatch, True)
    out = tmp_path / "out"
    seen = observe_publisher(monkeypatch)
    fsync = output_transaction.os.fsync
    primary = OSError("synthetic second payload fsync fault")
    flushed = []
    def fault(fd):
        flushed.append(fd)
        if len(flushed) == 2:
            assert len(list(out.iterdir())) == 2
            raise primary
        return fsync(fd)
    monkeypatch.setattr(output_transaction.os, "fsync", fault)
    with pytest.raises(OSError) as caught:
        tool.main(["--genome", str(inputs[0]), "--marker", str(inputs[1]), "--label", "Fixture", "--outdir", str(out)])
    assert caught.value is primary and len(flushed) == 2 and len(seen) == 1
    assert {row["status"] for row in primary.rollback_cleanup_diagnostics} == {"REMOVED"}
    assert out.is_dir() and list(out.iterdir()) == []
    assert {path: path.read_bytes() for path in inputs} == original
    assert capsys.readouterr().out == ""
