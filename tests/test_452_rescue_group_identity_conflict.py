"""A region alias that HIGH pairs carry on two different contigs is an identity conflict.

Before, candidate_groups kept whichever row came last, so two loci under one alias (for example rows from two
genomes) merged into one group member with the last row's contig.
"""
import pytest

from mamey.rescue_groups import candidate_groups


def _pair(a, ca, b, cb, edge_a="Edge", products_a="NRPS", conf="HIGH_RG_GMCI_RESCUE"):
    return {"pair": f"{a}+{b}", "bgc_a": a, "bgc_b": b, "contig_a": ca, "contig_b": cb, "edge_a": edge_a,
            "edge_b": "Full-contig", "products_a": products_a, "products_b": "NRPS", "rggmci_confidence": conf}


@pytest.mark.parametrize("second", [
    _pair("A", "ctg9", "C", "ctg3"),       # alias A on a different contig
    _pair("C", "ctg3", "A", "ctg9"),       # the same conflict on the other side of the pair
])
def test_conflicting_rows_for_one_alias_are_refused(second):
    with pytest.raises(ValueError, match="RGGMCI_GROUP_IDENTITY_CONFLICT: A"):
        candidate_groups([_pair("A", "ctg1", "B", "ctg2"), second])


def test_consistent_repeats_still_group():
    groups = candidate_groups([_pair("A", "ctg1", "B", "ctg2"), _pair("A", "ctg1", "C", "ctg3")])
    assert len(groups) == 1
    assert [(r["bgc_id"], r["contig"]) for r in groups[0]["regions"]] == [("A", "ctg1"), ("B", "ctg2"), ("C", "ctg3")]

