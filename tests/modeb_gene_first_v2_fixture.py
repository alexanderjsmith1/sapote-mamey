"""Generic synthetic fixture builder for Mode B gene-first v2 tests."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from mamey.mode_b.gene_first_stage_v2 import (
    CONTEXT_SCHEMA,
    EVIDENCE_FIELDS,
    IDENTITY_SCHEMA,
    PRODUCER_FIELDS,
    ROSTER_FIELDS,
    identity_token,
    query_roster_sha256,
    seal_stage,
)


IDENTITY = {
    "strain": "SYNTH-001",
    "full_node": "NODE_7_length_120000_cov_42.5",
    "region": "region002",
    "bgc_alias": "BGC007",
    "exact_identity": "SYNTH-001 / NODE_7_length_120000_cov_42.5 / region002 / BGC007",
}


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def refresh_producer_roster_digest(paths) -> str:
    """GF3-1 (schema v2.1): coordinates, strand, and membership are digest-visible.
    A test that legitimately edits the roster must rebind its producer receipts to
    the new roster digest — exactly what a real producer rerun would do. Returns
    the new digest so callers can assert on it."""
    from mamey.mode_b.gene_first_stage_v2 import PRODUCER_FIELDS, query_roster_sha256
    rows = read_tsv(paths["roster"])
    digest = query_roster_sha256(IDENTITY, rows)

    def rebind(producer_rows):
        for row in producer_rows:
            row["query_roster_sha256"] = digest

    rewrite_tsv(paths["producers"], PRODUCER_FIELDS, rebind)
    return digest


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv(path: Path, fields: tuple[str, ...], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=list(fields))
        writer.writeheader()
        writer.writerows(rows)


def rewrite_tsv(
    path: Path,
    fields: tuple[str, ...],
    transform: Callable[[list[dict[str, str]]], None],
) -> None:
    rows = read_tsv(path)
    transform(rows)
    write_tsv(path, fields, rows)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _identity_fields() -> dict[str, str]:
    return dict(IDENTITY)


def make_unsealed_stage(tmp_path: Path) -> tuple[Path, dict[str, Path]]:
    token = identity_token(IDENTITY)
    stage = tmp_path / token
    stage.mkdir()
    paths = {
        "identity": stage / f"{token}__identity.json",
        "roster": stage / f"{token}__gene_roster.tsv",
        "evidence": stage / f"{token}__evidence_observations.tsv",
        "context": stage / f"{token}__locus_context.json",
        "producers": stage / f"{token}__producer_receipts.tsv",
        "receipt": stage / f"{token}__stage_receipt.json",
    }
    write_json(
        paths["identity"],
        {
            "schema_version": IDENTITY_SCHEMA,
            **_identity_fields(),
            "identity_token": token,
            "source_package_locator": "package://synthetic/package/manifest.json",
            "source_package_sha256": digest("synthetic-package"),
            "region_source_locator": "package://synthetic/regions/region002.gbk",
            "region_source_sha256": digest("synthetic-region"),
        },
    )
    genes = [
        {
            **_identity_fields(),
            "membership": "EXACT_REGION",
            "locus_tag": "syn_core_001",
            "gene_order": "1",
            "cds_start": "1000",
            "cds_end": "3001",
            "strand": "+",
            "protein_length_aa": "666",
            "protein_sha256": digest("protein-syn-core-001"),
            "antismash_role": "biosynthetic",
            "gene_kind": "CORE_SYNTHASE",
            "partial_state": "COMPLETE",
            "boundary_proximity": "INTERIOR",
            "source_locator": "package://synthetic/regions/region002.gbk#syn_core_001",
            "source_sha256": digest("synthetic-region"),
        },
        {
            **_identity_fields(),
            "membership": "EXACT_REGION",
            "locus_tag": "syn_tailor_002",
            "gene_order": "2",
            "cds_start": "3200",
            "cds_end": "4100",
            "strand": "-",
            "protein_length_aa": "299",
            "protein_sha256": digest("protein-syn-tailor-002"),
            "antismash_role": "biosynthetic-additional",
            "gene_kind": "TAILORING_OXIDOREDUCTASE",
            "partial_state": "COMPLETE",
            "boundary_proximity": "INTERIOR",
            "source_locator": "package://synthetic/regions/region002.gbk#syn_tailor_002",
            "source_sha256": digest("synthetic-region"),
        },
        {
            **_identity_fields(),
            "membership": "EXACT_REGION",
            "locus_tag": "syn_reg_003",
            "gene_order": "3",
            "cds_start": "4300",
            "cds_end": "4900",
            "strand": "+",
            "protein_length_aa": "199",
            "protein_sha256": digest("protein-syn-reg-003"),
            "antismash_role": "regulatory",
            "gene_kind": "TRANSCRIPTIONAL_REGULATOR",
            "partial_state": "COMPLETE",
            "boundary_proximity": "INTERIOR",
            "source_locator": "package://synthetic/regions/region002.gbk#syn_reg_003",
            "source_sha256": digest("synthetic-region"),
        },
    ]
    write_tsv(paths["roster"], ROSTER_FIELDS, genes)
    roster_digest = query_roster_sha256(IDENTITY, genes)

    channels = (
        "nr",
        "clustered_nr",
        "local_swissprot",
        "mibig",
        "domain",
        "cassette",
        "neighborhood",
    )
    producers: list[dict[str, str]] = []
    for channel in channels:
        producer_state = "REGISTRY_ONLY" if channel == "cassette" else "COMPLETE"
        completeness = "NOT_APPLICABLE" if channel == "cassette" else "EXACT_LOCUS_COMPLETE"
        producers.append(
            {
                "producer_id": f"producer_{channel}",
                "channel": channel,
                "producer_state": producer_state,
                "completeness": completeness,
                "tool_name": f"synthetic-{channel}-producer",
                "tool_version": "1.0",
                "parameter_fingerprint": digest(f"params-{channel}"),
                "query_roster_sha256": roster_digest,
                "database_id": f"synthetic_{channel}_db",
                "database_version": "fixture-v1",
                "database_sha256": digest(f"database-{channel}"),
                "output_locator": f"evidence://synthetic/{channel}/normalized.tsv",
                "output_sha256": digest(f"output-{channel}"),
                "output_bytes": "123",
                "receipt_sha256": digest(f"receipt-{channel}"),
                "threads_used": "1",
                "resource_policy_id": "SYNTHETIC_LOW_CPU_MAX_2",
                "started_utc": "2026-01-01T00:00:00+00:00",
                "finished_utc": "2026-01-01T00:00:01+00:00",
                "duration_seconds": "1.0",
            }
        )
    write_tsv(paths["producers"], PRODUCER_FIELDS, producers)
    producer_by_channel = {row["channel"]: row for row in producers}

    def observation(
        channel: str,
        state: str,
        *,
        locus_tag: str = "",
        rank: str = "",
        accession: str = "",
        name: str = "",
        organism: str = "",
        identity: str = "",
        positives: str = "",
        coverage: str = "",
        aligned_length: str = "",
        evalue: str = "",
        bitscore: str = "",
        family: str = "",
        label: str = "",
    ) -> dict[str, str]:
        producer = producer_by_channel[channel]
        gene = next((row for row in genes if row["locus_tag"] == locus_tag), None)
        return {
            **_identity_fields(),
            "channel": channel,
            "observation_scope": "GENE" if locus_tag else "BGC",
            "locus_tag": locus_tag,
            "mapped_state": state,
            "source_state": f"SYNTHETIC_{state}",
            "query_sha256": gene["protein_sha256"] if gene else "",
            "hit_rank": rank,
            "subject_accession": accession,
            "subject_name": name,
            "subject_organism": organism,
            "pct_identity": identity,
            "pct_positives": positives,
            "query_coverage": coverage,
            "aligned_length": aligned_length,
            "evalue": evalue,
            "bitscore": bitscore,
            "functional_family_id": family,
            "evidence_label": label,
            "claim_note": "Synthetic similarity or context only; not identity, production, or activity.",
            "source_locator": producer["output_locator"],
            "source_sha256": producer["output_sha256"],
            "producer_id": producer["producer_id"],
            "producer_receipt_sha256": producer["receipt_sha256"],
            "database_id": producer["database_id"],
            "database_version": producer["database_version"],
            "database_sha256": producer["database_sha256"],
        }

    evidence: list[dict[str, str]] = []
    alignment_values = {
        "nr": {
            "syn_core_001": ("NR0001", "synthetic core synthase", "Organism alpha", "72", "82", "91", "600", "1e-80", "500", "core_family"),
            "syn_tailor_002": ("NR0002", "synthetic oxidoreductase", "Organism beta", "65", "74", "88", "270", "1e-40", "260", "tailor_family"),
            "syn_reg_003": ("NR0003", "synthetic regulator", "Organism gamma", "58", "69", "83", "180", "1e-20", "150", "regulator_family"),
        },
        "clustered_nr": {
            "syn_core_001": ("CNR0101", "synthetic alternate synthase", "Organism delta", "54", "63", "60", "390", "1e-30", "220", "alternate_core_family"),
            "syn_tailor_002": ("CNR0102", "synthetic oxidoreductase cluster", "Organism beta", "63", "72", "85", "265", "1e-35", "240", "tailor_family"),
        },
        "local_swissprot": {
            "syn_core_001": ("SP0001", "reviewed synthetic enzyme", "Organism epsilon", "60", "70", "76", "500", "1e-45", "310", "curated_core_family"),
            "syn_tailor_002": ("SP0002", "reviewed synthetic oxidoreductase", "Organism beta", "61", "70", "82", "255", "1e-32", "225", "tailor_family"),
            "syn_reg_003": ("SP0003", "reviewed synthetic regulator", "Organism gamma", "55", "65", "78", "170", "1e-17", "130", "regulator_family"),
        },
    }
    for channel, by_tag in alignment_values.items():
        for gene in genes:
            tag = gene["locus_tag"]
            if tag not in by_tag:
                evidence.append(observation(channel, "NO_BOUND_HIT", locus_tag=tag))
                continue
            values = by_tag[tag]
            evidence.append(
                observation(
                    channel,
                    "BOUND",
                    locus_tag=tag,
                    rank="1",
                    accession=values[0],
                    name=values[1],
                    organism=values[2],
                    identity=values[3],
                    positives=values[4],
                    coverage=values[5],
                    aligned_length=values[6],
                    evalue=values[7],
                    bitscore=values[8],
                    family=values[9],
                )
            )
    evidence.extend(
        [
            observation(
                "mibig",
                "BOUND",
                accession="MIBIG_SYNTHETIC_REFERENCE_0001",
                name="synthetic reference cluster",
                label="synthetic reference relation",
            ),
            observation(
                "domain",
                "BOUND",
                locus_tag="syn_core_001",
                label="synthetic core domain architecture",
            ),
            observation(
                "cassette",
                "REGISTRY_ONLY_NOT_EXECUTED",
                label="synthetic registry definition only",
            ),
            observation(
                "neighborhood",
                "BOUND",
                locus_tag="syn_core_001",
                label="synthetic ordered neighborhood context",
            ),
        ]
    )
    write_tsv(paths["evidence"], EVIDENCE_FIELDS, evidence)
    write_json(
        paths["context"],
        {
            "schema_version": CONTEXT_SCHEMA,
            **_identity_fields(),
            "region_start": 1000,
            "region_end": 90000,
            "contig_length": 120000,
            "bgc_boundary_state": "INTERIOR",
            "assembly_fragmentation_tier": "DRAFT",
            "detector_window_state": "WHOLE_REGION",
            "canonical_fragment_ceiling_state": "CLEAR",
            "canonical_fragment_ceiling_reason": "Synthetic canonical ceiling is clear.",
            "canonical_fragment_ceiling_owner": "mamey.fragment_ceiling",
            "source_locator": "package://synthetic/context/locus_context.json",
            "source_sha256": digest("synthetic-context"),
        },
    )
    return stage, paths


def make_sealed_stage(tmp_path: Path) -> tuple[Path, dict[str, Path], dict[str, Any]]:
    stage, paths = make_unsealed_stage(tmp_path)
    receipt = seal_stage(
        stage,
        max_threads=2,
        sealed_utc="2026-01-01T00:00:02+00:00",
    )
    return stage, paths, receipt
