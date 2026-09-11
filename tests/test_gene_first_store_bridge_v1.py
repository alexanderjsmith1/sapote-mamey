"""Evidence-store bridge round trip (V4 §7 required test — Black Cherry-4).

Builds a generic rev5-layout BLASTp evidence-store fixture (parsed round table + round
manifest + archived query FASTA), bridges it into stage rows for `nr`, swaps those rows
into a fixture stage, SEALS and RELOADS the stage, and matches every carried field back to
the source store rows. Also pins: read-only store, typed gaps (no XML2 positives → gap, not
BOUND; unqueried gene → NOT_RUN; queried-no-hit → NO_BOUND_HIT), query-hash conflict
refusal, node-corroboration refusal, and that the shortened defline node never reaches a
stage row. Synthetic identities only.
"""
from __future__ import annotations

import csv
import hashlib
import json

import pytest

from mamey.blastp_evidence_store import HIT_FIELDS, STORE_VERSION
from mamey.mode_b.gene_first_stage_v2 import (
    EVIDENCE_FIELDS,
    PRODUCER_FIELDS,
    StageHold,
    load_sealed_stage,
    seal_stage,
)
from mamey.mode_b.gene_first_store_bridge import BridgeHold, bridge_round, protein_sha256
from tests.modeb_gene_first_v2_fixture import (
    IDENTITY,
    make_unsealed_stage,
    read_tsv,
    write_tsv,
)

ROUND = "R001"
SEQS = {"syn_core_001": "MKVLAAGIVALLL", "syn_tailor_002": "MSTQPWERTYIPAS", "syn_reg_003": "MNRQLVKPDEST"}


def _defline(gene: str) -> str:
    return f"SYNTH-001|BGC007|slot=1|gene={gene}|node=NODE_7|region=region2|aa=13"


def _hit(gene: str, **over):
    row = {f: "" for f in HIT_FIELDS}
    row.update({
        "round_id": ROUND, "strain": "SYNTH-001", "bgc_id": "BGC007", "query_gene": gene,
        "node": "NODE_7", "region": "region2", "query_id": _defline(gene),
        "subject_id": f"WP_{gene}", "subject_accession": f"WP_{gene}.1",
        "subject_title": f"polyketide synthase [{gene}]", "subject_sciname": "Streptomyces sp.",
        "subject_taxid": "1883", "pct_identity": "71.5", "pct_positive": "83.0", "align_len": "410",
        "query_len": "420", "query_coverage": "0.9762", "evalue": "1e-150", "bitscore": "512.0",
        "evidence_tier": "TIER_A_CLASS_DEFINING", "next_action": "RETAIN_FOR_CLASS_PROOF_TABLE",
        "claim_safety": "similarity is not identity",
    })
    row.update(over)
    return row


def _store(tmp_path, hits, *, fasta_genes=None, roster_seqs=SEQS):
    store = tmp_path / "store"
    parsed = store / "parsed_rounds" / ROUND
    raw = store / "raw_ncbi_downloads" / ROUND
    parsed.mkdir(parents=True)
    raw.mkdir(parents=True)
    top = parsed / "BLASTP_top_hits_by_query.csv"
    with top.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=HIT_FIELDS)
        writer.writeheader()
        writer.writerows(hits)
    fasta = raw / "queries.fasta"
    genes = list(roster_seqs) if fasta_genes is None else fasta_genes
    fasta.write_text("".join(f">{_defline(g)}\n{roster_seqs[g]}\n" for g in genes))
    manifest = {
        "store_version": STORE_VERSION, "ingested_utc": "2026-01-01T00:00:00+00:00",
        "strain": "SYNTH-001", "round_id": ROUND, "purpose": "manual_iterative_blastp",
        "operator_note": "", "query_count": len(genes), "all_hit_count": len(hits),
        "raw_files": [{"kind": "fasta", "path": f"raw_ncbi_downloads/{ROUND}/queries.fasta",
                       "sha256": hashlib.sha256(fasta.read_bytes()).hexdigest(), "bytes": fasta.stat().st_size}],
        "claim_safety": "similarity is not identity",
    }
    (store / "BLASTP_round_manifest.jsonl").write_text(json.dumps(manifest, sort_keys=True) + "\n")
    return store


