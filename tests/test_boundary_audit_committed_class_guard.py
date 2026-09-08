"""Regression: boundary_audit must mirror the committed-class guard.

Guards against the v9.7.23 over-flag where boundary_audit reported an EXCLUSION
"miss" on every multi-class saccharide-tailored BGC, even though
scoring.standing_rule_for correctly returns "" (no downgrade) for committed leads.

Real-world trigger: Micromonospora fiedleri MG-37 (GCA_016774385.1) BGC030
(NRPS;PKS;RiPP;T1PKS;...;saccharide;thioamitides), rated Exceptional, was flagged
as an exclusion miss. It is not one — saccharide is a tailoring arm.
"""
from mamey.boundary_audit import audit_payloads


def _verdict(bgc_id, tier="High", conf="Moderate"):
    return {"bgc_id": bgc_id, "lead_tier": tier, "claim_confidence": conf}


def test_committed_saccharide_lead_not_overflagged():
    """A committed NRPS+saccharide lead with no downgrade is NOT an exclusion miss."""
    records = {"strain": "T", "records": [
        {"bgc_id": "BGC030", "products": ["NRPS", "PKS", "RiPP", "T1PKS",
                                          "saccharide", "thioamitides"]},
    ]}
    verdicts = {"strain": "T", "verdicts": [_verdict("BGC030", "Exceptional")]}
    _, problems = audit_payloads(records, verdicts)
    assert not [p for p in problems if p.startswith("EXCLUSION")], problems


def test_pure_saccharide_miss_still_flags():
    """A genuine pure-saccharide BGC that escaped downgrade MUST still flag."""
    records = {"strain": "T", "records": [
        {"bgc_id": "BGC001", "products": ["saccharide"]},
    ]}
    verdicts = {"strain": "T", "verdicts": [_verdict("BGC001", "Inventory", "Low")]}
    _, problems = audit_payloads(records, verdicts)
    assert [p for p in problems if p.startswith("EXCLUSION") and "BGC001" in p], problems


def test_mixed_cohort_only_pure_excluded_flags():
    """In a mixed set, only the pure-excluded record flags; committed leads pass."""
    records = {"strain": "T", "records": [
        {"bgc_id": "PURE", "products": ["saccharide"]},
        {"bgc_id": "LEAD", "products": ["RiPP", "lanthipeptide-class-iii", "saccharide"]},
    ]}
    verdicts = {"strain": "T", "verdicts": [
        _verdict("PURE", "Inventory", "Low"),
        _verdict("LEAD", "High"),
    ]}
    _, problems = audit_payloads(records, verdicts)
    excl = [p for p in problems if p.startswith("EXCLUSION")]
    assert any("PURE" in p for p in excl), excl
    assert not any("LEAD" in p for p in excl), excl
