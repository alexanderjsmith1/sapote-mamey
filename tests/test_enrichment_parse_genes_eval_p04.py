"""EVAL-P04/P09 (v9.7.326+): parse_genes must not crash card enrichment on a malformed gene-table
row — a missing locus_tag (was r["locus_tag"] -> KeyError, past the function's try/except) or a
non-numeric aa_length like "123 aa" / "1,024" (was int() -> ValueError).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mamey.enrichment_sections import parse_genes


def test_missing_locus_tag_row_is_skipped_not_crashed():
    rows = [
        {"sec_met_domains": "PKS_KS", "aa_length": "400"},                    # no locus_tag -> skip
        {"locus_tag": "ctg1_10", "sec_met_domains": "PKS_KS", "aa_length": "400"},
    ]
    genes = parse_genes(rows)
    assert [g.locus for g in genes] == ["ctg1_10"]


def test_non_numeric_aa_length_tolerated():
    rows = [
        {"locus_tag": "ctg1_10", "sec_met_domains": "PKS_KS", "aa_length": "400 aa"},
        {"locus_tag": "ctg1_11", "sec_met_domains": "Condensation", "aa_length": "1,024"},
        {"locus_tag": "ctg1_12", "sec_met_domains": "AMP-binding", "aa_length": ""},
    ]
    genes = parse_genes(rows)
    aa = {g.locus: g.aa for g in genes}
    assert aa == {"ctg1_10": 400, "ctg1_11": 1024, "ctg1_12": 0}
