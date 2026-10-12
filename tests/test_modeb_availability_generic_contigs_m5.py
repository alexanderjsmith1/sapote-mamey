"""Exact label joins across real availability entrypoints; no genome sequences.

Public accession strings are metadata only. All artifacts and gene labels here
are synthetic software fixtures, not claims about the public genome.
"""
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from mamey.mode_b.availability import (
    build_availability, discover_evidence, load_contract, load_evidence_index,
    load_inventory, write_outputs,
)

STRAIN = "SYNTHETIC_REFERENCE"
CONTIG = "CP103060.1"
NODE = "NODE_7_length_50000_cov_20.5"
ROOT = Path(__file__).resolve().parents[1]


def _table(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    return path


def _canonical(contig=CONTIG, **extra):
    return {"strain": STRAIN, "bgc": "BGC001", "full_node": contig,
            "region": "region001", **extra}


def _inventory(tmp_path, rows=None):
    path = _table(tmp_path / "inventory.tsv", rows or [_canonical()])
    return path, load_inventory(path)


def _index(tmp_path, loci, identity, *, name="opaque.txt", requested=""):
    artifact = tmp_path / name
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("synthetic evidence only\n")
    row = {"channel": "gene_inventory", "source_path": str(artifact), **identity}
    if requested:
        row["binding_state"] = requested
    path = _table(tmp_path / "evidence_index.tsv", [row])
    return load_evidence_index(path, loci)


def _states(loci, observations):
    return build_availability(loci, observations, load_contract())


def _assert_unbound(loci, observations):
    assert len(observations) == 1
    assert observations[0].binding_state == "UNBOUND"
    assert observations[0].exact_locus == ""
    rows, _, sections = _states(loci, observations)
    assert rows[0]["gene_inventory_state"] == "UNBOUND"
    assert rows[0]["writing_gate"] == "HOLD_MISSING_GENE_LEVEL_SOURCE"
    assert all("gene_inventory" not in r["available_streams"].split(";") for r in sections)


@pytest.mark.parametrize("header", ["full_node", "Contig", "Node_ID"])
def test_accession_engine_fields_reach_written_exact_identity(tmp_path, header):
    row = {"Strain": STRAIN, "BGC_ID": "BGC001", header: CONTIG, "Region": "1"}
    _, loci = _inventory(tmp_path, [row])
    observations = _index(tmp_path, loci, row)
    assert loci[0].full_node == CONTIG and loci[0].region == "region001"
    assert observations[0].binding_state == "EXACT_LOCUS"
    assert observations[0].full_node == CONTIG and observations[0].record_count == 1
    manifest = write_outputs(tmp_path / "outputs", loci, observations, load_contract())
    assert manifest["bgc_count"] == 1
    with (tmp_path / "outputs/modeb_bgc_availability.tsv").open() as handle:
        emitted = next(csv.DictReader(handle, delimiter="\t"))
    assert emitted["full_node"] == CONTIG
    assert emitted["exact_locus"] == f"{STRAIN}|{CONTIG}|region001"
    assert emitted["writing_gate"] == "PASS_FOR_GAP_AWARE_AUTHORING"
    with (tmp_path / "outputs/modeb_evidence_observations.tsv").open() as handle:
        observed = next(csv.DictReader(handle, delimiter="\t"))
    assert observed["full_node"] == CONTIG and observed["identity_diagnostics"] == ""


@pytest.mark.parametrize("contig", ["chromosome", "contig_alpha-1", "ctgA.v2", "scaffold_42", "ctg:alpha+beta"])
def test_generic_contigs_survive_index_table_and_final_gate(tmp_path, contig):
    _, loci = _inventory(tmp_path, [_canonical(contig)])
    indexed = _index(tmp_path, loci, _canonical(contig))
    source = _table(tmp_path / "discovery/gene_context.tsv", [_canonical(contig), _canonical(contig)])
    discovered = discover_evidence(loci, load_contract(), [("rows", source)])
    assert indexed[0].binding_state == discovered[0].binding_state == "EXACT_LOCUS"
    assert discovered[0].record_count == 2
    assert indexed[0].full_node == discovered[0].full_node == contig
    rows, _, _ = _states(loci, discovered)
    assert rows[0]["writing_gate"] == "PASS_FOR_GAP_AWARE_AUTHORING"
    assert rows[0]["promotion_gate"] == "HOLD_BLASTP_UNAVAILABLE_OR_UNBOUND"


@pytest.mark.parametrize("inventory_contig,evidence_contig", [
    ("ctgA", "CTGA"), (CONTIG, "CP103060.2"), (CONTIG, "CP103060"),
    (CONTIG, "NZ_CP103060.1"),
])
def test_generic_case_accession_version_and_namespace_are_not_coalesced(tmp_path, inventory_contig, evidence_contig):
    _, loci = _inventory(tmp_path, [_canonical(inventory_contig)])
    observations = _index(tmp_path, loci, _canonical(evidence_contig))
    _assert_unbound(loci, observations)
    assert observations[0].full_node == evidence_contig


@pytest.mark.parametrize("field,value", [
    ("Assembly_Locator", f"{CONTIG} region001 (BGC001)"),
    ("assembly_locator", f"{CONTIG} region001"),
    ("Source_GBK", f"{CONTIG}.region001.gbk"),
    ("region_member", f"input/{CONTIG}.region001.gbk"),
    ("source_gbk", f"C:\\staging\\{CONTIG}.region001.gbk"),
])
def test_display_and_member_fields_establish_exact_identity(tmp_path, field, value):
    row = {"strain": STRAIN, "bgc": "BGC001", field: value}
    _, loci = _inventory(tmp_path, [row])
    assert loci[0].full_node == CONTIG and loci[0].region == "region001"
    observations = _index(tmp_path, loci, row)
    assert observations[0].binding_state == "EXACT_LOCUS"
    assert observations[0].full_node == CONTIG
    assert _states(loci, observations)[0][0]["writing_gate"] == "PASS_FOR_GAP_AWARE_AUTHORING"


@pytest.mark.parametrize("extra", [
    {"Node_ID": "CP103061.1"},
    {"Assembly_Locator": f"{CONTIG} region002 (BGC001)"},
    {"Source_GBK": f"{CONTIG}.region002.gbk"},
    {"Assembly_Locator": f"{CONTIG} region001 (BGC002)"},
    {"Strain": "SYNTHETIC_OTHER"}, {"BGC_ID": "BGC002"},
])
def test_conflicting_columns_refuse_inventory_and_hold_index(tmp_path, extra):
    _, loci = _inventory(tmp_path)
    row = _canonical(**extra)
    bad = _table(tmp_path / "conflict.tsv", [row])
    with pytest.raises(ValueError, match="invalid/conflicting identity"):
        load_inventory(bad)
    observations = _index(tmp_path, loci, row)
    _assert_unbound(loci, observations)
    assert "CONFLICT" in observations[0].identity_diagnostics
    assert "CP103061.1" not in observations[0].notes


@pytest.mark.parametrize("name", [
    f"{CONTIG}.region001.gbk", f"{STRAIN}_BGC001_{CONTIG}.region001.gbk",
])
def test_region_member_discovery_uses_basename_and_inventory_context(tmp_path, name):
    _, loci = _inventory(tmp_path)
    source = tmp_path / "evidence" / STRAIN / "BGC001" / name
    source.parent.mkdir(parents=True)
    source.write_text("synthetic record marker; no sequence\n")
    observations = discover_evidence(loci, load_contract(), [("members", tmp_path / "evidence")])
    assert len(observations) == 1 and observations[0].binding_state == "EXACT_LOCUS"
    assert observations[0].full_node == CONTIG and observations[0].region == "region001"
    assert _states(loci, observations)[0][0]["writing_gate"] == "PASS_FOR_GAP_AWARE_AUTHORING"


def test_contig_directory_does_not_establish_exact_identity(tmp_path):
    _, loci = _inventory(tmp_path)
    source = tmp_path / "evidence" / STRAIN / "BGC001" / CONTIG / "unrelated_gene_context.csv"
    source.parent.mkdir(parents=True)
    source.write_text("description\nsynthetic\n")
    observations = discover_evidence(loci, load_contract(), [("paths", tmp_path / "evidence")])
    assert observations[0].binding_state == "ALIAS_BOUND"
    assert observations[0].full_node == "" and observations[0].region == ""


def test_opaque_header_aware_table_is_exact_and_input_immutable(tmp_path):
    inventory, loci = _inventory(tmp_path)
    source = _table(tmp_path / "opaque_gene_context.csv", [_canonical(), _canonical()])
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in [inventory, source]}
    observations = discover_evidence(loci, load_contract(), [("table", source)])
    assert observations[0].binding_state == "EXACT_LOCUS" and observations[0].record_count == 2
    write_outputs(tmp_path / "out", loci, observations, load_contract())
    assert before == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in before}


