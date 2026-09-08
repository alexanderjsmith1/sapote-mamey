"""Fast, deterministic interpretation surfaces for a sealed gene-first stage.

The scores in this candidate order review; they are not biological importance,
novelty, activity, or lead scores.  No producer or renderer is invoked here.
"""

from __future__ import annotations

import csv
try:
    from ..csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import hashlib
import json
import math
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .gene_first_stage_v2 import (
    ALIGNMENT_CHANNELS,
    CANONICAL_CHANNELS,
    IDENTITY_FIELDS,
    LoadedStage,
    StageHold,
    canonical_identity,
    identity_token,
    load_sealed_stage,
    sha256_file,
)


INTERPRETATION_SCHEMA = "modeb_gene_first_interpretation_v2"
DISAGREEMENT_SCHEMA = "modeb_nr_clustered_nr_disagreement_v2"
RANKING_SCHEMA = "modeb_important_gene_review_rank_v2"
DIAGNOSTIC_SCHEMA = "modeb_locus_diagnostics_v2"
AUTHORING_RECEIPT_SCHEMA = "modeb_gene_first_authoring_receipt_v2"

COVERAGE_ASYMMETRY_THRESHOLD_PP = 25.0
IDENTITY_ASYMMETRY_THRESHOLD_PP = 15.0
PROHIBITED_FIGURE_CONSUMER_PLANES = (
    "GENE",
    "DOMAIN",
    "MODULE",
    "CASSETTE",
    "NEIGHBORHOOD",
    "RAW_EVIDENCE",
)

DISAGREEMENT_FIELDS = (
    *IDENTITY_FIELDS,
    "locus_tag",
    "query_sha256",
    "pair_state",
    "nr_state",
    "nr_subject_accession",
    "nr_subject_name",
    "nr_subject_organism",
    "nr_functional_family_id",
    "nr_pct_identity",
    "nr_query_coverage",
    "clustered_nr_state",
    "clustered_nr_subject_accession",
    "clustered_nr_subject_name",
    "clustered_nr_subject_organism",
    "clustered_nr_functional_family_id",
    "clustered_nr_pct_identity",
    "clustered_nr_query_coverage",
    "coverage_delta_pp",
    "identity_delta_pp",
    "secondary_flags",
    "precedence_winner",
)

RANK_FIELDS = (
    *IDENTITY_FIELDS,
    "review_rank",
    "locus_tag",
    "gene_order",
    "membership",
    "antismash_role",
    "gene_kind",
    "structural_importance",
    "uncertainty_resolution_value",
    "review_priority",
    "structural_components",
    "uncertainty_components",
    "nr_clustered_nr_pair_state",
    "bound_channels",
    "partial_state",
    "boundary_proximity",
    "score_ceiling",
)


