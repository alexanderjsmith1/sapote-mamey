"""locus_rarity_by_genus: equal total_bp merges entries only when at most one distinct explicit accession is
involved (ruled 6 Nov 2026). Two different explicit accessions stay separate and are listed for review."""
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import locus_rarity_by_genus as lr  # noqa: E402

# Genus G, five public reference entries.
ENTRIES = [
    dict(strain="a", genus="G", assembly_accession="GCA_000000001.1", total_bp="8000000"),
    dict(strain="b", genus="G", assembly_accession="GCA_000000002.1", total_bp="8000000"),
    dict(strain="CP000003", genus="G", assembly_accession="", total_bp="8000000"),
    dict(strain="d", genus="G", assembly_accession="GCA_000000004.1", total_bp="6000000"),
    dict(strain="CP000005", genus="G", assembly_accession="", total_bp="6000000"),
]
HIT = ["a", "b", "d", "CP000005"]          # entries with a region matching >= 50 % of the locus genes


def _counts():
    keys = lr.assembly_keys(ENTRIES)
    totals = defaultdict(lambda: defaultdict(set))
    for e in ENTRIES:
        totals["G"]["reference"].add(e["strain"])
    rows = [dict(genus="G", role="reference", target_strain=s, genes_matched=2, core_genes_matched=1) for s in HIT]
    (row,) = lr.rarity_table(rows, 2, 1, "G", totals, keys)
    return keys, row


def test_two_different_explicit_accessions_are_not_merged_by_length():
    keys, _row = _counts()
    assert len({keys[s][0] for s in ("a", "b", "CP000003")}) == 3
    assert keys["d"][0] == keys["CP000005"][0] == "GCA_000000004"   # one explicit accession: merged


def test_rarity_counts_follow_the_ruled_rule():
    _keys, row = _counts()
    # Old rule: a, b and CP000003 were one key -> numerator 2, denominator 2.
    assert row["genomes_with_region_ge50pct_genes_public_by_assembly"] == 3
    assert row["public_genomes_by_assembly"] == 4
    assert row["genomes_with_region_ge50pct_genes_public_by_entry"] == 4
    assert row["public_genomes_by_entry"] == 5


def test_unmerged_length_matches_are_review_candidates():
    keys, _row = _counts()
    assert [c["strain"] for c in lr.length_review_candidates(keys)] == ["CP000003", "a", "b"]
    assert [m["strain"] for m in lr.length_merges(keys)] == ["CP000005"]
    assert "at most one distinct explicit" in lr.ASSEMBLY_KEY_POLICY


def test_no_length_match_lists_nothing():
    keys = lr.assembly_keys([dict(strain="a", genus="G", assembly_accession="GCA_1.1", total_bp="10")])
    assert lr.length_merges(keys) == [] and lr.length_review_candidates(keys) == []