@pytest.mark.parametrize("identity,name", [
    (_canonical("CP103060.2"), "gene_context.tsv"),
    (_canonical("invalid/contig"), "gene_context.tsv"),
    (_canonical(**{"Node_ID": "CP103061.1"}), "gene_context.tsv"),
])
def test_table_conflicts_are_not_repaired_by_helpful_paths(tmp_path, identity, name):
    _, loci = _inventory(tmp_path)
    source = _table(tmp_path / "evidence" / STRAIN / "BGC001" / CONTIG / name, [identity])
    observations = discover_evidence(loci, load_contract(), [("rows", tmp_path / "evidence")])
    _assert_unbound(loci, observations)
    assert observations[0].identity_diagnostics
    if identity["full_node"] == "CP103060.2":
        assert observations[0].identity_diagnostics == "inventory:FULL_CONTIG_CONFLICT"
        assert observations[0].full_node == "CP103060.2"


@pytest.mark.parametrize("rows,error", [
    ([_canonical(), _canonical("CP103061.1")], "alias is not unique"),
    ([_canonical(), _canonical(bgc="BGC002")], "exact locus is duplicated"),
])
def test_duplicate_alias_or_exact_generic_locus_refuses_inventory(tmp_path, rows, error):
    path = _table(tmp_path / "duplicate.tsv", rows)
    with pytest.raises(ValueError, match=error):
        load_inventory(path)


