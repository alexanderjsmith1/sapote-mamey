"""Three-layer readiness receipts for the Mode B gene-first stage (V4 §5 — successor r5).

The interpreter fuses gene-autonomous and locus-context surfaces into ONE authoring packet
and ONE receipt, so a missing cohort denominator — or an unresolved boundary — could be
read as blocking evidence that is in fact complete. This module splits the same sealed
stage into three immutable, one-way-referenced receipts with SEPARATE readiness and holds:

    gene_evidence_receipt (A)  ->  locus_context_receipt (B)  ->  cohort_analysis_receipt (C)

Owner decision rule (three-layer owner note, CONFIRMED): A READY -> emit A; B READY -> emit
B even when C is held; C emits only with a digest-bound external membership manifest and a
declared denominator. Later layers cite earlier receipt ids; they never rewrite them.
Missing later-layer evidence is recorded as NOT_REQUIRED_FOR_LAYER_<X>, never as a hold on
an earlier layer. Prefixes (AS-/AJS-/SID) are NEVER cohort membership.

Scope note (honest): a Layer-A-ONLY *stage* (no locus-context member) still cannot be
sealed — the stage sealer requires the combined package. This module makes the layers
independently READY/HELD and separately receipted on any sealed stage; relaxing the sealer
for A-only stages is a named follow-on.

Claim ceiling: engineering readiness only. No prevalence, recurrence, enrichment, activity,
production, or identity claim is produced by any layer here; judgment deferred.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from mamey.mode_b.gene_first_interpret_v2 import (
    _channel_coverage,
    _gene_channel_rows,
    build_locus_diagnostics,
    build_nr_clustered_nr_disagreement,
    choose_highest_information_next_analysis,
    rank_important_genes,
)
from mamey.mode_b.gene_first_stage_v2 import (
    ALIGNMENT_CHANNELS,
    IDENTITY_FIELDS,
    LoadedStage,
    load_sealed_stage,
)

LAYER_A_SCHEMA = "modeb_gene_first_gene_evidence_receipt_v1"
LAYER_B_SCHEMA = "modeb_gene_first_locus_context_receipt_v1"
LAYER_C_SCHEMA = "modeb_gene_first_cohort_analysis_receipt_v1"
GENE_LEVEL_CHANNELS = ("nr", "clustered_nr", "local_swissprot", "domain")
CONTEXT_CHANNELS = ("cassette", "neighborhood")
_PREFIX_ONLY = re.compile(r"^(AS|AJS|SID)[-_ ]?\d*\*?$", re.IGNORECASE)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

LAYER_A_ALLOWED = (
    "per_gene_channel_separated_observations",
    "paired_nr_clustered_nr_comparison",
    "domain_architecture_and_capacity_context",
    "protein_completeness_warning",
    "gene_level_uncertainty_flags",
)
LAYER_A_PROHIBITED = (
    "locus_membership", "pathway_role", "bgc_class", "cohort_prevalence",
    "recurrence", "enrichment", "production", "activity",
)
LAYER_B_PROHIBITED = ("cohort_prevalence", "population_recurrence", "enrichment", "comparative_rank")


class LayerHold(ValueError):
    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _receipt(basis: dict[str, Any], id_field: str) -> dict[str, Any]:
    out = dict(basis)
    out[id_field] = _sha256_json(basis)
    out["immutable"] = True
    return out


# --- Layer A --------------------------------------------------------------------------------

def build_layer_a(stage: LoadedStage) -> dict[str, Any]:
    """Gene-autonomous evidence receipt. Requires complete identity, canonical locus tags
    with protein digests, and an explicit typed state per requested gene-level channel.
    Neighborhood/cassette/boundary/cohort evidence is NOT REQUIRED here."""
    holds: list[str] = []
    identity = dict(stage.identity)
    if any(not identity.get(field) for field in IDENTITY_FIELDS):
        holds.append("LAYER_A_IDENTITY_HOLD")
    indexed = _gene_channel_rows(stage)
    genes: list[dict[str, Any]] = []
    for gene in stage.gene_roster:
        tag = gene["locus_tag"]
        if not _SHA256.match(str(gene.get("protein_sha256", "")).lower()):
            holds.append("LAYER_A_QUERY_BINDING_HOLD")
        channel_states: dict[str, str] = {}
        for channel in GENE_LEVEL_CHANNELS:
            rows = indexed.get((channel, tag), [])
            if not rows:
                if channel in ALIGNMENT_CHANNELS:
                    holds.append("LAYER_A_CHANNEL_GAP")
                channel_states[channel] = "NO_EXPLICIT_STATE"
                continue
            states = sorted({row["mapped_state"] for row in rows})
            channel_states[channel] = states[0] if len(states) == 1 else ";".join(states)
            for row in rows:
                if row["mapped_state"] == "BOUND" and row.get("query_sha256", "").lower() != gene["protein_sha256"].lower():
                    holds.append("LAYER_A_QUERY_BINDING_HOLD")
                if row["mapped_state"] == "PROVENANCE_HOLD":
                    holds.append("LAYER_A_PROVENANCE_HOLD")
        genes.append({
            "locus_tag": tag,
            "protein_sha256": gene["protein_sha256"].lower(),
            "protein_length_aa": gene.get("protein_length_aa", ""),
            "partial_state": gene.get("partial_state", ""),
            "channel_states": channel_states,
            "completeness_warning": gene.get("partial_state", "COMPLETE") != "COMPLETE",
        })
    if any(g["completeness_warning"] for g in genes):
        # A warning, not a hold: partial proteins still yield valid gene-autonomous evidence.
        pass
    pair_rows = build_nr_clustered_nr_disagreement(stage)
    basis = {
        "schema_version": LAYER_A_SCHEMA,
        "layer": "A",
        "identity": identity,
        "identity_token": stage.identity_token,
        "stage_id": stage.stage_receipt["stage_id"],
        "stage_receipt_sha256": stage.stage_receipt_sha256,
        "query_roster_sha256": stage.query_roster_sha256,
        "genes": genes,
        "paired_nr_clustered_nr": [
            {k: row[k] for k in ("locus_tag", "pair_state", "secondary_flags", "precedence_winner")}
            for row in pair_rows
        ],
        "channel_coverage": {c: v for c, v in _channel_coverage(stage).items() if c in GENE_LEVEL_CHANNELS},
        "not_required": {c: "NOT_REQUIRED_FOR_LAYER_A" for c in CONTEXT_CHANNELS + ("locus_context", "cohort_manifest", "global_denominator")},
        "holds": sorted(set(holds)),
        "readiness": "A_HELD" if holds else "A_READY",
        "allowed_outputs": list(LAYER_A_ALLOWED),
        "prohibited_claims": list(LAYER_A_PROHIBITED),
        "claim_ceiling": "GENE_AUTONOMOUS_EVIDENCE_ONLY_JUDGMENT_DEFERRED",
    }
    return _receipt(basis, "gene_evidence_receipt_id")


# --- Layer B --------------------------------------------------------------------------------

def build_layer_b(stage: LoadedStage, layer_a: Mapping[str, Any]) -> dict[str, Any]:
    """Exact-locus context receipt. Cites Layer A by id (one-way). Requires digest-bound
    locus context, ordered roster with coordinates/membership, and bound local channels.
    Cohort manifest / global denominator are NOT REQUIRED here."""
    if layer_a.get("stage_receipt_sha256") != stage.stage_receipt_sha256:
        raise LayerHold("LAYER_B_CONTEXT_BINDING_HOLD", "Layer A receipt is bound to a different stage")
    holds: list[str] = []
    context = stage.locus_context
    if not _SHA256.match(str(context.get("source_sha256", "")).lower()):
        holds.append("LAYER_B_EXACT_LOCUS_HOLD")
    for gene in stage.gene_roster:
        if not all(gene.get(k) for k in ("cds_start", "cds_end", "strand", "membership")):
            holds.append("LAYER_B_EXACT_LOCUS_HOLD")
            break
    diagnostics = build_locus_diagnostics(stage)
    if "CANONICAL_FRAGMENT_CEILING_TRIPPED" in diagnostics["diagnostic_flags"]:
        holds.append("LAYER_B_BOUNDARY_CEILING")
    if "INTERNAL_INTERVAL_CONFLICT" in diagnostics["diagnostic_flags"]:
        holds.append("LAYER_B_CONTEXT_BINDING_HOLD")
    coverage = _channel_coverage(stage)
    context_states: dict[str, Any] = {}
    for channel in CONTEXT_CHANNELS:
        states = coverage[channel]["mapped_states"]
        context_states[channel] = states
        if states.get("NOT_RUN") or states.get("INGEST_GAP") or states.get("PROVENANCE_HOLD"):
            holds.append("LAYER_B_CHANNEL_GAP")
    pair_rows = build_nr_clustered_nr_disagreement(stage)
    ranked = rank_important_genes(stage, pair_rows)
    next_analysis = choose_highest_information_next_analysis(stage, ranked, pair_rows)
    basis = {
        "schema_version": LAYER_B_SCHEMA,
        "layer": "B",
        "cites": {"gene_evidence_receipt_id": layer_a["gene_evidence_receipt_id"]},
        "identity": dict(stage.identity),
        "identity_token": stage.identity_token,
        "stage_id": stage.stage_receipt["stage_id"],
        "stage_receipt_sha256": stage.stage_receipt_sha256,
        "locus_source": {"locator": context.get("source_locator", ""), "sha256": context.get("source_sha256", "")},
        "diagnostics": diagnostics,
        "context_channel_states": context_states,
        "ranked_gene_count": len(ranked),
        "top_ranked_genes": [
            {k: row[k] for k in ("locus_tag", "review_rank", "review_priority")} for row in ranked[:10]
        ],
        "ranking_note": "review order only; 0.65/0.35 weights are provisional expert-set constants (uncalibrated)",
        "highest_information_next_analysis": next_analysis,
        "not_required": {k: "NOT_REQUIRED_FOR_LAYER_B" for k in ("cohort_manifest", "global_denominator", "greater_dataset_coverage")},
        "holds": sorted(set(holds)),
        "readiness": "B_HELD" if holds else "B_READY",
        "prohibited_claims": list(LAYER_B_PROHIBITED),
        "figure_factory_overlay_basis_layer": "B",
        "claim_ceiling": "EXACT_LOCUS_CONTEXT_ONLY_NO_COHORT_CLAIMS_JUDGMENT_DEFERRED",
    }
    return _receipt(basis, "locus_context_receipt_id")


# --- Layer C --------------------------------------------------------------------------------

def build_layer_c(layer_b: Mapping[str, Any], cohort_manifest: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Cohort/population readiness receipt. Emits READY only with an external, digest-bound
    membership manifest, an explicit denominator, and comparability declarations. Holds
    suppress ONLY Layer C outputs. Prefixes are never membership authority."""
    holds: list[str] = []
    manifest_summary: dict[str, Any] = {}
    if not cohort_manifest:
        holds += ["LAYER_C_MANIFEST_HOLD", "LAYER_C_DENOMINATOR_HOLD", "LAYER_C_COMPARABILITY_HOLD"]
    else:
        locator = str(cohort_manifest.get("logical_locator", ""))
        digest = str(cohort_manifest.get("sha256", "")).lower()
        if not locator or not _SHA256.match(digest):
            holds.append("LAYER_C_MANIFEST_HOLD")
        members = cohort_manifest.get("members")
        if not isinstance(members, list) or not members:
            holds.append("LAYER_C_MEMBERSHIP_HOLD")
        elif any(_PREFIX_ONLY.match(str(m)) for m in members):
            holds.append("LAYER_C_MEMBERSHIP_HOLD")  # a prefix or glob is not a member list
        denominator = cohort_manifest.get("denominator")
        if not isinstance(denominator, int) or denominator <= 0:
            holds.append("LAYER_C_DENOMINATOR_HOLD")
        elif isinstance(members, list) and len(members) != denominator:
            holds.append("LAYER_C_DENOMINATOR_HOLD")
        for key in ("schema_version_policy", "database_snapshot_policy", "missingness_policy"):
            if not str(cohort_manifest.get(key, "")).strip():
                holds.append("LAYER_C_COMPARABILITY_HOLD")
        manifest_summary = {
            "logical_locator": locator, "sha256": digest,
            "member_count": len(members) if isinstance(members, list) else 0,
            "denominator": denominator,
        }
    basis = {
        "schema_version": LAYER_C_SCHEMA,
        "layer": "C",
        "cites": {"locus_context_receipt_id": layer_b["locus_context_receipt_id"]},
        "identity": dict(layer_b["identity"]),
        "cohort_manifest": manifest_summary,
        "membership_authority": "EXTERNAL_DIGEST_BOUND_MANIFEST_ONLY_PREFIXES_NEVER",
        "holds": sorted(set(holds)),
        "readiness": "C_HELD" if holds else "C_READY",
        "outputs_emitted": [],  # v1 computes no cohort statistic; readiness only
        "claim_ceiling": "NO_COHORT_CLAIM_WITHOUT_MANIFEST_AND_DENOMINATOR_JUDGMENT_DEFERRED",
    }
    return _receipt(basis, "cohort_analysis_receipt_id")


