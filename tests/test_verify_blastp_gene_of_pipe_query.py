"""Regression: verify_blastp._gene_of must extract the gene from a pipe-query defline.

Found by gating real returned wave-2 results: deflines carry the locus as a `gene=ctgN_M`
KEY in the middle (…|gene=ctg13_21|node=…|reason=biosynthetic), so the old rsplit('|')[-1]
returned the constant trailing field ('reason=biosynthetic') and genes_covered collapsed to 1 —
silently breaking the --expect coverage (MISSING/PARTIAL) assertion, the gate's whole point.
"""
import scripts.verify_blastp as V


def test_gene_from_gene_equals_key_in_middle():
    q = "AS-168|BGC005|slot=core|role=core|gene=ctg13_21|node=NODE_13|region=region002|reason=biosynthetic"
    assert V._gene_of(q) == "ctg13_21"


def test_gene_backward_compatible_formats():
    assert V._gene_of("ctg12_38") == "ctg12_38"          # bare ctg token
    assert V._gene_of("query|ctg9_4") == "ctg9_4"        # ctg as last pipe field
    assert V._gene_of("plain_query") == "plain_query"    # no ctg / no pipe -> whole id


def test_distinct_genes_not_collapsed():
    rows = [
        "A|B|gene=ctg1_1|reason=x",
        "A|B|gene=ctg1_2|reason=x",
        "A|B|gene=ctg1_3|reason=x",
    ]
    assert len({V._gene_of(r) for r in rows}) == 3