def test_same_accession_in_two_strains_needs_unambiguous_path_context(tmp_path):
    _, loci = _inventory(tmp_path, [_canonical(), _canonical(strain="SYNTHETIC_OTHER")])
    assert len(loci) == 2
    source = tmp_path / "evidence" / STRAIN / "SYNTHETIC_OTHER" / f"{CONTIG}.region001.gbk"
    source.parent.mkdir(parents=True)
    source.write_text("synthetic marker\n")
    observations = discover_evidence(loci, load_contract(), [("ambiguous", tmp_path / "evidence")])
    assert observations[0].binding_state == "UNBOUND"
    assert "path_strain:AMBIGUOUS" in observations[0].identity_diagnostics
    rows, _, _ = _states(loci, observations)
    assert all(r["writing_gate"] == "HOLD_MISSING_GENE_LEVEL_SOURCE" for r in rows)


def test_missing_inventory_and_alias_only_evidence_keep_distinct_gates(tmp_path):
    _, unresolved = _inventory(tmp_path, [{"strain": STRAIN, "bgc": "BGC001"}])
    assert unresolved[0].full_node == ""
    alias = {"strain": STRAIN, "bgc": "BGC001"}
    rows, _, _ = _states(unresolved, _index(tmp_path, unresolved, alias))
    assert rows[0]["writing_gate"] == "HOLD_IDENTITY_UNRESOLVED"
    _, complete = _inventory(tmp_path)
    observations = _index(tmp_path, complete, alias)
    assert observations[0].binding_state == "ALIAS_BOUND" and observations[0].full_node == ""
    assert _states(complete, observations)[0][0]["writing_gate"] == "PASS_FOR_GAP_AWARE_AUTHORING"


@pytest.mark.parametrize("contig,evidence,state", [
    (NODE, "NODE_7", "ALIAS_BOUND"), (NODE, "NODE_8", "UNBOUND"),
    (CONTIG, "NODE_7", "UNBOUND"),
])
def test_short_node_is_partial_and_cannot_cross_accession_identity(tmp_path, contig, evidence, state):
    _, loci = _inventory(tmp_path, [_canonical(contig)])
    observations = _index(tmp_path, loci, _canonical(evidence))
    assert observations[0].binding_state == state and observations[0].full_node == ""
    assert "full_node=partial" in observations[0].identity_field_states
    if state == "UNBOUND":
        _assert_unbound(loci, observations)


