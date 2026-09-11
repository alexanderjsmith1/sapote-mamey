from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from mamey import bioassay_figure_factory as factory


def _row(**updates):
    row = dict.fromkeys(factory.FIELDS, "")
    row.update({
        "observation_id": "obs-1", "strain_id": "SYN-1", "experiment_id": "exp-1",
        "assay_plate_id": "plate-1", "plate_format": "384", "well": "A01",
        "material_id": "fraction-1", "material_type": "FLASH_FRACTION",
        "parent_material_id": "extract-1", "lineage_state": "VERIFIED",
        "material_amount_mg": "12.5", "dose_state": "VERIFIED",
        "stock_concentration_mg_ml": "10", "delivered_amount_ug": "12",
        "final_concentration_ug_ml": "120",
        "target_raw": "Candida species", "target_state": "AMBIGUOUS",
        "target_canonical": "", "timepoint_hours": "48", "replicate_id": "rep-1",
        "replicate_type": "SINGLETON", "inhibition_pct": "73.2", "control_state": "VALID",
        "inclusion_state": "INCLUDE", "exclusion_reason": "", "source_locator": "plates/plate-1.csv",
    })
    row.update(updates)
    return row


def _write(path: Path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=factory.FIELDS)
        writer.writeheader(); writer.writerows(rows)


def test_summary_preserves_material_target_timepoint_and_replication():
    rows = factory.validate_rows([
        _row(),
        _row(observation_id="obs-2", replicate_id="rep-2", replicate_type="TECHNICAL",
             inhibition_pct="53.2"),
    ])
    summary = factory.summarize(rows)
    assert len(summary) == 1
    assert summary[0]["target_state"] == "AMBIGUOUS"
    assert summary[0]["material_type"] == "FLASH_FRACTION"
    assert summary[0]["timepoint_hours"] == "48"
    assert summary[0]["final_concentration_ug_ml"] == "120"
    assert summary[0]["observation_count"] == 2
    assert summary[0]["replicate_count"] == 2
    assert summary[0]["mean_inhibition_pct"] == 63.2


@pytest.mark.parametrize("updates,code", [
    ({"plate_format": "96", "well": "P24"}, "BIOASSAY_WELL_HOLD"),
    ({"control_state": "POSITIVE_CONTROL_MISSING"}, "BIOASSAY_CONTROL_HOLD"),
    ({"target_state": "AMBIGUOUS", "target_canonical": "Candida albicans"}, "BIOASSAY_TARGET_HOLD"),
    ({"lineage_state": "VERIFIED", "parent_material_id": ""}, "BIOASSAY_LINEAGE_HOLD"),
    ({"dose_state": "VERIFIED", "final_concentration_ug_ml": ""}, "BIOASSAY_DOSE_HOLD"),
])
def test_invalid_or_overresolved_observation_is_refused(updates, code):
    with pytest.raises(factory.BioassayFigureHold, match=code):
        factory.validate_rows([_row(**updates)])


def test_held_control_failure_is_retained_but_not_summarized():
    held = _row(control_state="EXPECTED_OD_NORMALIZATION_HOLD", inclusion_state="HOLD",
                exclusion_reason="positive control absent; expected-OD normalization not admitted")
    rows = factory.validate_rows([held])
    with pytest.raises(factory.BioassayFigureHold, match="BIOASSAY_NO_INCLUDED_ROWS_HOLD"):
        factory.summarize(rows)


def test_summary_never_averages_different_final_concentrations():
    summary = factory.summarize(factory.validate_rows([
        _row(),
        _row(observation_id="obs-2", final_concentration_ug_ml="60", inhibition_pct="30"),
    ]))
    assert len(summary) == 2
    assert {row["final_concentration_ug_ml"] for row in summary} == {"60", "120"}


