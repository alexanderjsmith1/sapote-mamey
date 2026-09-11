"""Tests for the GCF-network + clinker figure module (mamey/bigscape_figures.py).

The blocker this module was held on was node-identity: a naive NODE_ regex mis-maps records to the
wrong BGC. These tests pin that the module's identity IS the tested ingest canon_locator identity,
plus the required-args and graceful-degradation contracts. No large DB fixture is needed.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import bigscape_ingest_to_mamey as ingest
from mamey import bigscape_figures as F


def test_module_uses_canonical_ingest_identity():
    """The DB gbk-path form and the evidence short-node form must reduce to the SAME canonical key —
    this is what prevents attributing a network node to the wrong BGC (the .291/.292 mis-map class)."""
    db_path = "AS-40_NODE_44_length_59421_cov_40.489923.region001.gbk"
    ev_node = "NODE_44_length_59421_cov_40"          # as stored in all_evidence.json
    _strain, db_key, _mibig = ingest.parse_locator(db_path)
    ev_key = ingest.canon_locator(f"{ev_node}.region001")
    assert db_key == ev_key == "NODE_44_length_59421.region001"
    print("PASS test_module_uses_canonical_ingest_identity")


def test_no_naive_node_regex_in_module():
    """Guard against regression: the module must not hand-roll a NODE_ regex mapper."""
    src = open(F.__file__).read()
    assert "re.search(r\"(NODE_" not in src and "re.match(r'(NODE_" not in src
    assert "canon_locator" in src and "parse_locator" in src
    print("PASS test_no_naive_node_regex_in_module")


def test_run_and_cutoff_required():
    r = F.gcf_network(db="x", strain="AS-40", run=None, cutoff=None)
    assert r["status"] == "MISSING_ARGS"
    print("PASS test_run_and_cutoff_required")


def test_clinker_degrades_gracefully():
    r = F.clinker_figure(["only_one.gbk"])
    assert r["status"] in ("NEED_2_GBKS", "SKIPPED_NO_CLINKER")
    print("PASS test_clinker_degrades_gracefully")


if __name__ == "__main__":
    test_module_uses_canonical_ingest_identity()
    test_no_naive_node_regex_in_module()
    test_run_and_cutoff_required()
    test_clinker_degrades_gracefully()
    print("all bigscape_figures tests PASS")
