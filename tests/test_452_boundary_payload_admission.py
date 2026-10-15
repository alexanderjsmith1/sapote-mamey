"""Malformed boundary payloads are holds, never a clean zero-BGC audit."""
import pytest

from mamey.boundary_audit import audit_payloads


def _schema(problems):
    return [p for p in problems if p.startswith("SCHEMA ")]


@pytest.mark.parametrize("records, verdicts", [
    ({}, {}),
    ({"records": []}, {"verdicts": []}),                                   # no strain identity
    ({"strain": "T"}, {"strain": "T"}),                                    # collections undeclared
    ({"strain": "T", "records": {}}, {"strain": "T", "verdicts": []}),     # wrong collection type
    ({"strain": "T", "records": []}, {"strain": "T", "verdicts": "none"}),
    ({"strain": "", "records": []}, {"strain": "", "verdicts": []}),       # empty strain
    ([], []),                                                              # not JSON objects
    ({"strain": "T", "records": [{"products": []}]}, {"strain": "T", "verdicts": []}),  # row lacks bgc_id
    ({"strain": "T", "records": ["BGC001"]}, {"strain": "T", "verdicts": []}),          # row not an object
])
def test_malformed_payload_is_not_clean(records, verdicts):
    rc, problems = audit_payloads(records, verdicts)
    assert rc == 1
    assert _schema(problems), problems


def test_declared_empty_roster_is_a_clean_zero():
    rc, problems = audit_payloads({"strain": "T", "records": []},
                                  {"strain": "T", "verdicts": []})
    assert (rc, problems) == (0, [])


def test_normal_correspondence_is_unchanged():
    records = {"strain": "T", "records": [{"bgc_id": "BGC001", "products": ["NRPS"]}]}
    verdicts = {"strain": "T", "verdicts": [{"bgc_id": "BGC001", "lead_tier": "High",
                                             "claim_confidence": "Moderate"}]}
    rc, problems = audit_payloads(records, verdicts)
    assert (rc, problems) == (0, [])


def test_strain_mismatch_still_reported_after_admission():
    rc, problems = audit_payloads({"strain": "A", "records": []},
                                  {"strain": "B", "verdicts": []})
    assert rc == 1 and any(p.startswith("STRAIN mismatch") for p in problems)
    assert not _schema(problems)
