"""Known/purified compound background-control branch."""

from __future__ import annotations

from dataclasses import dataclass

@dataclass
class BackgroundControl:
    bgc_id: str
    node: str
    reason: str
    purified_status: str
    activity_mapping_status: str
    reentry_condition: str

def streptophenazine_background() -> BackgroundControl:
    return BackgroundControl(
        bgc_id="BGC011",
        node="NODE_11",
        reason="streptophenazines purified; active antifungal likely elsewhere",
        purified_status="purified_known_branch",
        activity_mapping_status="excluded_from_primary_antifungal_hypothesis",
        reentry_condition="re-enter only if purified streptophenazines reproduce target antifungal activity",
    )
