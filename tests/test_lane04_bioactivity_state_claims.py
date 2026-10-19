"""State assertions cannot invent a measured outcome or locus/compound linkage."""
import pytest
from mamey.bioactivity_metadata import normalize_bioactivity,not_supplied,BioactivityMetadataError

@pytest.mark.parametrize("metadata,expected",[("NOT_SUPPLIED","NOT_OBSERVED"),("MEASURED_POSITIVE","POSITIVE"),("MEASURED_NEGATIVE","NEGATIVE")])
@pytest.mark.parametrize("observation",["NOT_OBSERVED","UNKNOWN","POSITIVE","NEGATIVE"])
def test_state_observation_consistency(metadata,expected,observation):
    value=not_supplied();value.update(metadata_state=metadata,observation_state=observation)
    if observation==expected:
        assert normalize_bioactivity(value)==value
    else:
        with pytest.raises(BioactivityMetadataError,match="states conflict"):
            normalize_bioactivity(value)

@pytest.mark.parametrize("linkage",["CONFIRMED_BGC_PRODUCTION","COMPOUND_IDENTIFIED",None,True])
def test_no_linkage_authority_in_strain_metadata(linkage):
    value=not_supplied();value["compound_linkage"]=linkage
    with pytest.raises(BioactivityMetadataError,match="separate governed workflow"):
        normalize_bioactivity(value)

def test_legacy_positive_word_is_unknown_context():
    value=normalize_bioactivity("synthetic positive screen text")
    assert value["observation_state"]=="UNKNOWN" and value["compound_linkage"]=="NOT_ESTABLISHED"