@pytest.mark.parametrize("value", [
    "NODE_7_length_50000", "NODE_7_length_50000_cov_20.5garbage",
    "/tmp/CP103060.1", "input/CP103060.1", "https://example.invalid/CP103060.1",
    "CP103060.1|other", "CP103060.1\nother", "NODE_UNRESOLVED", "C:chromosome",
    f"{CONTIG}.region001.gbk",
])
def test_invalid_explicit_contig_never_disappears_into_alias_fallback(tmp_path, value):
    _, loci = _inventory(tmp_path)
    row = _canonical(value)
    path = _table(tmp_path / "invalid.tsv", [row])
    with pytest.raises(ValueError, match="invalid/conflicting identity"):
        load_inventory(path)
    observations = _index(tmp_path, loci, row)
    _assert_unbound(loci, observations)
    assert "full_node:" in observations[0].identity_diagnostics
    assert value not in observations[0].notes


@pytest.mark.parametrize("exact", [
    f"{STRAIN}|CP103060.2|region001", f"{STRAIN}||region001", "malformed",
])
def test_explicit_generic_exact_locus_must_reconcile(tmp_path, exact):
    path = _table(tmp_path / "bad_exact.tsv", [_canonical(exact_locus=exact)])
    with pytest.raises(ValueError, match="exact_locus conflicts"):
        load_inventory(path)


def test_atomic_region_substring_is_preserved_without_region_inference(tmp_path):
    contig = "chrom.region001.segment"
    row = {"strain": STRAIN, "bgc": "BGC001", "full_node": contig}
    _, loci = _inventory(tmp_path, [row])
    assert loci[0].full_node == contig and loci[0].region == ""
    assert _states(loci, [])[0][0]["writing_gate"] == "HOLD_IDENTITY_UNRESOLVED"


@pytest.mark.parametrize("member", [
    f"{CONTIG}.region001.region002.gbk", f"{CONTIG}.region001.gbk.trailing",
    f"{CONTIG}.region000.gbk",
])
def test_malformed_region_members_hold_even_with_matching_alias(tmp_path, member):
    _, loci = _inventory(tmp_path)
    observations = _index(tmp_path, loci, _canonical(Source_GBK=member))
    _assert_unbound(loci, observations)
    assert "Source_GBK:" in observations[0].identity_diagnostics


def test_index_requested_binding_is_checked_after_generic_resolution(tmp_path):
    _, loci = _inventory(tmp_path)
    with pytest.raises(ValueError, match="requested EXACT_LOCUS"):
        _index(tmp_path, loci, {"strain": STRAIN, "bgc": "BGC001"}, requested="EXACT_LOCUS")


def test_opaque_whole_record_source_is_provenance_only(tmp_path):
    _, loci = _inventory(tmp_path, [_canonical(Source_GBK="input/whole_record.gbk")])
    observations = _index(tmp_path, loci, _canonical(Source_GBK="input/whole_record.gbk"),
                          name="CP103060.2/opaque.txt")
    assert observations[0].binding_state == "EXACT_LOCUS"
    assert "Source_GBK=provenance_only" in observations[0].identity_field_states
    assert observations[0].identity_diagnostics == ""


def test_invalid_and_alias_only_rows_are_not_deduplicated_together(tmp_path):
    _, loci = _inventory(tmp_path)
    source = _table(tmp_path / "evidence/gene_context.tsv", [
        {"strain": STRAIN, "bgc": "BGC001", "full_node": "invalid/contig"},
        {"strain": STRAIN, "bgc": "BGC001"},
    ])
    observations = discover_evidence(loci, load_contract(), [("rows", source)])
    assert len(observations) == 2
    assert {o.binding_state for o in observations} == {"UNBOUND", "ALIAS_BOUND"}
    assert sum(o.record_count for o in observations) == 2
    assert any(o.identity_diagnostics for o in observations)


