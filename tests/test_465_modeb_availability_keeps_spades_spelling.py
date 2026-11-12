"""9.7.465: modeb-availability prints a full SPAdes contig in SPAdes's own spelling.

Fail-before on sealed 9.7.464: the full_node column read NODE_3_LENGTH_41000_COV_12.5, which no package, card or
four-part identity uses. Pass-after: the column keeps NODE_3_length_41000_cov_12.5, an upper-cased
input is put back into that spelling, and a mixed-case evidence row still binds to its inventory locus.
"""
import csv

from mamey.mode_b.availability import (
    build_availability, load_contract, load_evidence_index, load_inventory, normalize_node,
)

NODE = "NODE_3_length_41000_cov_12.5"   # synthetic


def test_full_node_keeps_the_package_spelling():
    assert normalize_node(NODE) == NODE
    assert normalize_node(NODE.upper()) == NODE
    assert normalize_node("node_3_Length_41000_COV_12.5") == NODE
    assert normalize_node("NODE_3") == ""            # a short token is still not a full contig


def test_output_column_can_be_copied_into_an_identity(tmp_path):
    inventory = tmp_path / "inventory.tsv"
    inventory.write_text(f"strain\tbgc\tfull_node\tregion\nSYNTHETIC_REFERENCE\tBGC003\t{NODE}\tregion001\n")
    artifact = tmp_path / "evidence.txt"
    artifact.write_text("synthetic evidence; no biological result\n")
    index = tmp_path / "index.tsv"
    with index.open("w", newline="") as handle:
        w = csv.writer(handle, delimiter="\t")
        w.writerow(["channel", "source_path", "strain", "bgc", "full_node", "region", "freshness_state"])
        w.writerow(["gene_inventory", artifact.name, "SYNTHETIC_REFERENCE", "BGC003", NODE.upper(), "region001",
                    "CURRENT"])
    loci = load_inventory(inventory)
    assert loci[0].full_node == NODE
    observations = load_evidence_index(index, loci)
    assert [o.binding_state for o in observations] != ["UNBOUND"]   # case alone never unbinds a row
    rows, _, _ = build_availability(loci, observations, load_contract())
    assert rows[0]["full_node"] == NODE
    assert rows[0]["exact_locus"] == f"SYNTHETIC_REFERENCE|{NODE}|region001"
