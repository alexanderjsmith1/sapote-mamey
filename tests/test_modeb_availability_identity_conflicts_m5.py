"""Synthetic availability joins must preserve full physical-locus conflicts."""
import csv
import pytest

from mamey.mode_b.availability import (
    build_availability, load_contract, load_evidence_index, load_inventory,
)


NODE = "NODE_7_length_50000_cov_20.5"


def fixture(tmp_path, node):
    inventory = tmp_path / "inventory.tsv"
    inventory.write_text("strain\tbgc\tfull_node\tregion\n"
                         f"SYNTHETIC_REFERENCE\tBGC001\t{NODE}\tregion001\n")
    artifact = tmp_path / "evidence.txt"
    artifact.write_text("synthetic evidence; no biological result\n")
    index = tmp_path / "index.tsv"
    with index.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["channel", "source_path", "strain", "bgc", "full_node",
                         "region", "freshness_state"])
        writer.writerow(["gene_inventory", artifact.name, "SYNTHETIC_REFERENCE",
                         "BGC001", node, "region001", "CURRENT"])
    return load_inventory(inventory), index


@pytest.mark.parametrize("node", [
    "NODE_7_length_60000_cov_20.5",
    "NODE_7_length_50000_cov_21.0",
    "NODE_8_length_50000_cov_20.5",
    "NODE_8",
])
def test_conflicting_contig_is_not_rescued_by_matching_alias(tmp_path, node):
    loci, index = fixture(tmp_path, node)
    observations = load_evidence_index(index, loci)
    assert len(observations) == 1
    assert observations[0].binding_state == "UNBOUND"
    rows, _, sections = build_availability(loci, observations, load_contract())
    assert rows[0]["gene_inventory_state"] == "UNBOUND"
    assert rows[0]["writing_gate"] == "HOLD_MISSING_GENE_LEVEL_SOURCE"
    assert all("gene_inventory" not in row["available_streams"].split(";") for row in sections)


@pytest.mark.parametrize("node,state", [(NODE, "EXACT_LOCUS"), ("", "ALIAS_BOUND"),
                                        ("NODE_7", "ALIAS_BOUND")])
def test_nonconflicting_exact_and_partial_sources_keep_typed_binding(tmp_path, node, state):
    loci, index = fixture(tmp_path, node)
    observations = load_evidence_index(index, loci)
    assert observations[0].binding_state == state
    rows, _, _ = build_availability(loci, observations, load_contract())
    assert rows[0]["gene_inventory_state"] == state
    assert rows[0]["writing_gate"] == "PASS_FOR_GAP_AWARE_AUTHORING"


def test_same_alias_on_two_physical_loci_refuses_inventory(tmp_path):
    inventory = tmp_path / "duplicate.tsv"
    inventory.write_text("strain\tbgc\tfull_node\tregion\n"
                         f"SYNTHETIC_REFERENCE\tBGC001\t{NODE}\tregion001\n"
                         "SYNTHETIC_REFERENCE\tBGC001\tNODE_8_length_50000_cov_20.5\tregion001\n")
    with pytest.raises(ValueError, match="Inventory alias is not unique"):
        load_inventory(inventory)
