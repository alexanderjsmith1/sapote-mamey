"""A failed HMM reader must remain unavailable rather than a no-hit result."""
import pytest

from mamey import antismash_evidence as evidence
from mamey import antismash_tables as tables


@pytest.fixture
def empty_other_tables(monkeypatch):
    monkeypatch.setattr(tables, "extract_cds_features", lambda _: [])
    monkeypatch.setattr(tables, "extract_domain_features", lambda _: [])
    monkeypatch.setattr(tables, "extract_antismash_version", lambda _: "engineering-fixture")
    monkeypatch.setattr("mamey.degradation.record", lambda *args, **kwargs: None)


@pytest.mark.parametrize("error", [OSError, ValueError])
def test_structured_hmm_state_is_unavailable(empty_other_tables, monkeypatch, error):
    def unavailable(_):
        raise error("injected unavailable source")
    monkeypatch.setattr(evidence, "extract_gbk_pfam_hits", unavailable)
    result = tables.build_structured_tables("unused-injected-fixture", {}, [])
    assert result["hmm"] == []
    assert result["hmm_status"] == "UNAVAILABLE_HMM_EXTRACTION_ERROR"
    assert {"surface": "HMM_pfam_tigrfam", "error": error.__name__} in result["parse_errors"]


def test_successful_empty_hmm_input_keeps_no_hit_state(empty_other_tables):
    result = tables.build_structured_tables(
        "unused-precomputed-fixture", {"gbk_pfam_hits": {}}, [],
    )
    assert result["hmm_status"] == "NULL_NO_PFAM_TIGRFAM_HITS"
    assert result["parse_errors"] == []
