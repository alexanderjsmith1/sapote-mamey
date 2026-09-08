"""Evidence-store bridge for the Mode B gene-first stage (V4 §7 — successor r4).

Reads admitted rows from the estate's ONE BLASTp evidence store
(`mamey.blastp_evidence_store`, rev5 layout: `parsed_rounds/<round>/…csv` +
`BLASTP_round_manifest.jsonl` + archived `raw_ncbi_downloads/<round>/`) and emits
stage-format producer receipts and evidence observations for the alignment channels
(`nr`, `clustered_nr`, `local_swissprot`) — so the gene-first stage never grows a ninth
independent BLASTp data path. MIBiG relations are a separate producer (v2 of this bridge).

Hard rules:
- READ-ONLY on the store. Nothing is written back, renamed, or normalized in place.
- Every emitted BOUND row carries the store's own source locator + digest, the query's
  protein SHA-256 (computed from the archived round FASTA, never assumed), the declared
  database identity, and a producer receipt digest. Rows the sealer could not admit as
  BOUND (a hit-table-only round with no `pct_positive`, an unknown coverage) become TYPED
  gaps with the reason in `source_state` — never silently dropped, never coerced to zero.
- Identity is the four-part stage identity. The store's defline `node=NODE_11` token is a
  SHORTENED form by construction; it is used only to corroborate the full node's numeric id
  and is never written into any stage row (HARD node-naming rule).
- Any identity or query-hash conflict between store and roster is a typed refusal.

Claim ceiling: similarity is not identity; a bridged hit is a BLASTp observation with its
store tier as a label, not a functional-family call; judgment deferred.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from mamey.blastp_followup import parse_query_id
from mamey.mode_b.gene_first_stage_v2 import (
    ALIGNMENT_CHANNELS,
    EVIDENCE_FIELDS,
    IDENTITY_FIELDS,
    PRODUCER_FIELDS,
    StageHold,
    _normalize_identity_component,
    canonical_identity,
    query_roster_sha256,
)

BRIDGE_SCHEMA = "modeb_gene_first_store_bridge_v1"
RESOURCE_POLICY_ID = "blastp_store_bridge_v1"
CLAIM_NOTE = (
    "BLASTp similarity from the evidence store; similarity is not identity, capacity is not "
    "production or activity; store tier is a label, not a functional-family call; judgment deferred."
)
_NODE_NUMBER = re.compile(r"^NODE_(\d+)", re.IGNORECASE)


class BridgeHold(StageHold):
    """Typed bridge refusal (a StageHold subclass so callers can treat it uniformly)."""


def _hold(code: str, detail: str) -> None:
    raise BridgeHold(code, detail)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def protein_sha256(sequence: str) -> str:
    """Canonical query-sequence digest: uppercase, whitespace/terminal-stop stripped."""
    clean = "".join(sequence.split()).upper().rstrip("*")
    return _sha256_text(clean)


def read_round_fasta(path: Path) -> dict[str, str]:
    """query_id -> protein_sha256 for every record in an archived round FASTA."""
    digests: dict[str, str] = {}
    current: str | None = None
    chunks: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(">"):
            if current is not None:
                digests[current] = protein_sha256("".join(chunks))
            current = line[1:].strip()
            chunks = []
        elif current is not None:
            chunks.append(line.strip())
    if current is not None:
        digests[current] = protein_sha256("".join(chunks))
    return digests


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _corroborate_node(store_node: str, full_node: str, label: str) -> None:
    """The defline node token is shortened by construction; only its numeric id can be
    checked. A mismatch is a refusal; agreement is corroboration, never identity."""
    if not store_node:
        return
    a, b = _NODE_NUMBER.match(store_node), _NODE_NUMBER.match(full_node)
    if a and b and a.group(1) != b.group(1):
        _hold("MODEB_GF2_IDENTITY_HOLD",
              f"{label}: store node {store_node!r} contradicts stage node {full_node!r}")


def bridge_round(
    *,
    store_dir: str | Path,
    round_id: str,
    channel: str,
    identity: Mapping[str, str],
    gene_roster: Sequence[Mapping[str, str]],
    database_id: str,
    database_version: str,
    database_sha256: str | None = None,
    tool_name: str = "ncbi_blastp",
    tool_version: str = "web-service-unversioned",
) -> dict[str, Any]:
    """Bridge one store round into stage rows for one alignment channel.

    Returns {"producer": row, "evidence": [rows], "receipt": {...}}. Raises BridgeHold on
    any identity/query-hash conflict or missing provenance. Never touches the store.
    """
    if channel not in ALIGNMENT_CHANNELS:
        _hold("MODEB_GF2_CHANNEL_HOLD", f"bridge v1 covers {sorted(ALIGNMENT_CHANNELS)}, not {channel!r}")
    store = Path(store_dir)
    canonical = canonical_identity(identity)
    manifest_rows = [r for r in _read_jsonl(store / "BLASTP_round_manifest.jsonl") if r.get("round_id") == round_id]
    if not manifest_rows:
        _hold("MODEB_GF2_PRODUCER_HOLD", f"round {round_id!r} is not in the store manifest")
    manifest = manifest_rows[-1]
    if manifest.get("strain") and manifest["strain"] != canonical["strain"]:
        _hold("MODEB_GF2_IDENTITY_HOLD",
              f"store round strain {manifest['strain']!r} != stage strain {canonical['strain']!r}")

    parsed_dir = store / "parsed_rounds" / round_id
    top_path = parsed_dir / "BLASTP_top_hits_by_query.csv"
    if not top_path.is_file():
        _hold("MODEB_GF2_PRODUCER_HOLD", f"round {round_id!r} has no parsed top-hits table")
    top_rows = _read_csv(top_path)
    output_locator = f"blastp-store://{round_id}/parsed_rounds/BLASTP_top_hits_by_query.csv"
    output_sha = _sha256_file(top_path)

    # Query digests from the archived FASTA — the only honest source of query_sha256.
    fasta_entries = [f for f in manifest.get("raw_files", []) if f.get("kind") == "fasta"]
    fasta_digests: dict[str, str] = {}
    fasta_state = "ROUND_FASTA_ARCHIVED"
    if fasta_entries:
        fasta_path = store / fasta_entries[0]["path"]
        if not fasta_path.is_file() or _sha256_file(fasta_path) != fasta_entries[0].get("sha256"):
            _hold("MODEB_GF2_PRODUCER_HOLD", f"round {round_id!r} archived FASTA missing or digest mismatch")
        fasta_digests = read_round_fasta(fasta_path)
    else:
        fasta_state = "ROUND_FASTA_NOT_ARCHIVED"

    if database_sha256 is None:
        # Rolling databases (NCBI nr) have no stable digest; bind the round's manifest
        # line instead and SAY SO in every row's source_state.
        database_sha256 = _sha256_text(json.dumps(manifest, sort_keys=True))
        db_digest_note = "DATABASE_DIGEST_IS_ROUND_MANIFEST_PROXY"
    else:
        db_digest_note = "DATABASE_DIGEST_DECLARED"

    roster_digest = query_roster_sha256(identity, gene_roster)
    producer_id = f"blastp_store:{round_id}:{channel}"
    producer: dict[str, str] = {
        "producer_id": producer_id,
        "channel": channel,
        "producer_state": "COMPLETE",
        "completeness": "EXACT_LOCUS_COMPLETE",
        "tool_name": tool_name,
        "tool_version": tool_version,
        "parameter_fingerprint": _sha256_text(f"{manifest.get('purpose', '')}|{round_id}|{channel}"),
        "query_roster_sha256": roster_digest,
        "database_id": database_id,
        "database_version": database_version,
        "database_sha256": database_sha256,
        "output_locator": output_locator,
        "output_sha256": output_sha,
        "output_bytes": str(top_path.stat().st_size),
        "receipt_sha256": "",
        "threads_used": "1",
        "resource_policy_id": RESOURCE_POLICY_ID,
        "started_utc": str(manifest.get("ingested_utc", "")),
        "finished_utc": str(manifest.get("ingested_utc", "")),
        "duration_seconds": "",
    }
    producer["receipt_sha256"] = _sha256_text(
        json.dumps({k: v for k, v in producer.items() if k != "receipt_sha256"}, sort_keys=True)
    )

    # Index store rows by (bgc alias, gene) after normalizing the alias the stage way.
    by_gene: dict[str, dict[str, str]] = {}
    queried: set[str] = set()
    for row in top_rows:
        meta = parse_query_id(row.get("query_id", ""))
        if meta.get("strain") and meta["strain"] != canonical["strain"]:
            continue  # another strain's rows in a shared store are simply not this locus
        alias = meta.get("bgc_id", "")
        if alias:
            try:
                alias = _normalize_identity_component("bgc_alias", alias)
            except StageHold:
                _hold("MODEB_GF2_IDENTITY_HOLD", f"store row alias {alias!r} is not a canonical BGC alias")
            if alias != canonical["bgc_alias"]:
                continue
        gene = meta.get("gene", "")
        if not gene:
            continue
        _corroborate_node(meta.get("node", ""), canonical["full_node"], f"store row {row.get('query_id')!r}")
        region = meta.get("region", "")
        if region:
            try:
                if _normalize_identity_component("region", region) != canonical["region"]:
                    _hold("MODEB_GF2_IDENTITY_HOLD",
                          f"store row region {region!r} != stage region {canonical['region']!r}")
            except StageHold as exc:
                if exc.code == "MODEB_GF2_IDENTITY_HOLD" and "!=" in exc.detail:
                    raise
        by_gene[gene] = row
        queried.add(gene)
    for fasta_query in fasta_digests:
        meta = parse_query_id(fasta_query)
        if meta.get("gene") and (not meta.get("strain") or meta["strain"] == canonical["strain"]):
            queried.add(meta["gene"])

    identity_fields = {field: canonical[field] for field in IDENTITY_FIELDS}
    evidence: list[dict[str, str]] = []
    counts = {"BOUND": 0, "NO_BOUND_HIT": 0, "NOT_RUN": 0, "INGEST_GAP": 0, "PROVENANCE_HOLD": 0}

    def gap(locus_tag: str, protein_sha: str, state: str, reason: str) -> dict[str, str]:
        counts[state] += 1
        return {
            **identity_fields, "channel": channel, "observation_scope": "GENE",
            "locus_tag": locus_tag, "mapped_state": state,
            "source_state": f"{reason};{fasta_state};{db_digest_note}",
            "query_sha256": protein_sha, "hit_rank": "", "subject_accession": "",
            "subject_name": "", "subject_organism": "", "pct_identity": "", "pct_positives": "",
            "query_coverage": "", "aligned_length": "", "evalue": "", "bitscore": "",
            "functional_family_id": "", "evidence_label": "", "claim_note": CLAIM_NOTE,
            "source_locator": output_locator, "source_sha256": output_sha,
            "producer_id": producer_id, "producer_receipt_sha256": producer["receipt_sha256"],
            "database_id": database_id, "database_version": database_version,
            "database_sha256": database_sha256,
        }

    for gene_row in gene_roster:
        locus_tag = gene_row["locus_tag"]
        protein_sha = gene_row["protein_sha256"].lower()
        hit = by_gene.get(locus_tag)
        if hit is None:
            state = "NO_BOUND_HIT" if locus_tag in queried else "NOT_RUN"
            reason = "STORE_QUERY_NO_HIT" if state == "NO_BOUND_HIT" else "STORE_ROUND_DID_NOT_QUERY_GENE"
            evidence.append(gap(locus_tag, protein_sha, state, reason))
            continue
        # Query-hash binding: the archived FASTA must carry this query, and its digest
        # must equal the roster's canonical protein digest. A mismatch is a refusal.
        fasta_sha = fasta_digests.get(hit["query_id"])
        if fasta_sha is None:
            evidence.append(gap(locus_tag, protein_sha, "PROVENANCE_HOLD",
                                "QUERY_SEQUENCE_NOT_IN_ARCHIVED_FASTA"))
            continue
        if fasta_sha != protein_sha:
            _hold("MODEB_GF2_QUERY_HASH_HOLD",
                  f"{locus_tag}: archived query digest differs from the roster protein digest")
        positives = (hit.get("pct_positive") or "").strip()
        coverage_raw = (hit.get("query_coverage") or "").strip()
        if not positives or coverage_raw in ("", "NA"):
            missing = "STORE_HIT_MISSING_PCT_POSITIVES" if not positives else "STORE_HIT_COVERAGE_UNKNOWN"
            evidence.append(gap(locus_tag, protein_sha, "INGEST_GAP", missing + ";REINGEST_ROUND_WITH_XML2"))
            continue
        coverage_pct = f"{float(coverage_raw) * 100.0:.2f}"  # store keeps a FRACTION
        counts["BOUND"] += 1
        evidence.append({
            **identity_fields, "channel": channel, "observation_scope": "GENE",
            "locus_tag": locus_tag, "mapped_state": "BOUND",
            "source_state": f"STORE_TOP_HIT_RANK1;COVERAGE_FRACTION_X100;{fasta_state};{db_digest_note}",
            "query_sha256": protein_sha, "hit_rank": "1",
            "subject_accession": hit.get("subject_accession") or hit.get("subject_id") or "",
            "subject_name": hit.get("subject_title") or hit.get("subject_id") or "",
            "subject_organism": hit.get("subject_sciname", ""),
            "pct_identity": hit.get("pct_identity", ""), "pct_positives": positives,
            "query_coverage": coverage_pct, "aligned_length": hit.get("align_len", ""),
            "evalue": hit.get("evalue", ""), "bitscore": hit.get("bitscore", ""),
            "functional_family_id": "",
            "evidence_label": hit.get("evidence_tier", ""),
            "claim_note": CLAIM_NOTE,
            "source_locator": output_locator, "source_sha256": output_sha,
            "producer_id": producer_id, "producer_receipt_sha256": producer["receipt_sha256"],
            "database_id": database_id, "database_version": database_version,
            "database_sha256": database_sha256,
        })

    for row in evidence:
        missing_fields = [f for f in EVIDENCE_FIELDS if f not in row]
        if missing_fields:
            _hold("MODEB_GF2_BOUND_ROW_HOLD", f"bridge emitted an incomplete row: {missing_fields}")
    for field in PRODUCER_FIELDS:
        producer.setdefault(field, "")

    receipt = {
        "schema": BRIDGE_SCHEMA, "round_id": round_id, "channel": channel,
        "store_version": manifest.get("store_version", ""), "store_read_only": True,
        "exact_identity": canonical["exact_identity"], "roster_sha256": roster_digest,
        "output_locator": output_locator, "output_sha256": output_sha,
        "fasta_state": fasta_state, "database_digest_note": db_digest_note,
        "row_counts": counts, "claim_note": CLAIM_NOTE,
    }
    return {"producer": producer, "evidence": evidence, "receipt": receipt}