class InterpretationHold(ValueError):
    """Typed refusal raised before any interpretation output is created."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


@dataclass(frozen=True)
class InterpretationResult:
    stage: LoadedStage
    disagreement_rows: tuple[dict[str, Any], ...]
    ranked_genes: tuple[dict[str, Any], ...]
    diagnostics: dict[str, Any]
    authoring_packet: dict[str, Any]


def _refuse(code: str, detail: str) -> None:
    raise InterpretationHold(code, detail)


def _as_float(value: str) -> float | None:
    if value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _gene_channel_rows(stage: LoadedStage) -> dict[tuple[str, str], list[dict[str, str]]]:
    indexed: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in stage.evidence:
        if row["observation_scope"] == "GENE":
            indexed.setdefault((row["channel"], row["locus_tag"]), []).append(row)
    return indexed


def _top_or_gap(rows: Sequence[Mapping[str, str]]) -> Mapping[str, str]:
    bound = [row for row in rows if row["mapped_state"] == "BOUND"]
    if bound:
        return next(row for row in bound if row["hit_rank"] == "1")
    return rows[0]


def build_nr_clustered_nr_disagreement(stage: LoadedStage) -> list[dict[str, Any]]:
    """Pair rank-1 nr and clustered_nr evidence without choosing a winner."""

    indexed = _gene_channel_rows(stage)
    output: list[dict[str, Any]] = []
    for gene in stage.gene_roster:
        tag = gene["locus_tag"]
        nr = _top_or_gap(indexed[("nr", tag)])
        clustered = _top_or_gap(indexed[("clustered_nr", tag)])
        nr_state = nr["mapped_state"]
        clustered_state = clustered["mapped_state"]
        nr_bound = nr_state == "BOUND"
        clustered_bound = clustered_state == "BOUND"
        nr_family = nr["functional_family_id"]
        clustered_family = clustered["functional_family_id"]
        if nr_bound and clustered_bound:
            if nr_family and clustered_family and nr_family == clustered_family:
                pair_state = "PAIRED_BOUND_FAMILY_CONCORDANT"
            elif nr_family and clustered_family:
                pair_state = "PAIRED_BOUND_FAMILY_DIVERGENT"
            else:
                pair_state = "PAIRED_BOUND_UNRESOLVED_FAMILY"
        elif nr_bound:
            pair_state = "NR_ONLY_BOUND"
        elif clustered_bound:
            pair_state = "CLUSTERED_NR_ONLY_BOUND"
        else:
            pair_state = "NEITHER_BOUND_TYPED_GAP"

        nr_coverage = _as_float(nr["query_coverage"])
        clustered_coverage = _as_float(clustered["query_coverage"])
        nr_identity = _as_float(nr["pct_identity"])
        clustered_identity = _as_float(clustered["pct_identity"])
        coverage_delta = (
            abs(nr_coverage - clustered_coverage)
            if nr_coverage is not None and clustered_coverage is not None
            else None
        )
        identity_delta = (
            abs(nr_identity - clustered_identity)
            if nr_identity is not None and clustered_identity is not None
            else None
        )
        flags: list[str] = []
        if coverage_delta is not None and coverage_delta >= COVERAGE_ASYMMETRY_THRESHOLD_PP:
            flags.append("COVERAGE_ASYMMETRY")
        if identity_delta is not None and identity_delta >= IDENTITY_ASYMMETRY_THRESHOLD_PP:
            flags.append("IDENTITY_ASYMMETRY")
        if nr_bound and clustered_bound and nr["subject_accession"] == clustered["subject_accession"]:
            flags.append("ACCESSION_EQUAL")
        if (
            nr_bound
            and clustered_bound
            and nr["subject_organism"]
            and clustered["subject_organism"]
            and nr["subject_organism"] != clustered["subject_organism"]
        ):
            flags.append("SUBJECT_ORGANISM_DIFFERENT")
        output.append(
            {
                **{field: stage.identity[field] for field in IDENTITY_FIELDS},
                "locus_tag": tag,
                "query_sha256": gene["protein_sha256"],
                "pair_state": pair_state,
                "nr_state": nr_state,
                "nr_subject_accession": nr["subject_accession"],
                "nr_subject_name": nr["subject_name"],
                "nr_subject_organism": nr["subject_organism"],
                "nr_functional_family_id": nr_family,
                "nr_pct_identity": nr["pct_identity"],
                "nr_query_coverage": nr["query_coverage"],
                "clustered_nr_state": clustered_state,
                "clustered_nr_subject_accession": clustered["subject_accession"],
                "clustered_nr_subject_name": clustered["subject_name"],
                "clustered_nr_subject_organism": clustered["subject_organism"],
                "clustered_nr_functional_family_id": clustered_family,
                "clustered_nr_pct_identity": clustered["pct_identity"],
                "clustered_nr_query_coverage": clustered["query_coverage"],
                "coverage_delta_pp": "" if coverage_delta is None else round(coverage_delta, 3),
                "identity_delta_pp": "" if identity_delta is None else round(identity_delta, 3),
                "secondary_flags": ";".join(flags),
                "precedence_winner": "NONE_BY_CONTRACT",
            }
        )
    return output


def build_locus_diagnostics(stage: LoadedStage) -> dict[str, Any]:
    """Expose independent completeness axes and typed cross-axis flags."""

    context = stage.locus_context
    boundary = context["bgc_boundary_state"]
    assembly = context["assembly_fragmentation_tier"]
    detector_window = context["detector_window_state"]
    ceiling = context["canonical_fragment_ceiling_state"]
    start = int(context["region_start"])
    end = int(context["region_end"])
    contig_length = int(context["contig_length"])
    touches_left = start <= 1
    touches_right = end >= contig_length
    flags: list[str] = []
    if boundary == "EDGE":
        flags.append("BGC_EDGE_COMPLETENESS_HOLD")
    elif boundary == "FULL_CONTIG":
        flags.append("BGC_FULL_CONTIG_COMPLETENESS_HOLD")
    elif boundary == "UNKNOWN":
        flags.append("BOUNDARY_STATE_UNRESOLVED")
    if assembly in {"DRAFT", "FRAGMENTED", "HIGHLY_FRAGMENTED"}:
        flags.append("ASSEMBLY_FRAGMENTATION_CONTEXT")
    if detector_window == "DETECTOR_WINDOW":
        flags.append("DETECTOR_WINDOW_NOT_PATHWAY_BOUNDARY")
    elif detector_window == "BOUNDARY_CONTEXT_EXTENSION":
        flags.append("BOUNDARY_CONTEXT_PRESENT")
    elif detector_window == "UNRESOLVED":
        flags.append("DETECTOR_WINDOW_UNRESOLVED")
    if ceiling == "TRIPPED":
        flags.append("CANONICAL_FRAGMENT_CEILING_TRIPPED")
    if (
        (boundary == "INTERIOR" and (touches_left or touches_right))
        or (boundary == "EDGE" and not (touches_left or touches_right))
        or (boundary == "FULL_CONTIG" and not (touches_left and touches_right))
    ):
        flags.append("INTERNAL_INTERVAL_CONFLICT")

    partial_counts: dict[str, int] = {}
    partial_tags: list[str] = []
    boundary_context_tags: list[str] = []
    for gene in stage.gene_roster:
        partial_counts[gene["partial_state"]] = partial_counts.get(gene["partial_state"], 0) + 1
        if gene["partial_state"] != "COMPLETE":
            partial_tags.append(gene["locus_tag"])
        if gene["membership"] == "BOUNDARY_CONTEXT_ONLY":
            boundary_context_tags.append(gene["locus_tag"])
    if partial_tags:
        flags.append("PARTIAL_PROTEIN_CONTEXT")
    core_partial = [
        gene["locus_tag"]
        for gene in stage.gene_roster
        if gene["partial_state"] != "COMPLETE" and _is_defining_core(gene)
    ]
    if core_partial:
        flags.append("PARTIAL_CORE_PROTEIN_HOLD")
    if boundary_context_tags and "BOUNDARY_CONTEXT_PRESENT" not in flags:
        flags.append("BOUNDARY_CONTEXT_PRESENT")
    return {
        "schema_version": DIAGNOSTIC_SCHEMA,
        "identity": dict(stage.identity),
        "stage_id": stage.stage_receipt["stage_id"],
        "stage_receipt_sha256": stage.stage_receipt_sha256,
        "axes": {
            "bgc_boundary_state": boundary,
            "assembly_fragmentation_tier": assembly,
            "protein_partial_state_counts": dict(sorted(partial_counts.items())),
            "detector_window_state": detector_window,
        },
        "interval": {
            "region_start": start,
            "region_end": end,
            "contig_length": contig_length,
        },
        "canonical_fragment_ceiling": {
            "state": ceiling,
            "reason": context["canonical_fragment_ceiling_reason"],
            "owner": context["canonical_fragment_ceiling_owner"],
        },
        "partial_locus_tags": partial_tags,
        "partial_core_locus_tags": core_partial,
        "boundary_context_locus_tags": boundary_context_tags,
        "diagnostic_flags": sorted(set(flags)),
        "source_locator": context["source_locator"],
        "source_sha256": context["source_sha256"],
        "claim_ceiling": "COMPLETENESS_CONTEXT_ONLY_NOT_PATHWAY_BOUNDARY_PROOF",
    }


def _role_text(gene: Mapping[str, str]) -> str:
    return f"{gene['antismash_role']} {gene['gene_kind']}".lower()


def _is_defining_core(gene: Mapping[str, str]) -> bool:
    role = gene["antismash_role"].strip().lower().replace("_", "-")
    kind = gene["gene_kind"].strip().lower()
    return role == "biosynthetic" or any(
        term in kind for term in ("core", "synthase", "synthetase")
    )


def _is_tailoring(gene: Mapping[str, str]) -> bool:
    text = _role_text(gene)
    return any(term in text for term in ("tailor", "maturation", "modifier", "oxidoreductase"))


def _is_resistance_or_export(gene: Mapping[str, str]) -> bool:
    text = _role_text(gene)
    return any(term in text for term in ("resistance", "transport", "export", "efflux"))


def _is_regulatory(gene: Mapping[str, str]) -> bool:
    text = _role_text(gene)
    return any(term in text for term in ("regulat", "transcription", "sensor", "response regulator"))


def _is_source_unknown(gene: Mapping[str, str]) -> bool:
    text = _role_text(gene)
    return any(term in text for term in ("unknown", "hypothetical", "uncharacterized", "missing"))


def _bound_gene_channels(indexed: Mapping[tuple[str, str], Sequence[Mapping[str, str]]], tag: str) -> set[str]:
    return {
        channel
        for channel in CANONICAL_CHANNELS
        if any(row["mapped_state"] == "BOUND" for row in indexed.get((channel, tag), ()))
    }


def _top_bound_family(
    indexed: Mapping[tuple[str, str], Sequence[Mapping[str, str]]], channel: str, tag: str
) -> str:
    for row in indexed.get((channel, tag), ()):
        if row["mapped_state"] == "BOUND" and row.get("hit_rank") == "1":
            return row["functional_family_id"]
    return ""


def rank_important_genes(
    stage: LoadedStage,
    disagreement_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Return a transparent deterministic review order with component receipts."""

    disagreement_by_tag = {row["locus_tag"]: row for row in disagreement_rows}
    indexed = _gene_channel_rows(stage)
    scored: list[dict[str, Any]] = []
    for gene in stage.gene_roster:
        tag = gene["locus_tag"]
        structural: list[tuple[str, int]] = []
        if _is_defining_core(gene):
            structural.append(("defining_biosynthetic_core", 50))
        if _is_tailoring(gene):
            structural.append(("tailoring_or_maturation", 25))
        if _is_resistance_or_export(gene):
            structural.append(("resistance_or_export", 20))
        if _is_regulatory(gene):
            structural.append(("regulatory", 10))
        bound_channels = _bound_gene_channels(indexed, tag)
        if "domain" in bound_channels:
            structural.append(("bound_domain_architecture", 15))
        if "cassette" in bound_channels:
            structural.append(("executed_cassette_membership", 15))
        if "neighborhood" in bound_channels:
            structural.append(("bound_neighborhood_context", 10))

        pair_state = disagreement_by_tag[tag]["pair_state"]
        uncertainty: list[tuple[str, int]] = []
        if pair_state == "PAIRED_BOUND_FAMILY_DIVERGENT":
            uncertainty.append(("nr_clustered_nr_family_divergence", 30))
        elif pair_state == "PAIRED_BOUND_UNRESOLVED_FAMILY":
            uncertainty.append(("paired_family_unresolved", 20))
        elif pair_state in {"NR_ONLY_BOUND", "CLUSTERED_NR_ONLY_BOUND"}:
            uncertainty.append(("one_channel_only", 15))
        elif pair_state == "NEITHER_BOUND_TYPED_GAP":
            uncertainty.append(("neither_channel_bound", 20))

        swiss_family = _top_bound_family(indexed, "local_swissprot", tag)
        paired_families = {
            family
            for family in (
                disagreement_by_tag[tag]["nr_functional_family_id"],
                disagreement_by_tag[tag]["clustered_nr_functional_family_id"],
            )
            if family
        }
        if swiss_family and paired_families and swiss_family not in paired_families:
            uncertainty.append(("local_swissprot_family_conflict", 20))
        if gene["partial_state"] != "COMPLETE":
            uncertainty.append(("partial_or_internal_stop_protein", 20))
        if gene["membership"] == "BOUNDARY_CONTEXT_ONLY":
            uncertainty.append(("boundary_context_only", 15))
        if _is_source_unknown(gene):
            uncertainty.append(("source_annotation_unknown", 15))

        structural_score = min(100, sum(points for _, points in structural))
        uncertainty_score = min(100, sum(points for _, points in uncertainty))
        review_priority = round(0.65 * structural_score + 0.35 * uncertainty_score, 1)
        scored.append(
            {
                **{field: stage.identity[field] for field in IDENTITY_FIELDS},
                "review_rank": 0,
                "locus_tag": tag,
                "gene_order": int(gene["gene_order"]),
                "membership": gene["membership"],
                "antismash_role": gene["antismash_role"],
                "gene_kind": gene["gene_kind"],
                "structural_importance": structural_score,
                "uncertainty_resolution_value": uncertainty_score,
                "review_priority": review_priority,
                "structural_components": ";".join(f"{name}=+{points}" for name, points in structural),
                "uncertainty_components": ";".join(f"{name}=+{points}" for name, points in uncertainty),
                "nr_clustered_nr_pair_state": pair_state,
                "bound_channels": ";".join(sorted(bound_channels)),
                "partial_state": gene["partial_state"],
                "boundary_proximity": gene["boundary_proximity"],
                "score_ceiling": "REVIEW_ORDER_ONLY_NOT_BIOLOGICAL_IMPORTANCE",
            }
        )
    scored.sort(
        key=lambda row: (
            -float(row["review_priority"]),
            -int(row["structural_importance"]),
            -int(row["uncertainty_resolution_value"]),
            int(row["gene_order"]),
            str(row["locus_tag"]),
        )
    )
    for rank, row in enumerate(scored, start=1):
        row["review_rank"] = rank
    return scored


