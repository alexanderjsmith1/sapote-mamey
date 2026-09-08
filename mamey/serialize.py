"""mamey.serialize — emit the two sides of the deterministic↔judgment boundary as
audit-ready JSON (W4/W23).

The data already exists in a run: `run.bgcs` (BGCRecord, deterministic) and the output
of `triage_bgcs(...)` (TriageRecord, judgment). This module serialises each into a small,
stable JSON payload keyed by the real primary key `bgc_id`, so `mamey.boundary_audit`
can diff them and so a reviewer can inspect the contract directly.

records.json  = the deterministic facts (no scores, no claim confidence — mirrors the
                "extraction layer only" contract in models.py).
verdicts.json = the judgment layer's per-BGC call (lead tier, claim confidence, standing-
                rule downgrades), with similarity numbers passed through mamey.precision
                so no bare over-precise figure is emitted (W26).
"""
from __future__ import annotations

import json
import pathlib
from typing import Any

from .precision import similarity_band, round_bitscore

RECORDS_SCHEMA = "mamey.records/1"
VERDICTS_SCHEMA = "sapote.verdicts/1"


def records_payload(strain: str, bgcs: list) -> dict[str, Any]:
    """Deterministic side. Only source-bounded facts — deliberately no scores."""
    recs = []
    for b in bgcs:
        recs.append({
            "bgc_id": b.bgc_id,
            "contig": b.contig,
            "node_id": getattr(b, "node_id", "") or b.contig,
            "user_label": getattr(b, "user_label", "") or f"{getattr(b, 'node_id', '') or b.contig} ({b.bgc_id})",
            "region_number": b.region_number,
            "antismash_region": getattr(b, "antismash_region", ""),
            "edge_status": b.edge_status,
            "products": list(b.products),
            "mibig_hits": list(getattr(b, "mibig_hits", []) or []),
            "architecture_confidence": b.architecture_confidence,
            "architecture_capacity": getattr(b, "architecture_capacity", ""),
            "kcb_top": getattr(b, "kcb_top", None),
            "kcb_cumulative": getattr(b, "kcb_cumulative", None),
            "kcb_evidence_state": getattr(b, "kcb_evidence_state", "UNKNOWN_KCB"),
        })
    return {"schema": RECORDS_SCHEMA, "strain": strain, "records": recs}


def verdicts_payload(strain: str, triage: list) -> dict[str, Any]:
    """Judgment side. Per-BGC call; similarity is binned (W26), never a bare number."""
    verds = []
    for t in triage:
        verds.append({
            "bgc_id": t.bgc_id,
            "contig": getattr(t, "contig", ""),
            "user_label": getattr(t, "user_label", ""),
            "lead_tier": t.lead_tier,
            "claim_confidence": t.claim_confidence,
            "corrected_rank": t.corrected_rank,
            "standing_rule_flag": t.standing_rule_flag,
            "primary_metabolism_flag": bool(t.primary_metabolism_flag),
            "misanchor_flag": getattr(t, "misanchor_flag", ""),
            # v9.7.374: mobile_element_flag is a THIRD corrected_rank-gating downgrade signal
            # (scoring.py:686 excludes a BGC from corrected_rank when standing_rule_flag OR
            # primary_metabolism_flag OR mobile_element_flag is set) but was never round-tripped
            # into verdicts.json, so a mobile-element downgrade was invisible to any reviewer or
            # auditor reading the boundary payload directly.
            "mobile_element_flag": getattr(t, "mobile_element_flag", "") or "",
            "ab_score": t.ab_score,
            "af_score": t.af_score,
            "novelty_score": t.novelty_score,
            # W26: a coarse similarity band travels instead of a false-precise number.
            "kcb_similarity_band": similarity_band(getattr(t, "_kcb_cumulative", None)),
            # C1 v9.7.58: concordance verdict wired from SourceScanBundle.concordance_per_bgc
            "concordance_verdict": getattr(t, "concordance_verdict", "") or "",
            # v9.7.62: MATURATION_GAP when RiPP/nucleoside BGC has no nearby maturation genes
            "umed_gap_flag": getattr(t, "umed_gap_flag", "") or "",
        })
    return {"schema": VERDICTS_SCHEMA, "strain": strain, "verdicts": verds}


def write_boundary_payloads(package_dir, strain: str, bgcs: list, triage: list) -> tuple:
    """Write {strain}_records.json and {strain}_verdicts.json into the package dir.
    Returns the two paths. Called from cli._write_package."""
    pd = pathlib.Path(package_dir)
    # carry kcb_cumulative onto triage records for the W26 band (triage lacks it natively)
    by_id = {b.bgc_id: b for b in bgcs}
    for t in triage:
        b = by_id.get(t.bgc_id)
        if b is not None:
            try:
                setattr(t, "_kcb_cumulative", getattr(b, "kcb_cumulative", None))
            except Exception:
                pass
    rec_path = pd / f"{strain}_records.json"
    ver_path = pd / f"{strain}_verdicts.json"
    rec_tmp = rec_path.with_suffix(".json.tmp")
    ver_tmp = ver_path.with_suffix(".json.tmp")
    rec_tmp.write_text(json.dumps(records_payload(strain, bgcs), indent=2), encoding="utf-8")
    ver_tmp.write_text(json.dumps(verdicts_payload(strain, triage), indent=2), encoding="utf-8")
    import os
    os.replace(str(rec_tmp), str(rec_path))
    os.replace(str(ver_tmp), str(ver_path))
    return rec_path, ver_path
