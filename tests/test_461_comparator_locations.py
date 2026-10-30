"""Wrapped comparator feature coordinates must survive GenBank ingestion."""
import pytest
from mamey.comparators.antismash_ingest import parse_gbk_features

@pytest.mark.parametrize("location, expected", [
    ("join(100..200,\n                     400..500)", (100, 500, "+")),
    ("complement(join(100..200,\n                     400..500))", (100, 500, "-")),
    ("100..500", (100, 500, "+")),
])
def test_wrapped_feature_location(location, expected):
    text = ("LOCUS       fixture 600 bp DNA linear\n"
            "FEATURES             Location/Qualifiers\n"
            f"     CDS             {location}\n"
            '                     /locus_tag="fixture_gene"\n'
            "ORIGIN\n        1 acgt\n//\n")
    [feature] = parse_gbk_features(text)
    assert (feature.start, feature.end, feature.strand) == expected
    assert feature.qualifiers["locus_tag"] == ["fixture_gene"]
