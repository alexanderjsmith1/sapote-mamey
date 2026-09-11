"""GF3-1 coordinate-hash sensitivity and schema v2.1 locks (V4 §4 — Black Cherry-4).

The v2 roster digest hashed only gene_order/locus_tag/protein_sha256, so an unchanged
protein reassigned different physical coordinates, strand, or roster membership after a
boundary or source change produced the SAME content identity — silent stale-stage reuse.
Schema v2.1 makes the digest coordinate-sensitive and refuses cross-schema loads.

Engineering staging plumbing only; no scientific claim; judgment deferred.
"""
from __future__ import annotations

import json

import pytest

from mamey.mode_b.gene_first_stage_v2 import (
    ROSTER_FIELDS,
    SCHEMA_VERSION,
    StageHold,
    load_sealed_stage,
    query_roster_sha256,
    seal_stage,
)
from tests.modeb_gene_first_v2_fixture import (
    IDENTITY,
    make_unsealed_stage,
    read_json,
    read_tsv,
    refresh_producer_roster_digest,
    rewrite_tsv,
    write_json,
)


def _digest_after(tmp_path, mutate):
    tmp_path.mkdir(parents=True, exist_ok=True)
    stage, paths = make_unsealed_stage(tmp_path)
    rows = read_tsv(paths["roster"])
    mutate(rows)
    return query_roster_sha256(IDENTITY, rows)


def _base_digest(tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    stage, paths = make_unsealed_stage(tmp_path)
    return query_roster_sha256(IDENTITY, read_tsv(paths["roster"]))


def test_schema_version_is_v2_1():
    assert SCHEMA_VERSION == "modeb_gene_first_stage_v2.1"


# --- digest sensitivity: V4 §4 "a one-base coordinate change with an unchanged protein
# --- must change the roster digest" -------------------------------------------------------

@pytest.mark.parametrize("field,change", [
    ("cds_start", lambda v: str(int(v) + 1)),
    ("cds_end", lambda v: str(int(v) + 1)),
    ("strand", lambda v: "-" if v == "+" else "+"),
    ("membership", lambda v: "BOUNDARY_CONTEXT_ONLY" if v == "EXACT_REGION" else "EXACT_REGION"),
])
def test_physical_change_with_unchanged_protein_changes_digest(tmp_path, field, change):
    base = _base_digest(tmp_path / "a")

    def mutate(rows):
        rows[0][field] = change(rows[0][field])

    assert _digest_after(tmp_path / "b", mutate) != base, (
        f"roster digest is blind to {field} — v2 stale-reuse defect resurfaced"
    )


def test_digest_stable_when_nothing_changes(tmp_path):
    assert _base_digest(tmp_path / "a") == _base_digest(tmp_path / "b")


# --- stale-stage reuse refusal ------------------------------------------------------------

def test_coordinate_edit_without_producer_rebind_refuses_seal(tmp_path):
    """Producer receipts bound to the pre-edit roster digest must refuse the seal —
    the exact stale-stage reuse V4 §4 prohibits."""
    stage, paths = make_unsealed_stage(tmp_path)

    def shift_start(rows):
        rows[0]["cds_start"] = str(int(rows[0]["cds_start"]) + 1)

    rewrite_tsv(paths["roster"], ROSTER_FIELDS, shift_start)
    with pytest.raises(StageHold) as exc:
        seal_stage(stage, max_threads=2, sealed_utc="2026-01-01T00:00:02+00:00")
    assert exc.value.code == "MODEB_GF2_PRODUCER_HOLD"


def test_coordinate_edit_with_producer_rebind_seals_and_reloads(tmp_path):
    """The legitimate path: rebind producers to the new digest (a real rerun), reseal,
    reload — and the sealed receipt records the new digest under schema v2.1."""
    stage, paths = make_unsealed_stage(tmp_path)

    def shift_start(rows):
        rows[0]["cds_start"] = str(int(rows[0]["cds_start"]) + 1)

    rewrite_tsv(paths["roster"], ROSTER_FIELDS, shift_start)
    new_digest = refresh_producer_roster_digest(paths)
    seal_stage(stage, max_threads=2, sealed_utc="2026-01-01T00:00:02+00:00")
    loaded = load_sealed_stage(stage)
    assert loaded.query_roster_sha256 == new_digest
    assert loaded.stage_receipt["schema_version"] == "modeb_gene_first_stage_v2.1"


# --- cross-schema refusal: v2 and v2.1 receipts are never silently mixed ------------------

def test_v2_receipt_refuses_load_with_schema_hold_not_tamper(tmp_path):
    stage, paths = make_unsealed_stage(tmp_path)
    seal_stage(stage, max_threads=2, sealed_utc="2026-01-01T00:00:02+00:00")
    receipt_path = paths["receipt"]
    receipt = read_json(receipt_path)
    receipt["schema_version"] = "modeb_gene_first_stage_v2"
    write_json(receipt_path, receipt)
    with pytest.raises(StageHold) as exc:
        load_sealed_stage(stage)
    assert exc.value.code == "MODEB_GF2_STAGE_MEMBER_HOLD"
    assert "never mixed" in exc.value.detail