def _channel_coverage(stage: LoadedStage) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for channel in CANONICAL_CHANNELS:
        rows = [row for row in stage.evidence if row["channel"] == channel]
        states: dict[str, int] = {}
        for row in rows:
            states[row["mapped_state"]] = states.get(row["mapped_state"], 0) + 1
        result[channel] = {
            "rows": len(rows),
            "bound_rows": states.get("BOUND", 0),
            "mapped_states": dict(sorted(states.items())),
        }
    return result


def choose_highest_information_next_analysis(
    stage: LoadedStage,
    ranked_genes: Sequence[Mapping[str, Any]],
    disagreement_rows: Sequence[Mapping[str, Any]],
) -> dict[str, str]:
    """Select one workflow route from explicit staged gaps, never a biology score."""

    pair_by_tag = {row["locus_tag"]: row for row in disagreement_rows}
    indexed = _gene_channel_rows(stage)
    for gene in ranked_genes:
        pair = pair_by_tag[str(gene["locus_tag"])]
        state = pair["pair_state"]
        if state == "NR_ONLY_BOUND":
            return {
                "route": "COMPLETE_CLUSTERED_NR_FOR_HIGHEST_RANKED_UNPAIRED_GENE",
                "locus_tag": str(gene["locus_tag"]),
                "reason": "The paired comparison is limited by an explicit clustered_nr gap.",
            }
        if state == "CLUSTERED_NR_ONLY_BOUND":
            return {
                "route": "COMPLETE_NR_FOR_HIGHEST_RANKED_UNPAIRED_GENE",
                "locus_tag": str(gene["locus_tag"]),
                "reason": "The paired comparison is limited by an explicit nr gap.",
            }
        if state == "NEITHER_BOUND_TYPED_GAP":
            return {
                "route": "RUN_NR_FOR_HIGHEST_RANKED_UNRESOLVED_STRUCTURAL_GENE",
                "locus_tag": str(gene["locus_tag"]),
                "reason": "Neither paired channel is bound; start one exact-query channel without inferring absence.",
            }
    for gene in ranked_genes:
        pair = pair_by_tag[str(gene["locus_tag"])]
        if pair["pair_state"] == "PAIRED_BOUND_FAMILY_DIVERGENT":
            swiss = _top_bound_family(indexed, "local_swissprot", str(gene["locus_tag"]))
            if not swiss:
                return {
                    "route": "USE_LOCAL_SWISSPROT_TO_TEST_COARSE_FAMILY_DIVERGENCE",
                    "locus_tag": str(gene["locus_tag"]),
                    "reason": "Both broad channels are bound but their producer-supplied coarse families differ.",
                }
            if "domain" not in _bound_gene_channels(indexed, str(gene["locus_tag"])):
                return {
                    "route": "INGEST_DOMAIN_ARCHITECTURE_FOR_DIVERGENT_GENE",
                    "locus_tag": str(gene["locus_tag"]),
                    "reason": "Paired families diverge and curated context is already present; architecture is the next independent discriminator.",
                }
    for gene in ranked_genes:
        if int(gene["structural_importance"]) > 0 and "domain" not in _bound_gene_channels(
            indexed, str(gene["locus_tag"])
        ):
            return {
                "route": "INGEST_DOMAIN_ARCHITECTURE_FOR_HIGHEST_RANKED_STRUCTURAL_GENE",
                "locus_tag": str(gene["locus_tag"]),
                "reason": "A structurally relevant gene lacks bound domain evidence.",
            }
    if any(
        row["channel"] == "cassette" and row["mapped_state"] == "REGISTRY_ONLY_NOT_EXECUTED"
        for row in stage.evidence
    ):
        return {
            "route": "EXECUTE_OR_INGEST_CASSETTE_DETECTOR",
            "locus_tag": "",
            "reason": "The cassette channel contains a descriptive registry state but no executed detection.",
        }
    if not any(
        row["channel"] == "neighborhood" and row["mapped_state"] == "BOUND"
        for row in stage.evidence
    ):
        return {
            "route": "BIND_PHYSICAL_NEIGHBORHOOD_ORDER",
            "locus_tag": "",
            "reason": "No physical neighborhood observation is bound.",
        }
    return {
        "route": "RECONCILE_MIBIG_RELATION_WITH_BOUND_ARCHITECTURE",
        "locus_tag": "",
        "reason": "The primary paired and architecture gaps are resolved; compare reference relation without naming a product.",
    }


