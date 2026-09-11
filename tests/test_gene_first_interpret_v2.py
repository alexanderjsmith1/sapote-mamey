from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import pytest

from mamey.mode_b.gene_first_interpret_v2 import (
    InterpretationHold,
    build_locus_diagnostics,
    build_nr_clustered_nr_disagreement,
    interpret_stage,
    rank_important_genes,
    write_authoring_outputs,
)
from mamey.mode_b.gene_first_stage_v2 import ROSTER_FIELDS, load_sealed_stage, seal_stage

from tests.modeb_gene_first_v2_fixture import (
    refresh_producer_roster_digest,
    make_sealed_stage,
    make_unsealed_stage,
    read_json,
    rewrite_tsv,
    write_json,
)


def test_paired_disagreement_keeps_both_channels_and_names_no_winner(tmp_path):
    stage, _paths, _receipt = make_sealed_stage(tmp_path)
    rows = build_nr_clustered_nr_disagreement(load_sealed_stage(stage))
    by_tag = {row["locus_tag"]: row for row in rows}

    core = by_tag["syn_core_001"]
    assert core["pair_state"] == "PAIRED_BOUND_FAMILY_DIVERGENT"
    assert core["nr_subject_name"] == "synthetic core synthase"
    assert core["clustered_nr_subject_name"] == "synthetic alternate synthase"
    assert core["precedence_winner"] == "NONE_BY_CONTRACT"
    assert set(core["secondary_flags"].split(";")) >= {
        "COVERAGE_ASYMMETRY",
        "IDENTITY_ASYMMETRY",
        "SUBJECT_ORGANISM_DIFFERENT",
    }
    assert by_tag["syn_tailor_002"]["pair_state"] == "PAIRED_BOUND_FAMILY_CONCORDANT"
    assert by_tag["syn_reg_003"]["pair_state"] == "NR_ONLY_BOUND"


def test_boundary_assembly_protein_and_detector_axes_remain_independent(tmp_path):
    stage, paths = make_unsealed_stage(tmp_path)
    context = read_json(paths["context"])
    context.update(
        {
            "region_start": 0,
            "bgc_boundary_state": "EDGE",
            "assembly_fragmentation_tier": "HIGHLY_FRAGMENTED",
            "detector_window_state": "BOUNDARY_CONTEXT_EXTENSION",
            "canonical_fragment_ceiling_state": "TRIPPED",
            "canonical_fragment_ceiling_reason": "Synthetic ceiling trip for independent-axis QA.",
        }
    )
    write_json(paths["context"], context)

    def make_core_partial(rows):
        rows[0]["partial_state"] = "PARTIAL_5P"
        rows[0]["membership"] = "BOUNDARY_CONTEXT_ONLY"

    rewrite_tsv(paths["roster"], ROSTER_FIELDS, make_core_partial)
    # GF3-1: membership is digest-visible now; rebind producers to the edited roster
    # (the un-rebound form is pinned as a refusal in the v2.1 coordinate-hash suite).
    refresh_producer_roster_digest(paths)
    seal_stage(stage, max_threads=2, sealed_utc="2026-01-01T00:00:02+00:00")
    diagnostics = build_locus_diagnostics(load_sealed_stage(stage))

    assert diagnostics["axes"] == {
        "bgc_boundary_state": "EDGE",
        "assembly_fragmentation_tier": "HIGHLY_FRAGMENTED",
        "protein_partial_state_counts": {"COMPLETE": 2, "PARTIAL_5P": 1},
        "detector_window_state": "BOUNDARY_CONTEXT_EXTENSION",
    }
    assert set(diagnostics["diagnostic_flags"]) >= {
        "BGC_EDGE_COMPLETENESS_HOLD",
        "ASSEMBLY_FRAGMENTATION_CONTEXT",
        "PARTIAL_CORE_PROTEIN_HOLD",
        "BOUNDARY_CONTEXT_PRESENT",
        "CANONICAL_FRAGMENT_CEILING_TRIPPED",
    }
    assert "INTERNAL_INTERVAL_CONFLICT" not in diagnostics["diagnostic_flags"]


def test_review_rank_is_deterministic_transparent_and_registry_neutral(tmp_path):
    stage, _paths, _receipt = make_sealed_stage(tmp_path)
    loaded = load_sealed_stage(stage)
    disagreement = build_nr_clustered_nr_disagreement(loaded)
    first = rank_important_genes(loaded, disagreement)
    second = rank_important_genes(loaded, disagreement)

    assert first == second
    assert first[0]["locus_tag"] == "syn_core_001"
    assert "defining_biosynthetic_core=+50" in first[0]["structural_components"]
    assert "bound_domain_architecture=+15" in first[0]["structural_components"]
    assert "nr_clustered_nr_family_divergence=+30" in first[0]["uncertainty_components"]
    assert all("executed_cassette_membership" not in row["structural_components"] for row in first)
    assert all(row["score_ceiling"] == "REVIEW_ORDER_ONLY_NOT_BIOLOGICAL_IMPORTANCE" for row in first)


def test_next_analysis_prioritizes_missing_pair_for_highest_ranked_unpaired_gene(tmp_path):
    stage, _paths, _receipt = make_sealed_stage(tmp_path)
    result = interpret_stage(stage, now_utc=datetime(2026, 1, 1, 0, 1, tzinfo=timezone.utc))

    assert result.authoring_packet["highest_information_next_analysis"] == {
        "route": "COMPLETE_CLUSTERED_NR_FOR_HIGHEST_RANKED_UNPAIRED_GENE",
        "locus_tag": "syn_reg_003",
        "reason": "The paired comparison is limited by an explicit clustered_nr gap.",
    }
    assert result.authoring_packet["stage_binding"]["stage_age_seconds"] == 58.0


def test_authoring_outputs_are_small_additive_and_exact_identity_named(tmp_path):
    stage, paths, _receipt = make_sealed_stage(tmp_path)
    stage_receipt_before = hashlib.sha256(paths["receipt"].read_bytes()).hexdigest()
    output_root = tmp_path / "outputs"
    output_root.mkdir()
    result = write_authoring_outputs(
        stage,
        output_root,
        now_utc=datetime(2026, 1, 1, 0, 1, tzinfo=timezone.utc),
    )
    output_dir = output_root / stage.name

    assert output_dir.is_dir()
    assert len(list(output_dir.iterdir())) == 5
    assert all(path.name.startswith(stage.name) for path in output_dir.iterdir())
    assert sum(path.stat().st_size for path in output_dir.iterdir()) < 100_000
    assert result["receipt"]["stage_id"]
    assert hashlib.sha256(paths["receipt"].read_bytes()).hexdigest() == stage_receipt_before


def test_existing_identity_output_directory_refuses_before_new_file(tmp_path):
    stage, _paths, _receipt = make_sealed_stage(tmp_path)
    output_root = tmp_path / "outputs"
    output_root.mkdir()
    (output_root / stage.name).mkdir()

    with pytest.raises(InterpretationHold, match="MODEB_GF2_OUTPUT_REFUSED"):
        write_authoring_outputs(stage, output_root)
    assert not list((output_root / stage.name).iterdir())
