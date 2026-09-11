from mamey.ecology_context import build_bgc_ecology_context


def test_context_is_locus_scoped_and_keeps_missing_scan_typed():
    identity = {"strain": "AS-TEST", "node_or_contig": "NODE_1_length_100", "region": "region001", "bgc_alias": "BGC001"}
    result = build_bgc_ecology_context(identity, governed_locus_tags=["gene001"], tfbs={"hits": [{"target_locus": "gene001", "motif": "DasR_like_palindrome"}]})
    assert result["complete_identity"] == "AS-TEST / NODE_1_length_100 / region001 / BGC001"
    assert result["tfbs_ecology_rows"][0]["signal_present"] == "PRESENT"
    assert result["tfbs_ecology_rows"][1]["signal_present"] == "ABSENT"
    missing = build_bgc_ecology_context(identity)
    assert {r["signal_present"] for r in missing["tfbs_ecology_rows"]} == {"NOT_SCORED"}


def test_identity_is_fail_closed():
    try:
        build_bgc_ecology_context({"strain": "AS-TEST", "bgc_alias": "BGC001"})
    except ValueError as exc:
        assert "complete" in str(exc)
    else:
        raise AssertionError("incomplete identity was accepted")
