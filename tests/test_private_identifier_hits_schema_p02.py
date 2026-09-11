"""SCHEMA-P02 (v9.7.326+): the public-scaffold private-strain-ID guard must catch the real
private prefixes, not just 3-digit AS. The old default AS-\\d{3} missed the 2-digit strains
(AS-40/AS-74), 4-digit AS, and AJS-/PENDING- entirely — a public-tier leak in scaffold specs.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mamey.directed_pks_study import private_identifier_hits


def _hit_values(obj):
    return {h for _, h in private_identifier_hits(obj)}


def test_catches_two_digit_and_four_digit_AS_and_ajs_pending():
    # each was MISSED by the old AS-\d{3} default
    for sid in ("AS-40", "AS-74", "AS-1234", "AJS-9", "AJS-123", "PENDING-1", "PENDING-004"):
        assert private_identifier_hits({"strain_id": sid}), f"{sid} not flagged as private"


def test_still_catches_three_digit_AS_705():
    # the existing contract must not regress
    assert private_identifier_hits({"strain_id": "AS-705"})


def test_placeholder_and_public_and_cassette_ids_stay_clean():
    # AS-XXX placeholder, SID (public), CAS-/MCAS- cassette IDs, LAS- compound tails, AS-1 prose
    for ok in ("AS-XXX", "SID4923", "SID10815", "CAS-016", "MCAS-004", "LAS-21", "AS-1"):
        assert _hit_values({"strain_id": ok}) == set(), f"{ok} wrongly flagged: {_hit_values({'strain_id': ok})}"


def test_as1_prose_not_flagged():
    # AS-1 is documented prose (single digit), excluded like redact_public_tier's AS-\d{2,4}
    assert private_identifier_hits({"note": "see AS-1 above"}) == []
