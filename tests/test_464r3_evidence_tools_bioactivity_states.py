"""The hold code is not an admitted metadata state; the locator grammar is as documented."""
import pytest
from mamey.bioactivity_metadata import BioactivityMetadataError, normalize_bioactivity, validate_receipt_locator


def _obj(state, observation="UNKNOWN"):
    return {"schema_version": "bioactivity_metadata_v1", "metadata_state": state, "observation_state": observation,
            "usage_scope": "PRODUCTION", "assays": [], "compound_linkage": "NOT_ESTABLISHED"}


def test_hold_code_is_refused_as_a_state():
    with pytest.raises(BioactivityMetadataError, match="unknown metadata_state"):
        normalize_bioactivity(_obj("BIOACTIVITY_LEGACY_SHAPE_HOLD"))


def test_supplied_unknown_still_admitted():
    assert normalize_bioactivity(_obj("SUPPLIED_UNKNOWN"))["metadata_state"] == "SUPPLIED_UNKNOWN"


def test_locator_grammar_matches_the_page():
    assert validate_receipt_locator("receipts/version..old") == "receipts/version..old"
    with pytest.raises(BioactivityMetadataError):
        validate_receipt_locator("receipts/../x")