def _stage_age_seconds(stage: LoadedStage, now_utc: datetime) -> float | None:
    value = stage.stage_receipt.get("sealed_utc")
    if not isinstance(value, str):
        return None
    try:
        sealed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if sealed.tzinfo is None:
        sealed = sealed.replace(tzinfo=timezone.utc)
    return round(max(0.0, (now_utc - sealed.astimezone(timezone.utc)).total_seconds()), 3)


def _authoring_prompts(
    ranked_genes: Sequence[Mapping[str, Any]],
    disagreement_rows: Sequence[Mapping[str, Any]],
    diagnostics: Mapping[str, Any],
) -> dict[str, Any]:
    core_tags = [
        str(row["locus_tag"])
        for row in ranked_genes
        if "defining_biosynthetic_core" in str(row["structural_components"])
    ]
    divergent = [
        str(row["locus_tag"])
        for row in disagreement_rows
        if row["pair_state"] == "PAIRED_BOUND_FAMILY_DIVERGENT"
    ]
    alternatives = [
        "Test whether source-designated core roles and bound architectures support one compact biosynthetic model.",
        "Test whether disagreement reflects database representation or multidomain architecture rather than a different pathway model.",
    ]
    if diagnostics["diagnostic_flags"]:
        alternatives.append(
            "Test whether interval, protein partialness, detector-window, or assembly context limits the apparent core."
        )
    return {
        "smallest_plausible_core_locus_tags": core_tags,
        "core_ceiling": "SOURCE_ROLE_AND_ARCHITECTURE_CHECKLIST_NOT_PRODUCT_IDENTITY",
        "central_model_prompt": alternatives[0],
        "alternative_model_prompts": alternatives[1:],
        "paired_family_divergence_locus_tags": divergent,
    }


