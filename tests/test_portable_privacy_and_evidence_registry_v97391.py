import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mamey.evidence_registry import EvidenceRegistryError, validate_evidence_registry
from mamey.privacy_profile import PrivacyProfileError, load_privacy_profile, resolve_profile_privacy


def _profile(tmp_path, *, default="INTERNAL", assignments=None):
    path = tmp_path / "privacy.json"
    path.write_text(json.dumps({
        "schema_version": "sapote_privacy_profile_v1",
        "profile_id": "generic-project",
        "default_tier": default,
        "tiers": [
            {"tier_id": "INTERNAL", "public_export": False},
            {"tier_id": "REVIEW", "public_export": False},
            {"tier_id": "SHARE", "public_export": True},
        ],
        "strain_assignments": assignments or [],
    }), encoding="utf-8")
    return path


def _registry(tmp_path):
    path = tmp_path / "evidence.tsv"
    path.write_text(
        "record_id\tstrain_id\tmaterial_id\tparent_material_id\tpreparation_event_id\tevidence_type\tmaterial_level\tassay_state\tpanel_id\ttarget_id\treplicate_state\tprivacy_tier\tsource_locator\tclaim_ceiling\n"
        "g-1\tisolate-001\tgenome-001\tROOT\tassembly-001\tgenome\tgenome\tNOT_SCREENED\tNOT_APPLICABLE\tNOT_APPLICABLE\tNOT_APPLICABLE\tINTERNAL\tinput.zip\tavailability only\n"
        "m-1\tisolate-002\textract-001\tROOT\textract-001\tmaterial\tcrude_extract\tNOT_SCREENED\tNOT_APPLICABLE\tNOT_APPLICABLE\tNOT_APPLICABLE\tREVIEW\textract.tsv\tmaterial lineage only\n"
        "a-1\tisolate-002\textract-001\tROOT\textract-001\tassay\tcrude_extract\tRESULTS_BOUND\tpanel-small\tpathogen-a\tSINGLETON\tREVIEW\tassay.tsv\tscreening only\n"
        "m-2\tisolate-002\tflash-001\textract-001\tflash-001\tmaterial\tflash_fraction\tNOT_SCREENED\tNOT_APPLICABLE\tNOT_APPLICABLE\tNOT_APPLICABLE\tREVIEW\tflash.tsv\tfraction lineage only\n"
        "a-2\tisolate-002\tflash-001\textract-001\tflash-001\tassay\tflash_fraction\tSCREENED\tpanel-large\tpathogen-b\tSINGLETON\tREVIEW\tflash-assay.tsv\tno causal link\n",
        encoding="utf-8",
    )
    return path


def test_profile_uses_exact_assignment_and_private_default(tmp_path):
    profile = load_privacy_profile(_profile(tmp_path, assignments=[{"strain_id": "isolate-003", "tier_id": "SHARE"}]))
    assert resolve_profile_privacy("isolate-003", profile).release == "PUBLIC"
    unknown = resolve_profile_privacy("new-isolate", profile)
    assert (unknown.tier_id, unknown.release, unknown.assignment_state) == ("INTERNAL", "PRIVATE", "DEFAULT")
    refused = resolve_profile_privacy("new-isolate", profile, override="PUBLIC")
    assert refused.release == "PRIVATE"
    assert refused.reason == "public_override_refused_by_profile"


def test_profile_rejects_public_default_and_duplicate_assignment(tmp_path):
    with pytest.raises(PrivacyProfileError, match="default_tier must be non-public"):
        load_privacy_profile(_profile(tmp_path, default="SHARE"))
    with pytest.raises(PrivacyProfileError, match="duplicate exact strain assignment"):
        load_privacy_profile(_profile(tmp_path, assignments=[
            {"strain_id": "isolate-001", "tier_id": "INTERNAL"},
            {"strain_id": "isolate-001", "tier_id": "REVIEW"},
        ]))


def test_evidence_registry_preserves_heterogeneous_material_levels(tmp_path):
    result = validate_evidence_registry(_registry(tmp_path))
    assert result["status"] == "PASS"
    assert result["record_count"] == 5
    assert result["material_count"] == 2
    assert result["assay_record_count"] == 2
    assert result["by_strain"]["isolate-002"] == {"assay": 2, "material": 2}
    assert "do not establish activity" in result["claim_ceiling"]


def test_evidence_registry_rejects_duplicate_record_ids(tmp_path):
    path = _registry(tmp_path)
    path.write_text(path.read_text(encoding="utf-8").replace("a-2\tisolate-002", "a-1\tisolate-002"), encoding="utf-8")
    with pytest.raises(EvidenceRegistryError, match="duplicate record_id"):
        validate_evidence_registry(path)


def test_portable_validator_runs_against_generic_fixture(tmp_path):
    profile = _profile(tmp_path, assignments=[
        {"strain_id": "isolate-002", "tier_id": "REVIEW"},
        {"strain_id": "isolate-003", "tier_id": "SHARE"},
    ])
    registry = _registry(tmp_path)
    result = subprocess.run([
        sys.executable, str(ROOT / "tools" / "validate_portfolio_registry.py"),
        "--privacy-profile", str(profile), "--evidence-registry", str(registry),
    ], check=False, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["evidence"]["record_count"] == 5


def test_evidence_registry_rejects_fraction_without_parent_or_profile_drift(tmp_path):
    profile = load_privacy_profile(_profile(tmp_path, assignments=[{"strain_id": "isolate-002", "tier_id": "INTERNAL"}]))
    path = _registry(tmp_path)
    with pytest.raises(EvidenceRegistryError, match="privacy_tier"):
        validate_evidence_registry(path, profile=profile)
    profile = load_privacy_profile(_profile(tmp_path, assignments=[
        {"strain_id": "isolate-001", "tier_id": "INTERNAL"},
        {"strain_id": "isolate-002", "tier_id": "REVIEW"},
    ]))
    path.write_text(path.read_text(encoding="utf-8").replace("flash-001\textract-001\tflash-001\tmaterial", "flash-001\tROOT\tflash-001\tmaterial"), encoding="utf-8")
    with pytest.raises(EvidenceRegistryError, match="fraction requires"):
        validate_evidence_registry(path, profile=profile)
