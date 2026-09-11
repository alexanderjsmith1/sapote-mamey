from mamey.modeb_publication_gate import _section_disposition_uniform_findings


def matrix(distinct_basis=False):
    return "".join(
        f"| {n} | SUBSTANTIVE | {'source ' + str(n) if distinct_basis else 'source'} | RETAIN | scope |\n"
        for n in range(1, 51))


def test_uniformity_is_visible_but_not_an_error():
    findings = _section_disposition_uniform_findings(matrix())
    assert len(findings) == 1
    assert findings[0]["code"] == "SECTION_DISPOSITION_TABLE_UNIFORM"
    assert findings[0]["severity"] == "WARN"
    assert "does not establish an error" in findings[0]["message"]


def test_distinct_evidence_can_legitimately_share_state():
    finding = _section_disposition_uniform_findings(matrix(True))[0]
    assert finding["severity"] == "WARN"
    assert "50 distinct evidence bases" in finding["found"]


def test_mixed_states_are_not_certified_complete():
    # A silent heuristic is not a scientific PASS; it returns no acceptance record.
    mixed = matrix().replace("| 1 | SUBSTANTIVE |", "| 1 | UNRESOLVED |")
    assert _section_disposition_uniform_findings(mixed) == []
