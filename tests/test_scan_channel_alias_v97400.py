"""v9.7.400 regression: source_scans channel-alias stubs must resolve to their standalone files.

Four manifest source_scans sub-objects were embedded as verbatim copies of files already shipped
in the same package (~83-90% of source_scans, measured). The writer now embeds stubs; readers must
see the same content as before. Packaging mechanics only — no scientific content change.
"""
import builtins
import json
from pathlib import Path

import pytest

from mamey.scan_channel_alias import is_channel_stub, resolve_scan_channel, resolve_scan_channels

RG = {"ranked_pairs": [{"pair": "BGC001+BGC002", "rggmci_confidence": "LOW_SHARED_REFERENCE_SIGNAL"}],
      "pairs_total": 1}
STUB = {"schema": "source_scan_channel_alias_v1", "alias_of": "ST-401_4A_RGGMCI_full.json"}


def _pkg(tmp_path):
    (tmp_path / "ST-401_4A_RGGMCI_full.json").write_text(json.dumps(RG), encoding="utf-8")
    return tmp_path


def test_stub_resolves_to_standalone_file(tmp_path):
    pkg = _pkg(tmp_path)
    scans = {"rggmci": dict(STUB), "cctt": {"bgc_coupling": {}}}
    assert resolve_scan_channel(scans, "rggmci", pkg) == RG
    # non-stubbed channels pass through untouched
    assert resolve_scan_channel(scans, "cctt", pkg) == {"bgc_coupling": {}}


def test_pre400_full_object_untouched(tmp_path):
    scans = {"rggmci": RG}
    assert resolve_scan_channel(scans, "rggmci", tmp_path) == RG
    assert not is_channel_stub(RG)


def test_missing_target_fails_open(tmp_path):
    scans = {"rggmci": dict(STUB)}  # no standalone file written
    assert resolve_scan_channel(scans, "rggmci", tmp_path) == STUB


def test_resolve_all_channels_in_manifest(tmp_path):
    pkg = _pkg(tmp_path)
    man = {"strain_id": "ST-401", "source_scans": {"rggmci": dict(STUB), "flbr": {"n": 1}}}
    out = resolve_scan_channels(man, pkg)
    assert out["source_scans"]["rggmci"] == RG
    assert out["source_scans"]["flbr"] == {"n": 1}


def test_error_status_dict_is_not_mistaken_for_stub():
    # writers emit e.g. {"status": "ERROR_...", "per_gene_best_hit": {}} on failure — never a stub
    assert not is_channel_stub({"status": "ERROR_X", "per_gene_best_hit": {}})
    assert not is_channel_stub(None)
    assert not is_channel_stub({})


def _unsafe_alias_fixture(tmp_path, kind):
    package = tmp_path / "package"
    package.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    outside = outside_dir / "payload.json"
    outside.write_text(json.dumps({"marker": "CONTROLLED_EXTERNAL_PAYLOAD"}), encoding="utf-8")
    if kind == "traversal":
        target = "../outside/payload.json"
    elif kind == "absolute":
        target = str(outside)
    elif kind == "symlink_leaf":
        (package / "linked.json").symlink_to(outside)
        target = "linked.json"
    elif kind == "symlink_ancestor":
        (package / "linked_dir").symlink_to(outside_dir, target_is_directory=True)
        target = "linked_dir/payload.json"
    else:  # pragma: no cover - caller owns the finite case set
        raise AssertionError(kind)
    stub = {"schema": "source_scan_channel_alias_v1", "alias_of": target}
    return package, outside, stub


@pytest.mark.parametrize("kind", ["traversal", "absolute", "symlink_leaf", "symlink_ancestor"])
def test_unsafe_alias_returns_original_stub_without_opening_external_target(tmp_path, monkeypatch, kind):
    package, outside, stub = _unsafe_alias_fixture(tmp_path, kind)
    real_open = builtins.open
    opened_external = []

    def guarded_open(path, *args, **kwargs):
        if Path(path).resolve() == outside.resolve():
            opened_external.append(Path(path))
            raise AssertionError("compatibility resolver attempted to open the external target")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guarded_open)
    assert resolve_scan_channel({"clusterblast_genes": stub}, "clusterblast_genes", package) == stub
    assert opened_external == []


