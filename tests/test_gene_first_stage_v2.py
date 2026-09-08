from __future__ import annotations

import pytest

from mamey.mode_b.gene_first_stage_v2 import (
    CANONICAL_CHANNELS,
    EVIDENCE_FIELDS,
    PRODUCER_FIELDS,
    ROSTER_FIELDS,
    StageHold,
    load_sealed_stage,
    seal_stage,
)

from tests.modeb_gene_first_v2_fixture import (
    make_sealed_stage,
    make_unsealed_stage,
    read_json,
    rewrite_tsv,
    write_json,
)


def test_seal_and_reload_preserve_complete_identity_and_seven_channels(tmp_path):
    stage, _paths, receipt = make_sealed_stage(tmp_path)
    loaded = load_sealed_stage(stage)

    assert loaded.identity["exact_identity"] == (
        "SYNTH-001 / NODE_7_length_120000_cov_42.5 / region002 / BGC007"
    )
    assert loaded.identity_token == (
        "SYNTH-001__NODE_7_length_120000_cov_42.5__region002__BGC007"
    )
    assert tuple(receipt["canonical_channels"]) == CANONICAL_CHANNELS
    assert {row["channel"] for row in loaded.evidence} == set(CANONICAL_CHANNELS)
    assert receipt["counts"] == {"genes": 3, "evidence_rows": 13, "producer_receipts": 7}


def test_legacy_channel_aliases_normalize_visibly_without_collapse(tmp_path):
    stage, paths = make_unsealed_stage(tmp_path)

    def alias_producer(rows):
        next(row for row in rows if row["channel"] == "clustered_nr")["channel"] = "clusterednr"

    def alias_evidence(rows):
        for row in rows:
            if row["channel"] == "clustered_nr":
                row["channel"] = "clusterednr"

    rewrite_tsv(paths["producers"], PRODUCER_FIELDS, alias_producer)
    rewrite_tsv(paths["evidence"], EVIDENCE_FIELDS, alias_evidence)
    receipt = seal_stage(stage, max_threads=2, sealed_utc="2026-01-01T00:00:02+00:00")
    loaded = load_sealed_stage(stage)

    assert {row["channel"] for row in loaded.evidence} == set(CANONICAL_CHANNELS)
    aliases = receipt["legacy_alias_normalizations"]
    assert aliases
    assert {row["from"] for row in aliases} == {"clusterednr"}
    assert {row["to"] for row in aliases} == {"clustered_nr"}


def test_query_hash_mismatch_refuses_before_receipt(tmp_path):
    stage, paths = make_unsealed_stage(tmp_path)

    def break_query(rows):
        rows[0]["query_sha256"] = "0" * 64

    rewrite_tsv(paths["evidence"], EVIDENCE_FIELDS, break_query)
    with pytest.raises(StageHold, match="MODEB_GF2_QUERY_HASH_HOLD"):
        seal_stage(stage, max_threads=2)
    assert not paths["receipt"].exists()


def test_bound_alignment_without_named_subject_refuses_before_receipt(tmp_path):
    stage, paths = make_unsealed_stage(tmp_path)

    def remove_name(rows):
        next(row for row in rows if row["channel"] == "nr")["subject_name"] = ""

    rewrite_tsv(paths["evidence"], EVIDENCE_FIELDS, remove_name)
    with pytest.raises(StageHold, match="MODEB_GF2_BOUND_ROW_HOLD"):
        seal_stage(stage, max_threads=2)
    assert not paths["receipt"].exists()


def test_evidence_source_sha_must_match_producer_output(tmp_path):
    stage, paths = make_unsealed_stage(tmp_path)

    def break_source_binding(rows):
        rows[0]["source_sha256"] = "1" * 64

    rewrite_tsv(paths["evidence"], EVIDENCE_FIELDS, break_source_binding)
    with pytest.raises(StageHold, match="source SHA conflicts with producer output"):
        seal_stage(stage, max_threads=2)
    assert not paths["receipt"].exists()


def test_placeholder_locus_tag_refuses(tmp_path):
    stage, paths = make_unsealed_stage(tmp_path)

    def use_placeholder(rows):
        rows[0]["locus_tag"] = "_NOLOCUS"

    rewrite_tsv(paths["roster"], ROSTER_FIELDS, use_placeholder)
    with pytest.raises(StageHold, match="MODEB_GF2_GENE_ROSTER_HOLD"):
        seal_stage(stage, max_threads=2)


def test_shortened_full_node_refuses(tmp_path):
    stage, paths = make_unsealed_stage(tmp_path)
    identity = read_json(paths["identity"])
    identity["full_node"] = "NODE"
    identity["exact_identity"] = "SYNTH-001 / NODE / region002 / BGC007"
    write_json(paths["identity"], identity)

    with pytest.raises(StageHold, match="MODEB_GF2_IDENTITY_HOLD"):
        seal_stage(stage, max_threads=2)


def test_missing_required_channel_state_refuses(tmp_path):
    stage, paths = make_unsealed_stage(tmp_path)

    def remove_neighborhood(rows):
        rows[:] = [row for row in rows if row["channel"] != "neighborhood"]

    rewrite_tsv(paths["evidence"], EVIDENCE_FIELDS, remove_neighborhood)
    with pytest.raises(StageHold, match="MODEB_GF2_CHANNEL_HOLD"):
        seal_stage(stage, max_threads=2)


def test_recorded_thread_count_above_explicit_policy_refuses(tmp_path):
    stage, paths = make_unsealed_stage(tmp_path)

    def use_three_threads(rows):
        next(row for row in rows if row["channel"] == "nr")["threads_used"] = "3"

    rewrite_tsv(paths["producers"], PRODUCER_FIELDS, use_three_threads)
    with pytest.raises(StageHold, match="above policy maximum 2"):
        seal_stage(stage, max_threads=2)


def test_tampered_member_is_detected_on_reload(tmp_path):
    stage, paths, _receipt = make_sealed_stage(tmp_path)
    with paths["roster"].open("a", encoding="utf-8") as handle:
        handle.write("\n")

    with pytest.raises(StageHold, match="MODEB_GF2_STAGE_TAMPER_HOLD"):
        load_sealed_stage(stage)


def test_tampered_receipt_counts_are_detected(tmp_path):
    stage, paths, _receipt = make_sealed_stage(tmp_path)
    receipt = read_json(paths["receipt"])
    receipt["counts"]["genes"] = 99
    write_json(paths["receipt"], receipt)

    with pytest.raises(StageHold, match="receipt counts do not match"):
        load_sealed_stage(stage)


def test_unsealed_extra_member_is_refused_and_sealed_extra_is_tamper(tmp_path):
    stage, paths = make_unsealed_stage(tmp_path)
    extra = stage / "unexpected.txt"
    extra.write_text("unexpected\n", encoding="utf-8")
    with pytest.raises(StageHold, match="MODEB_GF2_STAGE_MEMBER_HOLD"):
        seal_stage(stage, max_threads=2)
    extra.unlink()
    seal_stage(stage, max_threads=2)
    extra.write_text("unexpected\n", encoding="utf-8")
    with pytest.raises(StageHold, match="MODEB_GF2_STAGE_TAMPER_HOLD"):
        load_sealed_stage(stage)


def test_second_seal_refuses_additive_output_collision(tmp_path):
    stage, _paths, _receipt = make_sealed_stage(tmp_path)
    with pytest.raises(StageHold, match="MODEB_GF2_OUTPUT_REFUSED"):
        seal_stage(stage, max_threads=2)