# --- driver ---------------------------------------------------------------------------------

def build_layers(stage_dir: str | Path, cohort_manifest: Mapping[str, Any] | None = None) -> dict[str, Any]:
    stage = load_sealed_stage(stage_dir)
    a = build_layer_a(stage)
    b = build_layer_b(stage, a)
    c = build_layer_c(b, cohort_manifest)
    return {"A": a, "B": b, "C": c, "identity_token": stage.identity_token}


def _write_exclusive(path: Path, value: Any) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError:
        raise LayerHold("MODEB_GF2_OUTPUT_REFUSED", f"layer receipt exists (immutable): {path.name}")


def write_layer_receipts(stage_dir: str | Path, output_root: str | Path,
                         cohort_manifest: Mapping[str, Any] | None = None,
                         now_utc: datetime | None = None) -> dict[str, Any]:
    layers = build_layers(stage_dir, cohort_manifest)
    root = Path(output_root)
    if not root.is_dir():
        raise LayerHold("MODEB_GF2_OUTPUT_REFUSED", "output root must already exist")
    token = layers["identity_token"]
    stamp = (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    written = {}
    for layer, name in (("A", "gene_evidence_receipt"), ("B", "locus_context_receipt"), ("C", "cohort_analysis_receipt")):
        path = root / f"{token}__{name}.json"
        _write_exclusive(path, {**layers[layer], "written_utc": stamp})
        written[layer] = str(path)
    return {"written": written, "readiness": {k: layers[k]["readiness"] for k in "ABC"}}


__all__ = [
    "LAYER_A_SCHEMA", "LAYER_B_SCHEMA", "LAYER_C_SCHEMA", "LayerHold",
    "build_layer_a", "build_layer_b", "build_layer_c", "build_layers", "write_layer_receipts",
]