def test_public_reference_metadata_51_region_cli_walkthrough(tmp_path):
    # Same identity/header shape as the separately bound public saved inventory;
    # no local workspace paths, genome sequences, or annotation claims bundled.
    public_strain = "Streptomyces_albus_DSM40763"
    rows = [{"Strain": public_strain, "BGC_ID": f"BGC{n:03d}", "Contig": CONTIG,
             "Node_ID": CONTIG, "Region": str(n), "antiSMASH_Region": f"region{n:03d}",
             "Assembly_Locator": f"{CONTIG} region{n:03d} (BGC{n:03d})",
             "Source_GBK": f"{CONTIG}.region{n:03d}.gbk"} for n in range(1, 52)]
    inventory = _table(tmp_path / "public_shape_inventory.tsv", rows)
    artifact = tmp_path / "synthetic_gene_context.tsv"
    _table(artifact, [{"strain": public_strain, "bgc": f"BGC{n:03d}", "Contig": CONTIG,
                       "region": f"region{n:03d}"} for n in range(1, 52)])
    index = _table(tmp_path / "curated_index.tsv", [
        {"channel": "gene_inventory", "source_path": str(artifact), "strain": public_strain,
         "bgc": f"BGC{n:03d}", "full_node": CONTIG, "region": f"region{n:03d}",
         "binding_state": "EXACT_LOCUS"} for n in range(1, 52)])
    source_inputs = [inventory, artifact, index]
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in source_inputs}
    output = tmp_path / "availability"
    result = subprocess.run([sys.executable, str(ROOT / "mamey_run.py"), "modeb-availability",
                             "--inventory", str(inventory), "--evidence-index", str(index),
                             "--out", str(output)], cwd=ROOT, capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]
    manifest = json.loads((output / "modeb_availability_manifest.json").read_text())
    assert manifest["status"] == "PASS" and manifest["bgc_count"] == 51
    with (output / "modeb_bgc_availability.tsv").open() as handle:
        emitted = list(csv.DictReader(handle, delimiter="\t"))
    assert len(emitted) == 51 and {r["full_node"] for r in emitted} == {CONTIG}
    assert {r["strain"] for r in emitted} == {public_strain}
    assert {r["exact_locus"] for r in emitted} == {
        f"{public_strain}|{CONTIG}|region{n:03d}" for n in range(1, 52)}
    assert {r["inventory_identity_state"] for r in emitted} == {"EXACT_LOCUS"}
    assert {r["gene_inventory_state"] for r in emitted} == {"EXACT_LOCUS"}
    assert {r["writing_gate"] for r in emitted} == {"PASS_FOR_GAP_AWARE_AUTHORING"}
    assert {r["promotion_gate"] for r in emitted} == {"HOLD_BLASTP_UNAVAILABLE_OR_UNBOUND"}
    assert {r["region"] for r in emitted} == {f"region{n:03d}" for n in range(1, 52)}
    with (output / "modeb_section_plan.tsv").open() as handle:
        sections = list(csv.DictReader(handle, delimiter="\t"))
    assert len(sections) == 51 * 30
    assert any("gene_inventory" in r["available_streams"].split(";") for r in sections)
    assert before == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in source_inputs}


@pytest.mark.parametrize("member", ["CP103060.2.region001.gbk", "CP103060.1.region002.gbk"])
def test_index_recognized_member_cannot_contradict_explicit_fields(tmp_path, member):
    _, loci = _inventory(tmp_path)
    observations = _index(tmp_path, loci, _canonical(), name=member)
    _assert_unbound(loci, observations)
    assert "PATH_CONFLICT" in observations[0].identity_diagnostics


def test_generic_member_contig_with_bgc_substring_is_not_a_path_alias(tmp_path):
    contig = "chrom_BGC007_complete"
    _, loci = _inventory(tmp_path, [_canonical(contig)])
    source = tmp_path / "evidence" / STRAIN / f"{contig}.region001.gbk"
    source.parent.mkdir(parents=True)
    source.write_text("synthetic marker\n")
    observations = discover_evidence(loci, load_contract(), [("member", tmp_path / "evidence")])
    assert observations[0].binding_state == "EXACT_LOCUS"
    assert observations[0].bgc == "BGC001" and observations[0].full_node == contig


@pytest.mark.parametrize("region", ["0", "-1", "prefix_region001", "region001 suffix"])
def test_structured_regions_require_positive_whole_values(tmp_path, region):
    _, loci = _inventory(tmp_path)
    observations = _index(tmp_path, loci, _canonical(region=region))
    _assert_unbound(loci, observations)
    assert "region:INVALID_REGION" in observations[0].identity_diagnostics


def _native_row(physical, normalized, **extra):
    return {"Strain": STRAIN, "BGC_ID": "BGC001", "Contig": physical,
            "Node_ID": normalized, "antiSMASH_Region": "region001", "Region": "1",
            "Assembly_Locator": f"{normalized} region001 (BGC001)", **extra}


