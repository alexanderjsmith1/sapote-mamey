"""Split/composite BGC claim-safety labels for Mode B (v9.7.143a)."""
from __future__ import annotations

from typing import Any

ALLOWED_SPLIT_COMPOSITE_LABELS = {
    "confirmed_contiguous_BGC",
    "candidate_split_BGC",
    "candidate_parallel_locus",
    "comparator_neighborhood_match",
    "standalone_complete_looking_BGC",
    "fragmented_partial_core",
    "do_not_merge",
    "inventory_context_only",
}


def classify_split_composite_status(evidence: dict[str, Any]) -> str:
    """Classify Mode B linkage status from explicit evidence booleans."""

    if evidence.get("physical_contiguity") and evidence.get("single_region"):
        return "confirmed_contiguous_BGC"
    if evidence.get("different_comparator_axis"):
        return "do_not_merge"
    if evidence.get("shared_comparator") and evidence.get("multiple_contigs"):
        return "candidate_split_BGC"
    if evidence.get("comparator_neighborhood_match"):
        return "comparator_neighborhood_match"
    if evidence.get("architecture_compatible") and not evidence.get("shared_comparator"):
        return "candidate_parallel_locus"
    if evidence.get("partial_core_only"):
        return "fragmented_partial_core"
    if evidence.get("complete_local_context"):
        return "standalone_complete_looking_BGC"
    return "inventory_context_only"


def claim_safety_note(label: str) -> str:
    if label == "confirmed_contiguous_BGC":
        return "Contiguous BGC claim allowed if source coordinates/region support it; exact product still requires product-level evidence."
    if label == "candidate_split_BGC":
        return "Candidate split/composite BGC only; do not claim confirmed contiguity."
    if label == "candidate_parallel_locus":
        return "Candidate companion/parallel locus; do not merge into one product model without stronger evidence."
    if label == "comparator_neighborhood_match":
        return "External comparator synteny supports relatedness; AS assembly contiguity still unresolved."
    if label == "do_not_merge":
        return "Different comparator axis or incompatible evidence; keep as separate Mode B hypothesis."
    if label == "fragmented_partial_core":
        return "Partial core only; missing support genes must be documented."
    if label == "standalone_complete_looking_BGC":
        return "Complete-looking local context; exact product still not proven."
    return "Inventory/context only; avoid pathway/product claims."