def interpret_stage(
    stage_dir: str | Path,
    *,
    now_utc: datetime | None = None,
) -> InterpretationResult:
    """Verify a warm stage and build all in-memory review surfaces."""

    timings: dict[str, float] = {}
    total_start = time.perf_counter()
    phase_start = time.perf_counter()
    stage = load_sealed_stage(stage_dir)
    timings["stage_preflight_seconds"] = round(time.perf_counter() - phase_start, 6)

    phase_start = time.perf_counter()
    disagreement = build_nr_clustered_nr_disagreement(stage)
    timings["paired_disagreement_seconds"] = round(time.perf_counter() - phase_start, 6)

    phase_start = time.perf_counter()
    diagnostics = build_locus_diagnostics(stage)
    timings["diagnostics_seconds"] = round(time.perf_counter() - phase_start, 6)

    phase_start = time.perf_counter()
    ranked = rank_important_genes(stage, disagreement)
    timings["ranking_seconds"] = round(time.perf_counter() - phase_start, 6)

    phase_start = time.perf_counter()
    next_analysis = choose_highest_information_next_analysis(stage, ranked, disagreement)
    prompts = _authoring_prompts(ranked, disagreement, diagnostics)
    now = (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc)
    token = stage.identity_token
    output_member_names = {
        "nr_clustered_nr_disagreement": f"{token}__nr_vs_clustered_nr_disagreement.tsv",
        "important_genes": f"{token}__important_genes_v2.tsv",
        "locus_diagnostics": f"{token}__locus_diagnostics.json",
        "authoring_packet": f"{token}__authoring_packet.json",
    }
    pair_state_counts: dict[str, int] = {}
    for row in disagreement:
        state = str(row["pair_state"])
        pair_state_counts[state] = pair_state_counts.get(state, 0) + 1
    packet = {
        "schema_version": INTERPRETATION_SCHEMA,
        "status": "ENGINEERING_CANDIDATE_AUTHORING_SURFACE_ONLY",
        "identity": dict(stage.identity),
        "identity_token": token,
        "stage_binding": {
            "stage_id": stage.stage_receipt["stage_id"],
            "stage_receipt_sha256": stage.stage_receipt_sha256,
            "query_roster_sha256": stage.query_roster_sha256,
            "sealed_utc": stage.stage_receipt.get("sealed_utc"),
            "stage_age_seconds": _stage_age_seconds(stage, now),
        },
        "channel_coverage": _channel_coverage(stage),
        "nr_clustered_nr_pair_state_counts": dict(sorted(pair_state_counts.items())),
        "ranked_gene_count": len(ranked),
        "top_ranked_genes": [
            {
                "locus_tag": row["locus_tag"],
                "review_rank": row["review_rank"],
                "structural_importance": row["structural_importance"],
                "uncertainty_resolution_value": row["uncertainty_resolution_value"],
                "review_priority": row["review_priority"],
            }
            for row in ranked[:10]
        ],
        "model_prompts": prompts,
        "diagnostic_flags": diagnostics["diagnostic_flags"],
        "highest_information_next_analysis": next_analysis,
        "figure_factory_summary_overlay_template": {
            "consumer_plane": "BGC_SUMMARY",
            "candidate_actions": [
                "RETAIN_SOURCE_SUMMARY",
                "FLAG_SUMMARY_ONLY",
                "WITHHOLD_SUMMARY_PENDING_BINDING",
                "PROPOSE_SUMMARY_RECLASSIFICATION",
            ],
            "selection_state": "OWNER_REVIEW_REQUIRED",
            "prohibited_consumer_planes": list(PROHIBITED_FIGURE_CONSUMER_PLANES),
            "mutation_policy": "SEPARATE_OVERLAY_ONLY_SOURCE_TABLE_IMMUTABLE",
        },
        "output_members": output_member_names,
        "claim_safety": [
            "SIMILARITY_NOT_IDENTITY",
            "CAPACITY_NOT_PRODUCTION",
            "MISSING_OR_UNBOUND_EVIDENCE_NOT_BIOLOGICAL_ABSENCE",
            "REVIEW_PRIORITY_NOT_BIOLOGICAL_IMPORTANCE",
            "JUDGMENT_DEFERRED",
        ],
        "authority_ceiling": "NO_CARD_NO_INTEGRATION_NO_RELEASE_NO_SCIENTIFIC_ACCEPTANCE",
    }
    timings["packet_composition_seconds"] = round(time.perf_counter() - phase_start, 6)
    timings["total_compute_seconds"] = round(time.perf_counter() - total_start, 6)
    packet["phase_timings"] = timings
    return InterpretationResult(
        stage=stage,
        disagreement_rows=tuple(disagreement),
        ranked_genes=tuple(ranked),
        diagnostics=diagnostics,
        authoring_packet=packet,
    )


