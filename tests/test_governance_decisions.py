"""v9.7.361 (R4): governance decisions must be machine-checkable, not prose.

Rationale (from MEMO_AS_strain_disclosure_2026-08-10): the AS-series disclosure decision that retired
the strain-ID privacy guard exists only as prose in TIER_DIFFERENCES.md plus one source comment. Prose
cannot expire, cannot be evaluated, and cannot distinguish an owner ruling from a later restatement.
STRICT_HEALTH_WAIVER.json shows the working alternative: a signed record with a condition that
invalidates it automatically -- which is exactly what forced the conscious re-sign at this cut.

These tests pin the SHAPE of the record, not the decision. They must never assert that GOV-001 is
approved; that is the owner's call and the record is deliberately PENDING.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GOV = ROOT / "GOVERNANCE_DECISIONS.json"
REQUIRED = {"id", "topic", "status", "asserted_signer", "asserted_date",
            "invalidates_when", "condition_currently_true", "record_type"}
VALID_STATUS = {"ACTIVE", "PENDING_OWNER_CONFIRMATION", "REPUDIATED", "SUPERSEDED", "EXPIRED"}


def _load():
    if not GOV.exists():
        pytest.skip("GOVERNANCE_DECISIONS.json not present in this tier")
    return json.loads(GOV.read_text())


def test_file_is_valid_json_with_a_schema_version():
    d = _load()
    assert d.get("schema_version", "").startswith("sapote.governance_decisions/")
    assert isinstance(d.get("decisions"), list) and d["decisions"]


def test_every_decision_carries_the_required_fields():
    for g in _load()["decisions"]:
        missing = REQUIRED - set(g)
        assert not missing, f"{g.get('id', '?')} missing required field(s): {sorted(missing)}"


def test_status_is_from_the_controlled_vocabulary():
    for g in _load()["decisions"]:
        assert g["status"] in VALID_STATUS, f"{g['id']}: unknown status {g['status']!r}"


def test_every_decision_has_a_mechanically_evaluable_expiry_condition():
    """The whole point: a decision that cannot expire will not expire, even after its premise does."""
    for g in _load()["decisions"]:
        cond = g["invalidates_when"]
        assert isinstance(cond, str) and cond.strip(), f"{g['id']}: empty invalidates_when"
        assert isinstance(g["condition_currently_true"], bool), \
            f"{g['id']}: condition_currently_true must be a bool, not prose"


def test_a_decision_whose_condition_is_true_is_not_marked_active():
    """If the invalidating condition holds, the decision must NOT read as good standing."""
    for g in _load()["decisions"]:
        if g["condition_currently_true"]:
            assert g["status"] != "ACTIVE", (
                f"{g['id']}: invalidating condition is currently TRUE but status is ACTIVE — "
                "this is exactly the failure mode the record exists to prevent"
            )


def test_prose_only_records_cannot_be_active():
    """A decision with no primary artifact is an assertion until an owner confirms it."""
    for g in _load()["decisions"]:
        if g.get("record_type") == "PROSE_ONLY":
            assert g["status"] != "ACTIVE", f"{g['id']}: PROSE_ONLY record marked ACTIVE"
            assert g.get("why_pending"), f"{g['id']}: PROSE_ONLY record must explain why it is pending"


def test_gov001_is_present_and_pending_not_silently_resolved():
    """Guards against a future cut quietly flipping the AS decision without an owner ruling."""
    g = next((x for x in _load()["decisions"] if x["id"] == "GOV-001"), None)
    assert g is not None, "GOV-001 (AS-series disclosure) must remain on the record"
    # v9.7.408: resolved DELIBERATELY alongside the ruling, as this assertion asked. The release owner
    # ruled 2026-08-28 (reaffirmed 2026-09-04) that cohort identifiers ship and genomes / unpublished
    # novelty findings / third-party personal identifiers do not; the record is REASONED_WITH_EVIDENCE
    # with a primary artifact, so it may be ACTIVE. Flipping it back, or to any other status, without a
    # new owner ruling is the thing this test now guards.
    assert g["status"] == "ACTIVE", (
        "GOV-001 status changed from the 2026-08-28 owner ruling (ACTIVE). Only the release owner may "
        "change it; if that has happened, update this test deliberately alongside the ruling."
    )
    assert g.get("record_type") == "REASONED_WITH_EVIDENCE" and g.get("primary_artifact")
    assert g.get("asserted_signer") and g.get("asserted_date") == "2026-08-28"
    assert g.get("remediation_available"), "GOV-001 must state how the effect is reversed"