def _roster_with_real_digests(paths):
    rows = read_tsv(paths["roster"])
    for row in rows:
        row["protein_sha256"] = protein_sha256(SEQS[row["locus_tag"]])
    from mamey.mode_b.gene_first_stage_v2 import ROSTER_FIELDS
    write_tsv(paths["roster"], ROSTER_FIELDS, rows)
    return rows


def _snapshot(store):
    return {p.relative_to(store).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in store.rglob("*") if p.is_file()}


def _install(paths, result):
    """Swap the fixture's synthetic nr producer/evidence rows for the bridged ones and
    rebind the OTHER producers to the (now real-digest) roster."""
    from mamey.mode_b.gene_first_stage_v2 import query_roster_sha256
    roster = read_tsv(paths["roster"])
    digest = query_roster_sha256(IDENTITY, roster)
    producers = [r for r in read_tsv(paths["producers"]) if r["channel"] != "nr"]
    for r in producers:
        r["query_roster_sha256"] = digest
    producers.append(result["producer"])
    write_tsv(paths["producers"], PRODUCER_FIELDS, producers)
    evidence = [r for r in read_tsv(paths["evidence"]) if r["channel"] != "nr"]
    for r in evidence:
        if r["locus_tag"]:
            r["query_sha256"] = next(x["protein_sha256"] for x in roster if x["locus_tag"] == r["locus_tag"])
    evidence.extend(result["evidence"])
    write_tsv(paths["evidence"], EVIDENCE_FIELDS, evidence)


def _bridge(store, roster, **over):
    kwargs = dict(store_dir=store, round_id=ROUND, channel="nr", identity=IDENTITY,
                  gene_roster=roster, database_id="ncbi_nr", database_version="2026-01-01")
    kwargs.update(over)
    return bridge_round(**kwargs)


# --- the V4 round trip ---------------------------------------------------------------------

def test_round_trip_seal_reload_matches_every_carried_field(tmp_path):
    hits = [_hit("syn_core_001"), _hit("syn_tailor_002", pct_identity="44.0", evalue="3e-20", bitscore="120.5")]
    store = _store(tmp_path, hits)
    before = _snapshot(store)
    stage, paths = make_unsealed_stage(tmp_path)
    roster = _roster_with_real_digests(paths)

    result = _bridge(store, roster)
    assert _snapshot(store) == before, "bridge wrote to the store"
    _install(paths, result)
    seal_stage(stage, max_threads=2, sealed_utc="2026-01-01T00:00:02+00:00")
    loaded = load_sealed_stage(stage)

    bridged = {row["locus_tag"]: row for row in loaded.evidence if row["channel"] == "nr"}
    by_gene = {h["query_gene"]: h for h in hits}
    for gene, hit in by_gene.items():
        row = bridged[gene]
        assert row["mapped_state"] == "BOUND"
        assert row["subject_accession"] == hit["subject_accession"]
        assert row["subject_name"] == hit["subject_title"]
        assert row["subject_organism"] == hit["subject_sciname"]
        assert row["pct_identity"] == hit["pct_identity"]
        assert row["pct_positives"] == hit["pct_positive"]
        assert float(row["query_coverage"]) == pytest.approx(float(hit["query_coverage"]) * 100, abs=0.01)
        assert row["aligned_length"] == hit["align_len"]
        assert row["evalue"] == hit["evalue"] and row["bitscore"] == hit["bitscore"]
        assert row["evidence_label"] == hit["evidence_tier"]
        assert row["query_sha256"] == protein_sha256(SEQS[gene])
        assert row["source_sha256"] == result["receipt"]["output_sha256"]
        assert row["database_id"] == "ncbi_nr"
        assert "NODE_7\t" not in json.dumps(row) and row["full_node"] == IDENTITY["full_node"]
    # The third roster gene was in the FASTA (queried) but had no hit -> NO_BOUND_HIT, typed.
    assert bridged["syn_reg_003"]["mapped_state"] == "NO_BOUND_HIT"
    assert "STORE_QUERY_NO_HIT" in bridged["syn_reg_003"]["source_state"]
    assert result["receipt"]["row_counts"] == {"BOUND": 2, "NO_BOUND_HIT": 1, "NOT_RUN": 0, "INGEST_GAP": 0, "PROVENANCE_HOLD": 0}


