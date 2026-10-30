"""Metadata-only normalization retains deposited taxon text across passes."""
from copy import deepcopy

import pytest

from mamey.npatlas_provision import normalize_record


@pytest.mark.parametrize("organism", [
    {"taxon": {"name": "deposited text placeholder"}},
    {"taxon_name": "deposited text placeholder"},
])
def test_normalization_retains_taxon_text_on_repeated_passes(organism):
    source = {"original_name": "engineering placeholder", "origin_organism": organism}
    original = deepcopy(source)
    once = normalize_record(source)
    assert once["origin_organism"]["taxon_name"] == "deposited text placeholder"
    assert normalize_record(once) == once
    assert source == original


@pytest.mark.parametrize("name", ["authoritative deposited text", "", None])
def test_nested_source_name_keeps_precedence(name):
    result = normalize_record({"origin_organism": {
        "taxon": {"name": name}, "taxon_name": "superseded text",
    }})
    assert result["origin_organism"]["taxon_name"] == name
