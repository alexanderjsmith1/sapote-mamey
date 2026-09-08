from __future__ import annotations

from copy import deepcopy
import hashlib
import json

import pytest

from mamey.mode_b.gene_first_figure_overlay import (
    OverlayHold,
    build_summary_overlay,
    write_summary_overlay,
)
from mamey.mode_b.gene_first_interpret_v2 import write_authoring_outputs
from mamey.mode_b.gene_first_stage_v2 import sha256_file

from tests.modeb_gene_first_v2_fixture import IDENTITY, digest, make_sealed_stage


def decision(tmp_path, **overrides):
    stage_id = digest("stage-id")
    stage_receipt_sha256 = digest("stage-receipt")
    token = "SYNTH-001__NODE_7_length_120000_cov_42.5__region002__BGC007"
    member_names = {
        "nr_clustered_nr_disagreement": f"{token}__nr_vs_clustered_nr_disagreement.tsv",
        "important_genes": f"{token}__important_genes_v2.tsv",
        "locus_diagnostics": f"{token}__locus_diagnostics.json",
        "authoring_packet": f"{token}__authoring_packet.json",
    }
    members = []
    for role, name in member_names.items():
        path = tmp_path / name
        path.write_text(f"synthetic {role}\n", encoding="utf-8")
        members.append(
            {
                "role": role,
                "name": name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "bytes": path.stat().st_size,
            }
        )
    receipt_basis = {
        "schema_version": "modeb_gene_first_authoring_receipt_v2",
        "identity": dict(IDENTITY),
        "identity_token": token,
        "stage_id": stage_id,
        "stage_receipt_sha256": stage_receipt_sha256,
        "members": members,
    }
    receipt = {
        **receipt_basis,
        "authoring_id": hashlib.sha256(
            json.dumps(
                receipt_basis,
                sort_keys=True,
                ensure_ascii=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
        "created_utc": "2026-01-01T00:01:00+00:00",
        "authority_ceiling": "ENGINEERING_CANDIDATE_AUTHORING_SURFACE_ONLY",
        "self_excluding_receipt": True,
    }
    receipt_path = tmp_path / f"{token}__authoring_receipt.json"
    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    authoring_receipt_sha256 = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    value = {
        **IDENTITY,
        "consumer_plane": "BGC_SUMMARY",
        "action": "FLAG_SUMMARY_ONLY",
        "source_summary_class": "synthetic_source_class",
        "proposed_summary_class": "",
        "reason_codes": ["PAIRED_FAMILY_DIVERGENCE", "BOUNDARY_CONTEXT"],
        "source_summary_locator": "package://synthetic/figures/bgc_summary.tsv",
        "source_summary_sha256": digest("source-summary"),
        "stage_id": stage_id,
        "stage_receipt_sha256": stage_receipt_sha256,
        "authoring_receipt_sha256": authoring_receipt_sha256,
        "claim_ceiling": "SUMMARY_FLAG_ONLY_NOT_SCIENTIFIC_RECLASSIFICATION",
    }
    value.update(overrides)
    return value, receipt_path


def test_valid_summary_overlay_is_additive_and_does_not_mutate_input(tmp_path):
    source, receipt_path = decision(tmp_path)
    before = deepcopy(source)
    row = build_summary_overlay(source, receipt_path)

    assert source == before
    assert row["consumer_plane"] == "BGC_SUMMARY"
    assert row["source_summary_class"] == "synthetic_source_class"
    assert row["proposed_summary_class"] == ""
    assert row["overlay_effect_scope"] == "BGC_SUMMARY_ONLY"
    assert row["independent_plane_policy"].endswith("RAW_EVIDENCE_UNCHANGED")
    assert row["status"] == "OWNER_REVIEW_CANDIDATE_NOT_APPLIED"


@pytest.mark.parametrize(
    "consumer_plane",
    ["GENE", "DOMAIN", "MODULE", "CASSETTE", "NEIGHBORHOOD", "RAW_EVIDENCE"],
)
def test_independent_evidence_planes_are_refused(tmp_path, consumer_plane):
    source, receipt_path = decision(tmp_path, consumer_plane=consumer_plane)
    with pytest.raises(OverlayHold, match="MODEB_GF2_OVERLAY_CONSUMER_REFUSED"):
        build_summary_overlay(source, receipt_path)


def test_reclassification_retains_source_and_requires_distinct_candidate_class(tmp_path):
    source, receipt_path = decision(
        tmp_path,
        action="PROPOSE_SUMMARY_RECLASSIFICATION",
        proposed_summary_class="synthetic_candidate_class",
    )
    row = build_summary_overlay(
        source,
        receipt_path,
    )
    assert row["source_summary_class"] == "synthetic_source_class"
    assert row["proposed_summary_class"] == "synthetic_candidate_class"

    source, receipt_path = decision(
        tmp_path,
        action="PROPOSE_SUMMARY_RECLASSIFICATION",
        proposed_summary_class="synthetic_source_class",
    )
    with pytest.raises(OverlayHold, match="distinct proposed summary class"):
        build_summary_overlay(source, receipt_path)


def test_non_reclassification_action_cannot_smuggle_proposed_class(tmp_path):
    source, receipt_path = decision(tmp_path, proposed_summary_class="smuggled_class")
    with pytest.raises(OverlayHold, match="only a reclassification proposal"):
        build_summary_overlay(source, receipt_path)


def test_personal_source_path_is_refused(tmp_path):
    source, receipt_path = decision(
        tmp_path,
        source_summary_locator="/Users/example/private/summary.tsv",
    )
    with pytest.raises(OverlayHold, match="not portable"):
        build_summary_overlay(source, receipt_path)


def test_overlay_filename_carries_complete_identity(tmp_path):
    source, receipt_path = decision(tmp_path)
    output_root = tmp_path / "overlays"
    output_root.mkdir()
    path = write_summary_overlay(source, receipt_path, output_root)
    assert path.name == (
        "SYNTH-001__NODE_7_length_120000_cov_42.5__region002__BGC007"
        "__figure_factory_bgc_summary_overlay.tsv"
    )
    assert path.read_text(encoding="utf-8").count("\n") == 2


def test_authoring_receipt_identity_conflict_is_refused(tmp_path):
    source, receipt_path = decision(
        tmp_path,
        full_node="NODE_8_length_120000_cov_42.5",
        exact_identity="SYNTH-001 / NODE_8_length_120000_cov_42.5 / region002 / BGC007",
    )
    with pytest.raises(OverlayHold, match="authoring receipt identity conflicts"):
        build_summary_overlay(source, receipt_path)


def test_tampered_authoring_receipt_is_refused(tmp_path):
    source, receipt_path = decision(tmp_path)
    with receipt_path.open("a", encoding="utf-8") as handle:
        handle.write("\n")
    with pytest.raises(OverlayHold, match="authoring receipt SHA does not match"):
        build_summary_overlay(source, receipt_path)


def test_tampered_authoring_member_is_refused(tmp_path):
    source, receipt_path = decision(tmp_path)
    member = next(path for path in tmp_path.iterdir() if path.name.endswith("__authoring_packet.json"))
    with member.open("a", encoding="utf-8") as handle:
        handle.write("changed\n")
    with pytest.raises(OverlayHold, match="authoring member changed"):
        build_summary_overlay(source, receipt_path)


def test_actual_authoring_receipt_and_members_are_compatible(tmp_path):
    stage_root = tmp_path / "stage"
    stage_root.mkdir()
    stage, _paths, _stage_receipt = make_sealed_stage(stage_root)
    authoring_root = tmp_path / "authoring"
    authoring_root.mkdir()
    written = write_authoring_outputs(stage, authoring_root)
    authoring_receipt_path = authoring_root / stage.name / f"{stage.name}__authoring_receipt.json"
    source = {
        **IDENTITY,
        "consumer_plane": "BGC_SUMMARY",
        "action": "FLAG_SUMMARY_ONLY",
        "source_summary_class": "synthetic_source_class",
        "proposed_summary_class": "",
        "reason_codes": ["PAIRING_REVIEW"],
        "source_summary_locator": "package://synthetic/figures/bgc_summary.tsv",
        "source_summary_sha256": digest("source-summary"),
        "stage_id": written["receipt"]["stage_id"],
        "stage_receipt_sha256": written["receipt"]["stage_receipt_sha256"],
        "authoring_receipt_sha256": sha256_file(authoring_receipt_path),
        "claim_ceiling": "SUMMARY_FLAG_ONLY_NOT_SCIENTIFIC_RECLASSIFICATION",
    }

    row = build_summary_overlay(source, authoring_receipt_path)
    assert row["stage_id"] == written["receipt"]["stage_id"]
    assert row["authoring_receipt_sha256"] == sha256_file(authoring_receipt_path)
