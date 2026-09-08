"""Three-layer receipt locks (V4 §5 / §15 "Layer independence" — Black Cherry-4).

A can be READY while B and C are held; B can be READY while C is held; C cannot be READY
without a digest-bound manifest + explicit denominator; prefixes are never membership;
references are one-way (B cites A, C cites B; A carries no B/C fields); receipts are
immutable on disk. Synthetic stage only.
"""
from __future__ import annotations

import json

import pytest

from mamey.mode_b.gene_first_layers import (
    LayerHold,
    build_layer_c,
    build_layers,
    write_layer_receipts,
)
from mamey.mode_b.gene_first_stage_v2 import ROSTER_FIELDS, seal_stage
from tests.modeb_gene_first_v2_fixture import (
    make_unsealed_stage,
    read_json,
    refresh_producer_roster_digest,
    rewrite_tsv,
    write_json,
)

SHA = "a" * 64


def _sealed(tmp_path, *, mutate_context=None, mutate_roster=None):
    stage, paths = make_unsealed_stage(tmp_path)
    if mutate_context:
        context = read_json(paths["context"])
        mutate_context(context)
        write_json(paths["context"], context)
    if mutate_roster:
        rewrite_tsv(paths["roster"], ROSTER_FIELDS, mutate_roster)
        refresh_producer_roster_digest(paths)
    seal_stage(stage, max_threads=2, sealed_utc="2026-01-01T00:00:02+00:00")
    return stage


def _manifest(**over):
    m = {"logical_locator": "cohort/membership.tsv", "sha256": SHA,
         "members": ["SYN-001", "SYN-002", "SYN-003"], "denominator": 3,
         "schema_version_policy": "v2.1 only", "database_snapshot_policy": "nr 2026-01-01",
         "missingness_policy": "typed; non-comparable loci excluded and counted"}
    m.update(over)
    return m


def test_baseline_a_and_b_ready_c_held_without_manifest(tmp_path):
    layers = build_layers(_sealed(tmp_path))
    assert layers["A"]["readiness"] == "A_READY", layers["A"]["holds"]
    assert layers["B"]["readiness"] == "B_READY", layers["B"]["holds"]
    assert layers["C"]["readiness"] == "C_HELD"
    assert set(layers["C"]["holds"]) >= {"LAYER_C_MANIFEST_HOLD", "LAYER_C_DENOMINATOR_HOLD"}
    assert layers["C"]["outputs_emitted"] == []


def test_a_ready_while_b_held_by_boundary_ceiling(tmp_path):
    def trip(context):
        context["canonical_fragment_ceiling_state"] = "TRIPPED"
        context["canonical_fragment_ceiling_reason"] = "synthetic trip"
    layers = build_layers(_sealed(tmp_path, mutate_context=trip))
    assert layers["A"]["readiness"] == "A_READY"
    assert layers["B"]["readiness"] == "B_HELD"
    assert "LAYER_B_BOUNDARY_CEILING" in layers["B"]["holds"]


def test_b_ready_while_c_held_and_c_ready_with_bound_manifest(tmp_path):
    stage = _sealed(tmp_path)
    held = build_layers(stage)
    assert held["B"]["readiness"] == "B_READY" and held["C"]["readiness"] == "C_HELD"
    ready = build_layers(stage, _manifest())
    assert ready["C"]["readiness"] == "C_READY", ready["C"]["holds"]
    assert ready["C"]["cohort_manifest"]["denominator"] == 3


def test_prefix_is_never_membership(tmp_path):
    layers = build_layers(_sealed(tmp_path), _manifest(members=["AS-*", "AJS-*"], denominator=2))
    assert "LAYER_C_MEMBERSHIP_HOLD" in layers["C"]["holds"]
    assert layers["C"]["readiness"] == "C_HELD"


def test_denominator_must_match_member_count_and_be_explicit(tmp_path):
    stage = _sealed(tmp_path)
    assert "LAYER_C_DENOMINATOR_HOLD" in build_layers(stage, _manifest(denominator=44))["C"]["holds"]
    assert "LAYER_C_DENOMINATOR_HOLD" in build_layers(stage, _manifest(denominator=None))["C"]["holds"]


def test_unbound_manifest_holds(tmp_path):
    layers = build_layers(_sealed(tmp_path), _manifest(sha256="not-a-digest"))
    assert "LAYER_C_MANIFEST_HOLD" in layers["C"]["holds"]


def test_references_are_one_way(tmp_path):
    layers = build_layers(_sealed(tmp_path))
    a, b, c = layers["A"], layers["B"], layers["C"]
    assert b["cites"] == {"gene_evidence_receipt_id": a["gene_evidence_receipt_id"]}
    assert c["cites"] == {"locus_context_receipt_id": b["locus_context_receipt_id"]}
    assert "cites" not in a
    assert not any(k.startswith("locus_context") or k.startswith("cohort") for k in a if k != "not_required")
    assert a["not_required"]["cohort_manifest"] == "NOT_REQUIRED_FOR_LAYER_A"
    assert b["not_required"]["cohort_manifest"] == "NOT_REQUIRED_FOR_LAYER_B"


def test_layer_b_refuses_foreign_layer_a(tmp_path):
    stage = _sealed(tmp_path)
    layers = build_layers(stage)
    from mamey.mode_b.gene_first_layers import build_layer_b
    from mamey.mode_b.gene_first_stage_v2 import load_sealed_stage
    foreign_a = dict(layers["A"]); foreign_a["stage_receipt_sha256"] = "b" * 64
    with pytest.raises(LayerHold) as exc:
        build_layer_b(load_sealed_stage(stage), foreign_a)
    assert exc.value.code == "LAYER_B_CONTEXT_BINDING_HOLD"


def test_receipts_written_once_and_immutable(tmp_path):
    stage = _sealed(tmp_path)
    out = tmp_path / "out"; out.mkdir()
    result = write_layer_receipts(stage, out, now_utc=None)
    assert result["readiness"] == {"A": "A_READY", "B": "B_READY", "C": "C_HELD"}
    written = json.loads(open(result["written"]["B"]).read())
    assert written["immutable"] is True and written["figure_factory_overlay_basis_layer"] == "B"
    with pytest.raises(LayerHold) as exc:
        write_layer_receipts(stage, out)
    assert exc.value.code == "MODEB_GF2_OUTPUT_REFUSED"


def test_partial_protein_is_a_warning_not_a_layer_a_hold(tmp_path):
    def partial(rows):
        rows[0]["partial_state"] = "PARTIAL_5P"
    layers = build_layers(_sealed(tmp_path, mutate_roster=partial))
    assert layers["A"]["readiness"] == "A_READY"
    assert any(g["completeness_warning"] for g in layers["A"]["genes"])
