"""v9.7.400 regression: the Project_Memory_Snapshot alias stub must resolve to the manifest.

Pre-.400 the snapshot was a verbatim re-dump of manifest.json (measured: a 96-BGC strain carried
a byte-identical 20,882,853-byte ``source_scans`` in BOTH files — ~40% of the sealed package).
The writer now emits a stub {"alias_of": "manifest.json"}; every reader must see the same content
it saw before. Packaging mechanics only — no scientific content changes.
"""
import json
import os

from mamey.snapshot_alias import load_snapshot, resolve_alias

MANIFEST = {
    "strain_id": "ST-400",
    "taxonomy": "Genericus sp.",
    "assembly": {"genome_bp": 5_000_000},
    "bgc_counts": {"raw": 3},
    "bgcs": [{"bgc_id": "BGC001", "contig": "C1"}],
    "source_scans": {"cctt": {"bgc_coupling": {}}, "domain_architecture": {"per_bgc": {}}},
}
STUB = {"schema": "project_memory_snapshot_alias_v1", "alias_of": "manifest.json",
        "strain_id": "ST-400", "note": "alias stub"}


def _write(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps(MANIFEST), encoding="utf-8")
    p = tmp_path / "ST-400_Project_Memory_Snapshot.json"
    p.write_text(json.dumps(STUB), encoding="utf-8")
    return str(p)


def test_load_snapshot_follows_alias(tmp_path):
    p = _write(tmp_path)
    got = load_snapshot(p)
    assert got["source_scans"] == MANIFEST["source_scans"]
    assert got["bgcs"] == MANIFEST["bgcs"]


def test_full_pre400_snapshot_returned_as_is(tmp_path):
    p = tmp_path / "ST-400_Project_Memory_Snapshot.json"
    p.write_text(json.dumps(MANIFEST), encoding="utf-8")  # old-style full copy
    got = load_snapshot(str(p))
    assert got == MANIFEST  # no alias key -> untouched


def test_missing_target_fails_open_to_stub(tmp_path):
    p = tmp_path / "ST-400_Project_Memory_Snapshot.json"
    p.write_text(json.dumps(STUB), encoding="utf-8")  # no manifest.json beside it
    got = load_snapshot(str(p))
    assert got == STUB  # honest degraded read, no exception


def test_resolve_alias_ignores_non_stub_dicts(tmp_path):
    d = {"alias_of": "manifest.json", "source_scans": {"x": 1}}  # has real content -> not a stub
    assert resolve_alias(d, str(tmp_path / "s.json")) == d


def test_tool_readers_follow_stub(tmp_path):
    """The tool-local loaders resolve the stub too (build_bgc_markers exemplar)."""
    import importlib.util, pathlib
    root = pathlib.Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("bbm", root / "tools" / "build_bgc_markers.py")
    bbm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bbm)
    p = _write(tmp_path)
    got = bbm._read_json(p)
    assert got["source_scans"] == MANIFEST["source_scans"]
    # non-snapshot files with an alias_of key are NOT rerouted
    other = tmp_path / "config.json"
    other.write_text(json.dumps({"alias_of": "manifest.json"}), encoding="utf-8")
    assert bbm._read_json(str(other)) == {"alias_of": "manifest.json"}


def test_deep_data_reads_manifest_through_stub(tmp_path):
    from mamey.deep_data import build_deep_data_files
    _write(tmp_path)
    (tmp_path / "ST-400_AntiSMASH_Evidence_Parse.json").write_text("{}", encoding="utf-8")
    counts = build_deep_data_files(tmp_path, "ST-400")
    # It ran against manifest content (source_scans present) without raising.
    assert isinstance(counts, dict)
    assert os.path.exists(tmp_path / "deep_data.json")
