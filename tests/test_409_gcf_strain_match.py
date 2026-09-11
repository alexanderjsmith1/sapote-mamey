"""Fail-before / pass-after for CLAUDE_409_gcf_strain_match.

Bug: tools/bigscape_ingest_to_mamey.parse_locator() only recognised SPAdes-style
`NODE_<n>_length_<L>` contig names (the module-level LOCATOR regex). Region GBKs whose
contig is an NCBI WGS accession (e.g. `RB68_WEGH01000001.1.region006.gbk`) returned
`loc=None`, so mamey/bigscape_figures.gcf_network() dropped every record and reported
`{'status':'NO_RECORDS', ...}` on a DB that actually held 60 RB68 region records.

Run with the sealed-.408 tree on sys.path (tools/ importable):
    pytest test_409_gcf_strain_match.py
Pristine .408 -> the WGS test FAILS (loc is None). Patched -> all pass.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # unused when run against a tree
from tools import bigscape_ingest_to_mamey as I  # noqa: E402  (adjust sys.path to the tree under test)


def test_wgs_accession_contig_now_parses():
    # THE FIX: NCBI WGS accession contig (no NODE_ token) must yield a locator, not None.
    strain, loc, is_mibig = I.parse_locator("/x/RB68_WEGH01000001.1.region006.gbk")
    assert strain == "RB68"
    assert is_mibig is False
    assert loc == "WEGH01000001.1.region006"   # pristine .408 returns None here -> RED


def test_spades_node_contig_unchanged():
    # Regression guard: cov-independent NODE_ canonicalisation is byte-identical to .408.
    _s, loc, _m = I.parse_locator("/x/AS-40_NODE_402_length_4883_cov_73.020183.region001.gbk")
    assert loc == "NODE_402_length_4883.region001"
    _s2, loc2, _m2 = I.parse_locator("/x/AS-40_NODE_402_length_4883_cov_73.20183.region001.gbk")
    assert loc2 == "NODE_402_length_4883.region001"


def test_mibig_reference_unchanged():
    label, ident, is_mibig = I.parse_locator("/x/BGC0001234.gbk")
    assert (label, ident, is_mibig) == ("MIBiG", "BGC0001234", True)
