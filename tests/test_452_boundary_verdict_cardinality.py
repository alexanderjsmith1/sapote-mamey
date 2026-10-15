"""Two verdicts for one BGC fail the boundary audit; a later row cannot hide an earlier one."""
import itertools

from mamey.boundary_audit import audit_payloads


def _verdict(bgc_id, tier="High", conf="Moderate", **extra):
    row = {"bgc_id": bgc_id, "lead_tier": tier, "claim_confidence": conf}
    row.update(extra)
    return row


def _records(*ids):
    return {"strain": "T", "records": [{"bgc_id": i, "products": ["NRPS"]} for i in ids]}


def _dup_problems(problems):
    return [p for p in problems if p.startswith("DUPLICATE bgc_id in verdicts")]


def test_valid_last_verdict_cannot_hide_invalid_first():
    verdicts = {"strain": "T", "verdicts": [_verdict("BGC001", tier="Legendary"),
                                            _verdict("BGC001")]}
    rc, problems = audit_payloads(_records("BGC001"), verdicts)
    assert rc == 1
    dup = _dup_problems(problems)
    assert len(dup) == 1, problems
    assert "2 verdict rows for 1 unique loci" in dup[0]
    assert "conflicting=['BGC001']" in dup[0] and "identical=[]" in dup[0]


def test_identical_duplicate_verdicts_still_fail():
    verdicts = {"strain": "T", "verdicts": [_verdict("BGC001"), _verdict("BGC001"),
                                            _verdict("BGC002")]}
    rc, problems = audit_payloads(_records("BGC001", "BGC002"), verdicts)
    assert rc == 1
    dup = _dup_problems(problems)
    assert dup and "3 verdict rows for 2 unique loci" in dup[0]
    assert "conflicting=[]" in dup[0] and "identical=['BGC001']" in dup[0]


def test_duplicate_records_and_verdicts_both_reported():
    records = {"strain": "T", "records": [{"bgc_id": "BGC001", "products": ["NRPS"]},
                                          {"bgc_id": "BGC001", "products": ["NRPS"]}]}
    verdicts = {"strain": "T", "verdicts": [_verdict("BGC001"), _verdict("BGC001", conf="Low")]}
    rc, problems = audit_payloads(records, verdicts)
    assert rc == 1
    assert any(p.startswith("DUPLICATE bgc_id in records") for p in problems), problems
    assert _dup_problems(problems), problems


def test_every_source_order_fails_the_same_way():
    rows = [_verdict("BGC001"), _verdict("BGC001", tier="Low"), _verdict("BGC002")]
    seen = set()
    for perm in itertools.permutations(rows):
        rc, problems = audit_payloads(_records("BGC001", "BGC002"),
                                      {"strain": "T", "verdicts": list(perm)})
        assert rc == 1
        seen.add(tuple(_dup_problems(problems)))
    assert len(seen) == 1, seen


def test_one_verdict_per_bgc_has_no_duplicate_problem():
    verdicts = {"strain": "T", "verdicts": [_verdict("BGC001"), _verdict("BGC002")]}
    _, problems = audit_payloads(_records("BGC001", "BGC002"), verdicts)
    assert not _dup_problems(problems), problems
