"""Public explore presentation uses complete, admitted exact-locus identities.

The conservation scanners retain opaque-key lookup coverage. Identity admission
is a separate presentation boundary for human and JSON CLI output.
"""
from __future__ import annotations

import argparse
import json

import pytest

from mamey.exact_identity import (
    ExactLocusIdentityError,
    NativeManifestBGCIdentity,
    exact_locus_from_mapping,
    exact_locus_from_native_manifest_bgc,
)
from mamey.genome_explore import explore_command, render_explore, scan_divergence


STRAIN = "SYNTHETIC-001"


def _record(number: int) -> dict:
    alias = f"BGC{number:03d}"
    node = f"NODE_{number}_length_1000_cov_1"
    return {
        "bgc_id": alias,
        "contig": node,
        "node_id": node,
        "region_number": number,
        "antismash_region": f"region{number:03d}",
        "products": ["synthetic class"],
        "ab_score": 80,
        "af_score": 20,
    }


def _identity(number: int) -> str:
    return (
        f"{STRAIN} / NODE_{number}_length_1000_cov_1 / "
        f"region{number:03d} / BGC{number:03d}"
    )


def _package(tmp_path, records=None):
    root = tmp_path / "SYNTHETIC-001__NODE_1_length_1000_cov_1__region001__BGC001"
    root.mkdir()
    records = list(records if records is not None else (_record(1), _record(2), _record(3)))
    manifest = {
        "strain_id": STRAIN,
        "bgcs": records,
        "source_scans": {
            "clusterblast_genes": {
                "per_gene_best_hit": {
                    "BGC002": [{"pct_identity": 60}],
                }
            }
        },
        "resistance_gene_summary": {"bgc_coupling": {}},
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    overlay = root / "blastp_online"
    overlay.mkdir()
    (overlay / "BGC001_online_blastp.csv").write_text(
        "pct_identity,channel,source_channel\n50,nr,nr\n", encoding="utf-8"
    )
    (root / "synthetic_gene_context.jsonl").write_text(
        json.dumps({
            "bgc_id": "BGC003",
            "cds": [{"locus_tag": "gene_1", "product": "transposase"}],
        }) + "\n",
        encoding="utf-8",
    )
    return root


def test_canonical_mapping_accepts_current_lowercase_region_spelling():
    assert exact_locus_from_mapping(STRAIN, _record(1)) == _identity(1)


@pytest.mark.parametrize(
    ("contig", "node_id"),
    (
        ("NODE_1_length_1000_cov_1.5", "NODE_1_length_1000_cov_1"),
        ("ctg10_extra_suffix", "ctg10"),
        ("scaffold_42_segment_A", "scaffold_42"),
        ("CP123456.1", "CP123456.1"),
    ),
)
def test_native_adapter_preserves_full_contig_and_typed_join(contig, node_id):
    row = _record(1)
    row["contig"] = contig
    row["node_id"] = node_id
    result = exact_locus_from_native_manifest_bgc(STRAIN, row)
    assert isinstance(result, NativeManifestBGCIdentity)
    assert result.full_contig == contig
    assert result.normalized_node_id == node_id
    assert result.exact_locus == f"{STRAIN} / {contig} / region001 / BGC001"


@pytest.mark.parametrize("node_id", [None, "", "NODE_9_length_1000_cov_1"])
def test_native_adapter_refuses_missing_or_mismatched_normalized_node(node_id):
    row = _record(1)
    row["contig"] = "NODE_1_length_1000_cov_1.5"
    row["node_id"] = node_id
    with pytest.raises(ExactLocusIdentityError):
        exact_locus_from_native_manifest_bgc(STRAIN, row)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("Full_Node_ID", "NODE_9_length_1000_cov_1.5"),
        ("Contig", "NODE_9_length_1000_cov_1.5"),
        ("node", "NODE_9_length_1000_cov_1.5"),
        ("Node_ID", "NODE_9_length_1000_cov_1.5"),
        ("strain_id", "SYNTHETIC-999"),
        ("region", "region009"),
        ("bgc_alias", "BGC009"),
    ),
)
def test_native_adapter_keeps_other_synonyms_visible_to_conflict_owner(field, value):
    row = _record(1)
    row["contig"] = "NODE_1_length_1000_cov_1.5"
    row["node_id"] = "NODE_1_length_1000_cov_1"
    row[field] = value
    with pytest.raises(ExactLocusIdentityError):
        exact_locus_from_native_manifest_bgc(STRAIN, row)