@pytest.mark.parametrize("contig,normalized", [
    ("NODE_7_length_50000_cov_20.5", "NODE_7_length_50000_cov_20"),
    ("scaffold_42_complete.v2", "scaffold_42"), ("ctg10_extended", "ctg10"),
])
def test_current_native_inventory_roles_keep_complete_physical_contig(tmp_path, contig, normalized):
    row = _native_row(contig, normalized)
    _, loci = _inventory(tmp_path, [row])
    observations = _index(tmp_path, loci, row)
    expected = contig.upper() if contig.startswith("NODE_") else contig
    assert loci[0].full_node == observations[0].full_node == expected
    assert observations[0].binding_state == "EXACT_LOCUS"
    assert observations[0].identity_diagnostics == ""
    assert "Node_ID=producer_normalized" in observations[0].identity_field_states
    assert "Assembly_Locator=producer_display" in observations[0].identity_field_states
    assert _states(loci, observations)[0][0]["writing_gate"] == "PASS_FOR_GAP_AWARE_AUTHORING"


@pytest.mark.parametrize("extra", [
    {"Node_ID": "NODE_7_length_50000_cov_21"},
    {"full_node": "NODE_7_length_50000_cov_21.5"},
    {"Assembly_Locator": "NODE_7_length_50000_cov_21 region001 (BGC001)"},
    {"Region": "2"}, {"Source_GBK": "NODE_7_length_50000_cov_21.5.region001.gbk"},
])
def test_native_producer_roles_cannot_hide_physical_or_display_conflicts(tmp_path, extra):
    row = _native_row(NODE, "NODE_7_length_50000_cov_20", **extra)
    # Establish the canonical row using the actual validated producer roles.
    _, loci = _inventory(tmp_path, [_native_row(NODE, "NODE_7_length_50000_cov_20")])
    path = _table(tmp_path / "invalid_native.tsv", [row])
    with pytest.raises(ValueError, match="invalid/conflicting identity"):
        load_inventory(path)
    observations = _index(tmp_path, loci, row)
    _assert_unbound(loci, observations)
    assert observations[0].identity_diagnostics


@pytest.mark.parametrize("contig,normalized", [
    ("NODE_7_length_50000_cov_20.5", "NODE_7_length_50000_cov_20"),
    ("scaffold_42_complete.v2", "scaffold_42"),
])
def test_current_native_lowercase_crosswalk_roles_are_validated_separately(tmp_path, contig, normalized):
    row = {"strain": STRAIN, "bgc_id": "BGC001", "contig": contig,
           "node_id": normalized, "antismash_region": "region001",
           "assembly_locator": f"{normalized} region001 (BGC001)"}
    _, loci = _inventory(tmp_path, [row])
    observations = _index(tmp_path, loci, row)
    assert observations[0].binding_state == "EXACT_LOCUS"
    assert observations[0].full_node == loci[0].full_node
    assert "node_id=producer_normalized" in observations[0].identity_field_states


def test_partial_native_header_set_does_not_authorize_producer_token_equivalence(tmp_path):
    _, loci = _inventory(tmp_path, [_canonical(NODE)])
    row = {"strain": STRAIN, "BGC_ID": "BGC001", "Contig": NODE,
           "Node_ID": "NODE_7_length_50000_cov_20", "region": "region001"}
    observations = _index(tmp_path, loci, row)
    _assert_unbound(loci, observations)
    assert "full_node:CONFLICT" in observations[0].identity_diagnostics


@pytest.mark.parametrize("extra", [
    {"Node_ID": "CP103060.2"},
    {"node_id": "CP103060.2"},
    {"contig": "CP103060.2"},
    {"full_node": "CP103060"},
])
def test_native_accession_roles_keep_version_and_synonym_conflicts_visible(tmp_path, extra):
    _, loci = _inventory(tmp_path, [_native_row(CONTIG, CONTIG)])
    observations = _index(tmp_path, loci, _native_row(CONTIG, CONTIG, **extra))
    _assert_unbound(loci, observations)
    assert observations[0].identity_diagnostics


def test_valid_generic_exact_locus_round_trips_in_inventory_and_index(tmp_path):
    exact = f"{STRAIN}|{CONTIG}|region001"
    row = _canonical(exact_locus=exact)
    _, loci = _inventory(tmp_path, [row])
    observations = _index(tmp_path, loci, row, requested="EXACT_LOCUS")
    assert loci[0].exact_locus == observations[0].exact_locus == exact