@pytest.mark.parametrize("bad_alias", [7, ["payload.json"], {"name": "payload.json"}])
def test_malformed_alias_type_never_materializes_a_stringified_filename(tmp_path, bad_alias):
    package = tmp_path / "package"
    package.mkdir()
    stringified = package / str(bad_alias)
    stringified.write_text(json.dumps({"marker": "MUST_NOT_MATERIALIZE"}), encoding="utf-8")
    stub = {"schema": "source_scan_channel_alias_v1", "alias_of": bad_alias}
    assert resolve_scan_channel({"clusterblast_genes": stub}, "clusterblast_genes", package) == stub


@pytest.mark.parametrize("payload", ["[]", "null", "{broken"])
def test_malformed_or_non_object_payload_returns_original_stub(tmp_path, payload):
    target = tmp_path / "payload.json"
    target.write_text(payload, encoding="utf-8")
    stub = {"schema": "source_scan_channel_alias_v1", "alias_of": target.name}
    assert resolve_scan_channel({"clusterblast_genes": stub}, "clusterblast_genes", tmp_path) == stub


def test_valid_nested_package_alias_still_materializes(tmp_path):
    nested = tmp_path / "nested"
    nested.mkdir()
    payload = {"marker": "CONTROLLED_INTERNAL_PAYLOAD"}
    (nested / "payload.json").write_text(json.dumps(payload), encoding="utf-8")
    stub = {"schema": "source_scan_channel_alias_v1", "alias_of": "nested/payload.json"}
    assert resolve_scan_channel({"clusterblast_genes": stub}, "clusterblast_genes", tmp_path) == payload


def test_bound_loader_rejects_symlink_ancestor(tmp_path):
    package = tmp_path / "package"
    package.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    (outside_dir / "payload.json").write_text("{}", encoding="utf-8")
    (package / "linked_dir").symlink_to(outside_dir, target_is_directory=True)
    manifest = package / "manifest.json"
    manifest.write_text(json.dumps({"source_scans": {"clusterblast_genes": {
        "schema": "source_scan_channel_alias_v1",
        "alias_of": "linked_dir/payload.json",
    }}}), encoding="utf-8")

    from mamey.scan_channel_alias import load_bound_scan_manifest, ScanChannelBindingError
    with pytest.raises(ScanChannelBindingError, match="symlinks"):
        load_bound_scan_manifest(manifest)


@pytest.mark.parametrize("kind", ["traversal", "absolute", "symlink_leaf", "symlink_ancestor"])
def test_genome_explore_cannot_consume_external_alias_payload(tmp_path, kind):
    from mamey.genome_explore import _conservation_median

    package, outside, stub = _unsafe_alias_fixture(tmp_path, kind)
    outside.write_text(json.dumps({"per_gene_best_hit": {
        "SYNTHETIC_ALIAS": [{"pct_identity": 99.0}],
    }}), encoding="utf-8")
    manifest = {"source_scans": {"clusterblast_genes": stub}}
    assert _conservation_median(package, manifest, "SYNTHETIC_ALIAS") == (None, 0, 0)


@pytest.mark.parametrize("kind", ["traversal", "absolute", "symlink_leaf", "symlink_ancestor"])
def test_authored_verify_cannot_consume_external_alias_payload(tmp_path, kind):
    from mamey.authored_verify import _bgc_context_from_package

    package, outside, stub = _unsafe_alias_fixture(tmp_path, kind)
    outside.write_text(json.dumps({"per_gene_best_hit": {
        "SYNTHETIC_ALIAS": [{"pct_identity": 99.0}],
    }}), encoding="utf-8")
    (package / "manifest.json").write_text(json.dumps({
        "bgcs": [{"bgc_id": "SYNTHETIC_ALIAS"}],
        "source_scans": {"clusterblast_genes": stub},
    }), encoding="utf-8")
    context = _bgc_context_from_package(str(package), "SYNTHETIC_ALIAS") or {}
    assert "conservation_median_id" not in context