def test_native_adapter_does_not_use_source_filename_as_identity_fallback():
    row = _record(1)
    row["contig"] = "unrecognized_record"
    row["node_id"] = "NODE_1_length_1000_cov_1"
    row["source_gbk"] = "NODE_1_length_1000_cov_1.5.region001.gbk"
    with pytest.raises(ExactLocusIdentityError, match="producer normalization"):
        exact_locus_from_native_manifest_bgc(STRAIN, row)


def test_generic_mapping_remains_strict_for_native_normalized_pair():
    row = _record(1)
    row["contig"] = "NODE_1_length_1000_cov_1.5"
    row["node_id"] = "NODE_1_length_1000_cov_1"
    with pytest.raises(ExactLocusIdentityError, match="conflicting full node-or-contig"):
        exact_locus_from_mapping(STRAIN, row)


def test_human_output_uses_exact_identity_in_every_individual_branch(tmp_path):
    text = render_explore(_package(tmp_path), top=3)
    top, confirmed, unconfirmed, co_capture = (
        text.split("## Top exploration leads", 1)[1].split("## nr-confirmed", 1)[0],
        text.split("## nr-confirmed", 1)[1].split("## Unconfirmed", 1)[0],
        text.split("## Unconfirmed", 1)[1].split("## Co-capture", 1)[0],
        text.split("## Co-capture", 1)[1],
    )
    assert all(_identity(number) in top for number in (1, 2, 3))
    assert _identity(1) in confirmed
    assert _identity(2) in unconfirmed
    assert _identity(3) in co_capture
    assert "the documented false-divergence case" in unconfirmed


def test_json_rows_gain_exact_identity_and_retain_secondary_fields(tmp_path, capsys):
    root = _package(tmp_path)
    assert explore_command(argparse.Namespace(package=root, top=3, json=True)) == 0
    payload = json.loads(capsys.readouterr().out)
    for section in ("exploration_board", "divergence", "co_capture"):
        for row in payload[section]:
            number = int(row["bgc_id"][-3:])
            assert row["exact_locus"] == _identity(number)
            assert "bgc_id" in row
            assert "node_region" in row


@pytest.mark.parametrize("json_output", [False, True])
@pytest.mark.parametrize(
    "case",
    (
        "missing_strain",
        "missing_node",
        "short_node",
        "missing_region",
        "conflicting_node",
        "conflicting_region",
        "missing_alias",
        "conflicting_alias",
    ),
)
def test_invalid_raw_record_fails_before_any_cli_output(tmp_path, capsys, case, json_output):
    record = _record(1)
    manifest_strain = STRAIN
    if case == "missing_strain":
        manifest_strain = None
    elif case == "missing_node":
        record.pop("node_id")
        record.pop("contig")
    elif case == "short_node":
        record["node_id"] = record["contig"] = "NODE_1"
    elif case == "missing_region":
        record.pop("antismash_region")
    elif case == "conflicting_node":
        record["contig"] = "NODE_9_length_1000_cov_1"
    elif case == "conflicting_region":
        record["region"] = "region009"
    elif case == "missing_alias":
        record.pop("bgc_id")
    elif case == "conflicting_alias":
        record["bgc_alias"] = "BGC009"

    root = _package(tmp_path, [record])
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    manifest["strain_id"] = manifest_strain
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(SystemExit, match="^EXACT_LOCUS_IDENTITY_REQUIRED: "):
        explore_command(argparse.Namespace(package=root, top=3, json=json_output))
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("json_output", [False, True])
def test_duplicate_raw_alias_fails_before_keyed_collapse_or_output(tmp_path, capsys, json_output):
    first = _record(1)
    duplicate = _record(2)
    duplicate["bgc_id"] = first["bgc_id"]
    root = _package(tmp_path, [first, duplicate])
    with pytest.raises(SystemExit, match="duplicate"):
        explore_command(argparse.Namespace(package=root, top=3, json=json_output))
    assert capsys.readouterr().out == ""


def test_opaque_numeric_lookup_fixture_stays_low_level_and_is_not_identity_admitted(tmp_path):
    record = _record(1)
    opaque_key = "SYNTHETIC-001__NODE_1_length_1000_cov_1__region001__BGC001"
    record["bgc_id"] = opaque_key
    record["bgc_alias"] = "BGC001"
    root = _package(tmp_path, [record])
    row = scan_divergence(root)[0]
    assert row["bgc_id"] == opaque_key
    with pytest.raises(ExactLocusIdentityError, match="conflicting BGC alias"):
        render_explore(root)
