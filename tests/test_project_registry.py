import csv
import json

import pytest

from mamey.project_registry import (
    PrivacyHold,
    ProjectRegistry,
    ProjectRegistryError,
    load_project_registry,
    write_strain_registry_surfaces,
)


def payload():
    return {
        "schema_version": "sapote_project_registry_v1",
        "public_export_tier": "OPEN",
        "privacy_tiers": [
            {"tier_id": "OPEN", "audience_rank": 0},
            {"tier_id": "TEAM", "audience_rank": 50},
            {"tier_id": "OWNER_ONLY", "audience_rank": 100},
        ],
        "strains": [
            {
                "strain_id": "STRAIN-001",
                "privacy_tier": "TEAM",
                "publication_status": "IN_PREPARATION",
                "genome_state": "ANALYZED",
            },
            {
                "strain_id": "STRAIN-002",
                "privacy_tier": "OPEN",
                "publication_status": "PUBLISHED",
                "genome_state": "NOT_PROVIDED",
            },
        ],
        "assays": [
            {
                "assay_id": "ASSAY-CRUDE-001",
                "strain_id": "STRAIN-001",
                "privacy_tier": "TEAM",
                "material_level": "CRUDE_EXTRACT",
                "target_ids": ["TARGET-A", "TARGET-B"],
                "result_state": "OBSERVED_ACTIVITY_AT_RECORDED_CONDITIONS",
                "replicate_count": 3,
            },
            {
                "assay_id": "ASSAY-HPLC-001",
                "strain_id": "STRAIN-001",
                "privacy_tier": "OWNER_ONLY",
                "material_level": "HPLC_FRACTION",
                "parent_material_id": "EXTRACT-001",
                "target_ids": ["TARGET-C"],
                "result_state": "NOT_RETURNED",
            },
        ],
    }


def test_user_defined_tiers_do_not_depend_on_strain_prefixes():
    registry = ProjectRegistry.from_dict(payload())
    assert registry.require_strain("STRAIN-001").privacy_tier == "TEAM"
    assert registry.require_strain("STRAIN-002").privacy_tier == "OPEN"
    assert registry.legacy_release("STRAIN-002") == "PUBLIC"
    assert registry.legacy_release("STRAIN-001") == "PRIVATE"
    with pytest.raises(PrivacyHold):
        registry.require_strain("UNDECLARED-STRAIN")


def test_effective_privacy_uses_most_restrictive_linked_record():
    registry = ProjectRegistry.from_dict(payload())
    decision = registry.authorize_export(
        "STRAIN-001", "TEAM", linked_tiers=["OWNER_ONLY"]
    )
    assert decision["allowed"] is False
    assert decision["effective_privacy_tier"] == "OWNER_ONLY"
    assert registry.authorize_export(
        "STRAIN-001", "OWNER_ONLY", linked_tiers=["OWNER_ONLY"]
    )["allowed"] is True


def test_genome_and_assay_axes_are_independent_and_missing_is_not_negative():
    registry = ProjectRegistry.from_dict(payload())
    assert registry.require_strain("STRAIN-002").genome_state == "NOT_PROVIDED"
    assert registry.assay_summary("STRAIN-002")["assay_data_state"] == "NOT_PROVIDED"

    summary = registry.assay_summary("STRAIN-001")
    assert summary["assay_record_count"] == 2
    assert summary["unique_target_count"] == 3
    assert set(summary["material_levels"]) == {"CRUDE_EXTRACT", "HPLC_FRACTION"}
    assert summary["result_state_counts"]["NOT_RETURNED"] == 1
    assert "not biological inactivity" in summary["claim_guard"]


def test_snapshot_and_flat_assay_table_are_written(tmp_path):
    source = tmp_path / "registry.json"
    source.write_text(json.dumps(payload()), encoding="utf-8")
    registry = load_project_registry(source)
    receipt = write_strain_registry_surfaces(tmp_path / "package", registry, "STRAIN-001")
    assert receipt["privacy_tier"] == "OWNER_ONLY"
    assert receipt["legacy_release"] == "PRIVATE"
    snapshot = json.loads((tmp_path / "package/project_registry_snapshot.json").read_text())
    assert snapshot["privacy_contract"]["strain_privacy_tier"] == "TEAM"
    assert snapshot["privacy_contract"]["effective_package_privacy_tier"] == "OWNER_ONLY"
    with (tmp_path / "package/bioassay_scope.tsv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert len(rows) == 2
    assert rows[1]["result_state"] == "NOT_RETURNED"


def test_unknown_tier_and_untyped_result_fail_closed():
    broken = payload()
    broken["strains"][0]["privacy_tier"] = "MISSING_TIER"
    with pytest.raises(ProjectRegistryError, match="Unknown privacy tier"):
        ProjectRegistry.from_dict(broken)

    broken = payload()
    broken["assays"][0]["result_state"] = "NEGATIVE"
    with pytest.raises(ProjectRegistryError, match="result_state"):
        ProjectRegistry.from_dict(broken)