def test_source_member_cannot_override_typed_native_physical_contig(tmp_path):
    row = _native_row(NODE, "NODE_7_length_50000_cov_20")
    _, loci = _inventory(tmp_path, [row])
    observations = _index(tmp_path, loci, row, name="NODE_7_length_50000_cov_20.region001.gbk")
    _assert_unbound(loci, observations)
    assert "full_node:PATH_CONFLICT" in observations[0].identity_diagnostics


@pytest.mark.parametrize("identity,diagnostic", [
    (_canonical("CP103060.2"), "inventory:FULL_CONTIG_CONFLICT"),
    (_canonical(bgc="BGC002"), "inventory:ALIAS_CONFLICT"),
    (_canonical(full_node="NODE_8"), "inventory:NODE_TOKEN_CONFLICT"),
    (_canonical(region="region002"), "inventory:REGION_CONFLICT"),
    (_canonical(strain="OtherReference"), "inventory:NO_IDENTITY_MATCH"),
])
def test_inventory_binding_rejections_emit_fixed_diagnostics(tmp_path, identity, diagnostic):
    _, loci = _inventory(tmp_path)
    observations = _index(tmp_path, loci, identity)
    assert observations[0].binding_state == "UNBOUND"
    assert observations[0].exact_locus == ""
    assert observations[0].identity_diagnostics == diagnostic
    assert all(r["writing_gate"] == "HOLD_MISSING_GENE_LEVEL_SOURCE"
               for r in _states(loci, observations)[0])


@pytest.mark.parametrize("strain", ["Streptomyces_albus_DSM40763", "Foo", "foo", STRAIN])
def test_exact_strain_spelling_survives_inventory_index_and_outputs(tmp_path, strain):
    row = _canonical(strain=strain, exact_locus=f"{strain}|{CONTIG}|region001")
    _, loci = _inventory(tmp_path, [row])
    observations = _index(tmp_path, loci, row)
    assert loci[0].strain == observations[0].strain == strain
    assert loci[0].exact_locus == observations[0].exact_locus == row["exact_locus"]
    manifest = write_outputs(tmp_path / "outputs", loci, observations, load_contract())
    assert manifest["status"] == "PASS" and manifest["strain_count"] == 1
    for filename in ("modeb_bgc_availability.tsv", "modeb_strain_availability.tsv",
                     "modeb_evidence_observations.tsv", "modeb_section_plan.tsv"):
        with (tmp_path / "outputs" / filename).open() as handle:
            emitted = list(csv.DictReader(handle, delimiter="\t"))
        assert emitted and {r["strain"] for r in emitted} == {strain}


def test_case_distinct_strains_keep_independent_alias_and_exact_keys(tmp_path):
    _, loci = _inventory(tmp_path, [_canonical(strain=s) for s in ("Foo", "foo")])
    observations = [_index(tmp_path / s, loci, _canonical(strain=s))[0] for s in ("Foo", "foo")]
    assert {l.strain for l in loci} == {"Foo", "foo"}
    assert {o.exact_locus for o in observations} == {f"{s}|{CONTIG}|region001" for s in ("Foo", "foo")}
    assert all(o.binding_state == "EXACT_LOCUS" for o in observations)
    rows, strains, _ = _states(loci, observations)
    assert len(strains) == 2 and {r["strain"] for r in rows} == {"Foo", "foo"}
    assert all(r["gene_inventory_state"] == "EXACT_LOCUS" for r in rows)


def test_wrong_case_explicit_strain_does_not_join_or_rewrite_source(tmp_path):
    strain = "Streptomyces_albus_DSM40763"
    _, loci = _inventory(tmp_path, [_canonical(strain=strain)])
    observations = _index(tmp_path, loci, _canonical(strain=strain.upper()))
    assert observations[0].binding_state == "UNBOUND" and observations[0].exact_locus == ""
    assert observations[0].strain == strain.upper()
    assert observations[0].identity_diagnostics == "inventory:NO_IDENTITY_MATCH"
    assert _states(loci, observations)[0][0]["writing_gate"] == "HOLD_MISSING_GENE_LEVEL_SOURCE"