def test_hash_bound_factory_emits_data_without_collapsing_held_rows(tmp_path):
    source = tmp_path / "observations.csv"
    _write(source, [
        _row(),
        _row(observation_id="obs-2", inclusion_state="HOLD",
             control_state="POSITIVE_CONTROL_LOCATION_UNRESOLVED",
             exclusion_reason="positive-control location unresolved"),
    ])
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    config = tmp_path / "config.json"
    config.write_text(json.dumps({
        "schema_version": factory.SCHEMA, "figure_kind": factory.FIGURE_KIND,
        "external_data_root": str(tmp_path),
        "observations": {"logical_locator": source.name, "sha256": digest},
        "output_dir": "out", "render_with_r": False,
    }), encoding="utf-8")
    receipt = factory.build(config)
    assert receipt["status"] == "PASS_DATA_READY_R_NOT_REQUESTED"
    caption = json.loads((tmp_path / "out" / "bioassay_caption_methods.json").read_text())
    assert caption["included_observations"] == 1
    assert caption["held_observations"] == 1
    assert caption["tree_overlay_state"] == "REQUIRES_EXPLICIT_MATERIAL_TARGET_TIMEPOINT_SELECTION"
    clean = (tmp_path / "out" / "bioassay_observations_admitted.tsv").read_text()
    assert "POSITIVE_CONTROL_LOCATION_UNRESOLVED" in clean


def test_cli_dispatches_bioassay_kind_through_existing_factory_command(tmp_path, capsys):
    from types import SimpleNamespace
    from mamey.cli import figure_factory_command

    source = tmp_path / "observations.csv"
    _write(source, [_row()])
    config = tmp_path / "config.json"
    config.write_text(json.dumps({
        "schema_version": factory.SCHEMA, "figure_kind": factory.FIGURE_KIND,
        "external_data_root": str(tmp_path),
        "observations": {"logical_locator": source.name,
                         "sha256": hashlib.sha256(source.read_bytes()).hexdigest()},
        "output_dir": "cli-out", "render_with_r": False,
    }), encoding="utf-8")
    assert figure_factory_command(SimpleNamespace(config=str(config))) == 0
    assert "PASS_DATA_READY_R_NOT_REQUESTED" in capsys.readouterr().out


def test_r_template_does_not_print_internal_claim_disclosures_on_canvas():
    text = (Path(__file__).resolve().parents[1] / "tools" / "sapote_bioassay_figure.R").read_text()
    assert "ggsave" in text and ".svg" in text and ".png" in text
    assert "judgment deferred" not in text.lower()
    assert "capacity is not production" not in text.lower()


def test_tree_track_requires_exact_per_strain_material_selection():
    rows = factory.validate_rows([
        _row(target_state="VERIFIED", target_raw="Candida auris",
             target_canonical="Candida auris"),
    ])
    summary = factory.summarize(rows)
    track = factory.build_tree_track(summary, {
        "selection_id": "candida_auris_48h_flash",
        "target": "Candida auris", "target_state": "VERIFIED", "timepoint_hours": 48,
        "final_concentration_ug_ml": 120,
        "material_type": "FLASH_FRACTION", "aggregation": "mean_inhibition_pct",
        "strain_roster": ["SYN-1", "SYN-2"],
        "material_ids_by_strain": {"SYN-1": "fraction-1", "SYN-2": "fraction-9"},
    })
    assert track == [
        {"strain": "SYN-1", "channel": "BIOASSAY", "feature": "candida_auris_48h_flash",
         "value": 73.2, "state": "OBSERVED"},
        {"strain": "SYN-2", "channel": "BIOASSAY", "feature": "candida_auris_48h_flash",
         "value": "", "state": "NOT_MEASURED"},
    ]


def test_tree_track_refuses_partial_material_map():
    summary = factory.summarize(factory.validate_rows([_row()]))
    with pytest.raises(factory.BioassayFigureHold, match="bind every roster strain exactly"):
        factory.build_tree_track(summary, {
            "selection_id": "one_track", "target": "Candida species",
            "target_state": "AMBIGUOUS", "timepoint_hours": 48,
            "final_concentration_ug_ml": 120,
            "material_type": "FLASH_FRACTION", "strain_roster": ["SYN-1", "SYN-2"],
            "material_ids_by_strain": {"SYN-1": "fraction-1"},
        })


def test_fraction_set_max_is_explicit_and_preserves_breadth_and_amount():
    rows = factory.validate_rows([
        _row(material_id="fraction-1", material_amount_mg="12.5", inhibition_pct="72"),
        _row(observation_id="obs-2", material_id="fraction-2", material_amount_mg="8.0",
             inhibition_pct="41"),
        _row(observation_id="obs-3", material_id="fraction-3", material_amount_mg="3.0",
             inhibition_pct="5"),
    ])
    track, details = factory._select_tree_track(factory.summarize(rows), {
        "selection_id": "fraction_set_max_48h_120ugml", "target": "Candida species",
        "target_state": "AMBIGUOUS", "timepoint_hours": 48,
        "final_concentration_ug_ml": 120, "material_type": "FLASH_FRACTION",
        "aggregation": "fraction_set_max", "active_threshold_pct": 20,
        "strain_roster": ["SYN-1"],
        "material_ids_by_strain": {"SYN-1": ["fraction-1", "fraction-2", "fraction-3"]},
    })
    assert track[0]["value"] == 72.0
    assert details[0]["selected_material_id"] == "fraction-1"
    assert details[0]["active_material_count"] == 2
    assert details[0]["total_recorded_material_amount_mg"] == 23.5


