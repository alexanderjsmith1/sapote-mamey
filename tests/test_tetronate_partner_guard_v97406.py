from mamey.antismash_evidence import tetronate_cassette_completeness


def test_edge_partner_ksiii_is_ambiguous_until_exactly_bound():
    result = tetronate_cassette_completeness(
        {"FkbH", "ACP"}, {"fabH"}, edge_truncated=True
    )
    assert result["grade"] == "TET_CASSETTE_INDETERMINATE"
    assert result["ambiguous_partner"] is True
    assert "AMBIGUOUS_PARTNER" in result["reason"]


def test_exact_rggmci_partner_can_supply_edge_closure():
    result = tetronate_cassette_completeness(
        {"FkbH", "ACP"}, {"fabH"}, edge_truncated=True,
        partner_binding_state="EXACT_RGGMCI_PARTNER",
    )
    assert result["grade"] == "TET_CASSETTE_COMPLETE"
    assert result["ambiguous_partner"] is False


def test_same_cluster_ksiii_does_not_need_partner_binding():
    result = tetronate_cassette_completeness(
        {"FkbH", "ACP", "fabH"}, edge_truncated=True
    )
    assert result["grade"] == "TET_CASSETTE_COMPLETE"
    assert result["ambiguous_partner"] is False