@pytest.mark.parametrize("wrapper,expected", [
    ("Foo_BGC001_", "EXACT_LOCUS"), ("Foo_bgc001_", "EXACT_LOCUS"),
    ("foo_BGC001_", "UNBOUND"),
])
def test_path_wrappers_preserve_strain_case_and_typed_bgc_case(tmp_path, wrapper, expected):
    _, loci = _inventory(tmp_path, [_canonical(strain="Foo")])
    source = tmp_path / "evidence/Foo/BGC001" / f"{wrapper}{CONTIG}.region001.gbk"
    source.parent.mkdir(parents=True)
    source.write_text("synthetic marker only\n")
    observations = discover_evidence(loci, load_contract(), [("members", tmp_path / "evidence")])
    assert len(observations) == 1 and observations[0].binding_state == expected
    if expected == "EXACT_LOCUS":
        assert observations[0].strain == "Foo"
        assert observations[0].exact_locus == f"Foo|{CONTIG}|region001"
    else:
        assert observations[0].exact_locus == ""
        assert observations[0].full_node == f"{wrapper}{CONTIG}"
        assert observations[0].identity_diagnostics == "inventory:FULL_CONTIG_CONFLICT"


def test_wrong_case_path_directory_does_not_localize_a_public_strain(tmp_path):
    strain = "Streptomyces_albus_DSM40763"
    _, loci = _inventory(tmp_path, [_canonical(strain=strain)])
    source = tmp_path / "evidence" / strain.upper() / f"{CONTIG}.region001.gbk"
    source.parent.mkdir(parents=True)
    source.write_text("synthetic marker only\n")
    observations = discover_evidence(loci, load_contract(), [("members", tmp_path / "evidence")])
    assert len(observations) == 1 and observations[0].binding_state == "UNBOUND"
    assert observations[0].strain == "" and observations[0].exact_locus == ""
    assert observations[0].identity_diagnostics == "inventory:NO_IDENTITY_MATCH"


@pytest.mark.parametrize("role", ["native_inventory", "native_manifest"])
def test_native_producer_roles_preserve_mixed_case_public_strain(tmp_path, role):
    strain = "Streptomyces_albus_DSM40763"
    if role == "native_inventory":
        row = _native_row(NODE, "NODE_7_length_50000_cov_20", Strain=strain)
    else:
        row = {"strain": strain, "bgc_id": "BGC001", "contig": NODE,
               "node_id": "NODE_7_length_50000_cov_20", "antismash_region": "region001"}
    _, loci = _inventory(tmp_path, [row])
    observations = _index(tmp_path, loci, row)
    assert observations[0].binding_state == "EXACT_LOCUS"
    assert observations[0].strain == loci[0].strain == strain
    assert observations[0].exact_locus == f"{strain}|{NODE.upper()}|region001"
    assert observations[0].identity_diagnostics == ""


def test_case_conflicting_strain_fields_remain_invalid(tmp_path):
    row = _canonical(strain="Foo", Strain="foo")
    path = _table(tmp_path / "conflicting_strain.tsv", [row])
    with pytest.raises(ValueError, match="strain:CONFLICT"):
        load_inventory(path)
    _, loci = _inventory(tmp_path, [_canonical(strain="Foo")])
    observations = _index(tmp_path, loci, row)
    assert observations[0].binding_state == "UNBOUND"
    assert observations[0].identity_diagnostics == "strain:CONFLICT"


def test_case_distinct_strain_paths_select_only_the_exact_inventory_label(tmp_path):
    _, loci = _inventory(tmp_path, [_canonical(strain=s) for s in ("Foo", "foo")])
    # Separate parents keep the two exact labels representable on a
    # case-insensitive filesystem while discovery still sees both together.
    for branch, strain in (("first", "Foo"), ("second", "foo")):
        source = tmp_path / "evidence" / branch / strain / f"{CONTIG}.region001.gbk"
        source.parent.mkdir(parents=True)
        source.write_text("synthetic marker only\n")
    observations = discover_evidence(loci, load_contract(), [("members", tmp_path / "evidence")])
    assert len(observations) == 2 and all(o.binding_state == "EXACT_LOCUS" for o in observations)
    assert {o.strain for o in observations} == {"Foo", "foo"}
    assert {o.exact_locus for o in observations} == {f"{s}|{CONTIG}|region001" for s in ("Foo", "foo")}
    assert all(o.identity_diagnostics == "" for o in observations)