# --- typed gaps, never silent -----------------------------------------------------------------

def test_hit_without_positives_becomes_typed_ingest_gap_not_bound(tmp_path):
    store = _store(tmp_path, [_hit("syn_core_001", pct_positive="")])
    _, paths = make_unsealed_stage(tmp_path)
    roster = _roster_with_real_digests(paths)
    result = _bridge(store, roster)
    row = next(r for r in result["evidence"] if r["locus_tag"] == "syn_core_001")
    assert row["mapped_state"] == "INGEST_GAP"
    assert "STORE_HIT_MISSING_PCT_POSITIVES" in row["source_state"]
    assert row["pct_identity"] == "" and row["bitscore"] == ""  # nothing coerced to zero


def test_unqueried_gene_is_not_run(tmp_path):
    store = _store(tmp_path, [_hit("syn_core_001")], fasta_genes=["syn_core_001"])
    _, paths = make_unsealed_stage(tmp_path)
    roster = _roster_with_real_digests(paths)
    result = _bridge(store, roster)
    states = {r["locus_tag"]: r["mapped_state"] for r in result["evidence"]}
    assert states == {"syn_core_001": "BOUND", "syn_tailor_002": "NOT_RUN", "syn_reg_003": "NOT_RUN"}


def test_missing_archived_fasta_yields_provenance_hold_not_bound(tmp_path):
    store = _store(tmp_path, [_hit("syn_core_001")])
    manifest_path = store / "BLASTP_round_manifest.jsonl"
    manifest = json.loads(manifest_path.read_text())
    manifest["raw_files"] = []
    manifest_path.write_text(json.dumps(manifest) + "\n")
    _, paths = make_unsealed_stage(tmp_path)
    roster = _roster_with_real_digests(paths)
    result = _bridge(store, roster)
    row = next(r for r in result["evidence"] if r["locus_tag"] == "syn_core_001")
    assert row["mapped_state"] == "PROVENANCE_HOLD"
    assert "QUERY_SEQUENCE_NOT_IN_ARCHIVED_FASTA" in row["source_state"]
    assert result["receipt"]["fasta_state"] == "ROUND_FASTA_NOT_ARCHIVED"


# --- refusals ---------------------------------------------------------------------------------

def test_query_hash_conflict_refuses(tmp_path):
    store = _store(tmp_path, [_hit("syn_core_001")], roster_seqs={**SEQS, "syn_core_001": "MDIFFERENTSEQ"})
    _, paths = make_unsealed_stage(tmp_path)
    roster = _roster_with_real_digests(paths)  # roster digests from SEQS, FASTA from a different sequence
    with pytest.raises(BridgeHold) as exc:
        _bridge(store, roster)
    assert exc.value.code == "MODEB_GF2_QUERY_HASH_HOLD"


def test_node_number_contradiction_refuses(tmp_path):
    bad = _hit("syn_core_001")
    bad["query_id"] = bad["query_id"].replace("node=NODE_7", "node=NODE_99")
    store = _store(tmp_path, [bad])
    _, paths = make_unsealed_stage(tmp_path)
    roster = _roster_with_real_digests(paths)
    with pytest.raises(BridgeHold) as exc:
        _bridge(store, roster)
    assert exc.value.code == "MODEB_GF2_IDENTITY_HOLD"


def test_unknown_round_refuses(tmp_path):
    store = _store(tmp_path, [_hit("syn_core_001")])
    _, paths = make_unsealed_stage(tmp_path)
    roster = _roster_with_real_digests(paths)
    with pytest.raises(BridgeHold) as exc:
        _bridge(store, roster, round_id="R999")
    assert exc.value.code == "MODEB_GF2_PRODUCER_HOLD"


def test_non_alignment_channel_refused_in_v1(tmp_path):
    store = _store(tmp_path, [_hit("syn_core_001")])
    _, paths = make_unsealed_stage(tmp_path)
    roster = _roster_with_real_digests(paths)
    with pytest.raises(BridgeHold) as exc:
        _bridge(store, roster, channel="mibig")
    assert exc.value.code == "MODEB_GF2_CHANNEL_HOLD"
