"""A requested region that is not on the record is an identity hold, never region001.

`_region_index` took the first run of digits and fell back to area 0 when it was out of range.
On a Saccharothrix draft, contig LGED01000002.1 has 3 regions: "region004" and
"LGED01000002.1.region003" both resolved to region001, and the ledger reported region001's
KnownClusterBlast label under the requested name.
"""
import pytest

from mamey.tab_reconcile import _clusterblast_json_summary, _gene_overview_summary, _region_index

REC = {
    "id": "LGED01000002.1",
    "areas": [{"start": 0, "end": 10, "products": ["NRPS"]},
              {"start": 20, "end": 30, "products": ["T1PKS"]},
              {"start": 40, "end": 50, "products": ["terpene"]}],
    "features": [],
    "modules": {"antismash.modules.clusterblast": {"knowncluster": {"results": [
        {"region_number": 1, "ranking": [[{"accession": "BGC_ONE", "description": "first"}, {}]]},
        {"region_number": 3, "ranking": [[{"accession": "BGC_THREE", "description": "third"}, {}]]},
    ]}}},
}


def test_contig_id_digits_are_not_a_region_number():
    assert _region_index(REC, "LGED01000002.1.region003") == 2
    assert _region_index(REC, "LGED01000002.1.region003.gbk") == 2


@pytest.mark.parametrize("wanted", ["region004", "4", "region000", "BGC", "LGED01000002.1"])
def test_unknown_region_is_a_hold(wanted):
    with pytest.raises(SystemExit, match="IDENTITY_HOLD"):
        _region_index(REC, wanted)


def test_clusterblast_entry_is_chosen_by_its_region_number():
    n, raw = _clusterblast_json_summary(REC, "knowncluster", 2)
    assert n == 1 and "third" in raw and "first" not in raw
    # region002 has no entry of its own: it must not borrow region003's (or region001's).
    assert _clusterblast_json_summary(REC, "knowncluster", 1) == (0, "NO_RESULTS_FOR_REGION")


def test_gene_overview_refuses_an_area_off_the_record():
    with pytest.raises(SystemExit, match="IDENTITY_HOLD"):
        _gene_overview_summary(REC, 5)
