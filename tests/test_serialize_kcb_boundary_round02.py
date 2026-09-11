"""Regression: boundary serialization must not depend on mutating triage records."""

from __future__ import annotations

import json
from dataclasses import dataclass
from types import SimpleNamespace

from mamey.serialize import write_boundary_payloads


@dataclass(frozen=True)
class FrozenTriage:
    bgc_id: str
    ab_score: float = 1.0
    af_score: float = 2.0
    novelty_score: float = 3.0
    lead_tier: str = "Inventory"
    claim_confidence: str = "Unknown"
    corrected_rank: int | None = None
    standing_rule_flag: str = ""
    primary_metabolism_flag: bool = False


def _bgc(bgc_id, cumulative):
    return SimpleNamespace(
        bgc_id=bgc_id,
        contig="NODE_1_length_1000_cov_1",
        node_id="NODE_1",
        user_label=f"NODE_1_length_1000_cov_1 region001 ({bgc_id})",
        region_number=1,
        antismash_region="region001",
        edge_status="interior",
        products=[],
        mibig_hits=[],
        architecture_confidence="unknown",
        architecture_capacity="",
        kcb_top=None,
        kcb_cumulative=cumulative,
        kcb_evidence_state="UNKNOWN_KCB",
    )


def test_write_boundary_uses_source_kcb_without_mutating_frozen_triage(tmp_path):
    _, verdict_path = write_boundary_payloads(
        tmp_path, "GENERIC-TEST", [_bgc("BGC001", 80)], [FrozenTriage("BGC001")]
    )

    verdict = json.loads(verdict_path.read_text(encoding="utf-8"))["verdicts"][0]
    assert verdict["kcb_similarity_band"] == "high"


def test_unmatched_triage_remains_unresolved(tmp_path):
    _, verdict_path = write_boundary_payloads(
        tmp_path, "GENERIC-TEST", [], [FrozenTriage("BGC001")]
    )

    verdict = json.loads(verdict_path.read_text(encoding="utf-8"))["verdicts"][0]
    assert verdict["kcb_similarity_band"] == "unresolved"