def _write_json_exclusive(path: Path, value: Any) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError:
        _refuse("MODEB_GF2_OUTPUT_REFUSED", f"output exists: {path.name}")


def _write_tsv_exclusive(path: Path, rows: Iterable[Mapping[str, Any]], fields: Sequence[str]) -> None:
    try:
        with path.open("x", encoding="utf-8", newline="") as handle:
            writer = _SafeDictWriter(handle, delimiter="\t", fieldnames=list(fields), extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in fields})
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError:
        _refuse("MODEB_GF2_OUTPUT_REFUSED", f"output exists: {path.name}")


def write_authoring_outputs(
    stage_dir: str | Path,
    output_root: str | Path,
    *,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Write a compact additive packet after all stage and output checks pass."""

    result = interpret_stage(stage_dir, now_utc=now_utc)
    root = Path(output_root)
    if not root.is_dir():
        _refuse("MODEB_GF2_OUTPUT_REFUSED", "output root must already exist")
    target = root / result.stage.identity_token
    if target.exists():
        _refuse("MODEB_GF2_OUTPUT_REFUSED", f"output identity directory exists: {target.name}")
    names = result.authoring_packet["output_members"]
    target.mkdir()
    disagreement_path = target / names["nr_clustered_nr_disagreement"]
    ranking_path = target / names["important_genes"]
    diagnostic_path = target / names["locus_diagnostics"]
    packet_path = target / names["authoring_packet"]
    _write_tsv_exclusive(disagreement_path, result.disagreement_rows, DISAGREEMENT_FIELDS)
    _write_tsv_exclusive(ranking_path, result.ranked_genes, RANK_FIELDS)
    _write_json_exclusive(diagnostic_path, result.diagnostics)
    _write_json_exclusive(packet_path, result.authoring_packet)
    members = [
        {
            "role": role,
            "name": path.name,
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        }
        for role, path in (
            ("nr_clustered_nr_disagreement", disagreement_path),
            ("important_genes", ranking_path),
            ("locus_diagnostics", diagnostic_path),
            ("authoring_packet", packet_path),
        )
    ]
    receipt_basis = {
        "schema_version": AUTHORING_RECEIPT_SCHEMA,
        "identity": dict(result.stage.identity),
        "identity_token": result.stage.identity_token,
        "stage_id": result.stage.stage_receipt["stage_id"],
        "stage_receipt_sha256": result.stage.stage_receipt_sha256,
        "members": members,
    }
    receipt = {
        **receipt_basis,
        "authoring_id": _sha256_json(receipt_basis),
        "created_utc": (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat(),
        "authority_ceiling": "ENGINEERING_CANDIDATE_AUTHORING_SURFACE_ONLY",
        "self_excluding_receipt": True,
    }
    receipt_path = target / f"{result.stage.identity_token}__authoring_receipt.json"
    _write_json_exclusive(receipt_path, receipt)
    return {
        "output_dir": str(target),
        "receipt_path": str(receipt_path),
        "receipt": receipt,
    }


__all__ = [
    "AUTHORING_RECEIPT_SCHEMA",
    "DIAGNOSTIC_SCHEMA",
    "DISAGREEMENT_FIELDS",
    "DISAGREEMENT_SCHEMA",
    "IDENTITY_ASYMMETRY_THRESHOLD_PP",
    "INTERPRETATION_SCHEMA",
    "InterpretationHold",
    "InterpretationResult",
    "PROHIBITED_FIGURE_CONSUMER_PLANES",
    "RANK_FIELDS",
    "RANKING_SCHEMA",
    "build_locus_diagnostics",
    "build_nr_clustered_nr_disagreement",
    "choose_highest_information_next_analysis",
    "interpret_stage",
    "rank_important_genes",
    "write_authoring_outputs",
]