def test_fraction_set_max_refuses_partially_observed_named_set():
    summary = factory.summarize(factory.validate_rows([_row(material_id="fraction-1")]))
    with pytest.raises(factory.BioassayFigureHold, match="incomplete named fraction set"):
        factory.build_tree_track(summary, {
            "selection_id": "incomplete_set", "target": "Candida species",
            "target_state": "AMBIGUOUS", "timepoint_hours": 48,
            "final_concentration_ug_ml": 120, "material_type": "FLASH_FRACTION",
            "aggregation": "fraction_set_max", "active_threshold_pct": 20,
            "strain_roster": ["SYN-1"],
            "material_ids_by_strain": {"SYN-1": ["fraction-1", "fraction-2"]},
        })


def test_project_plan_cleans_staging_directory_after_write_failure(tmp_path, monkeypatch):
    source = tmp_path / "raw.csv"; source.write_text("raw\n1\n")
    config = tmp_path / "plan.json"
    config.write_text(json.dumps({
        "schema_version": factory.PLAN_SCHEMA, "figure_kind": factory.PLAN_KIND,
        "external_data_root": str(tmp_path), "output_dir": "plan-out",
        "datasets": [{
            "dataset_id": "raw", "data_state": "RAW_OD", "plate_format": "384",
            "material_scope": "MIXED", "logical_locator": source.name,
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        }],
    }))
    original = factory.json.dumps
    calls = 0

    def fail_first_dump(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("synthetic write preparation failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(factory.json, "dumps", fail_first_dump)
    with pytest.raises(OSError, match="synthetic"):
        factory.build_plan(config)
    assert not list(tmp_path.glob(".bioassay_project_plan.*"))


def test_project_plan_distinguishes_raw_precomputed_discovery_and_mic_inputs(tmp_path):
    raw = tmp_path / "raw384.csv"; raw.write_text("raw\n1\n")
    pre = tmp_path / "precomputed96.csv"; pre.write_text("inhibition\n42\n")
    config = tmp_path / "plan.json"
    config.write_text(json.dumps({
        "schema_version": factory.PLAN_SCHEMA, "figure_kind": factory.PLAN_KIND,
        "external_data_root": str(tmp_path), "output_dir": "plan-out",
        "project_label": "Synthetic fraction screen",
        "datasets": [
            {"dataset_id": "raw-384", "data_state": "RAW_OD", "plate_format": "384",
             "material_scope": "FLASH_FRACTION", "targets": ["Candida auris", "MRSA"],
             "timepoints_hours": [24, 48], "final_concentrations_ug_ml": [15, 30, 60, 120],
             "replication": "MIXED", "controls": "REQUIRES_MAPPING",
             "material_amounts_available": True, "logical_locator": raw.name,
             "sha256": hashlib.sha256(raw.read_bytes()).hexdigest()},
            {"dataset_id": "pre-96", "data_state": "PRECOMPUTED_PERCENT_INHIBITION",
             "plate_format": "96", "material_scope": "CRUDE_EXTRACT", "targets": ["MRSA"],
             "timepoints_hours": [24], "final_concentrations_ug_ml": [80],
             "replication": "SINGLETON", "controls": "USER_PRECOMPUTED",
             "logical_locator": pre.name,
             "sha256": hashlib.sha256(pre.read_bytes()).hexdigest()},
        ],
    }))
    receipt = factory.build_plan(config)
    assert receipt["status"] == "PASS_REVIEW_REQUIRED"
    plan = json.loads((tmp_path / "plan-out" / "bioassay_project_plan.json").read_text())
    assert "control_and_normalization_QC_before_activity_figures" in plan["proposed_previews"]
    assert "explicit_fraction_set_max_overview" in plan["proposed_previews"]
    assert "dose_response_preview" in plan["proposed_previews"]
    assert "Inferential statistics require" in plan["statistics_gate"]
