"""Regression coverage for portable public-export policy controls.

Fixtures use generic identifiers only.  They exercise staging-boundary policy,
not a real cohort, release decision, or scientific record.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "public_release_audit.py"


def _audit_module():
    spec = importlib.util.spec_from_file_location("public_release_audit_policy", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _tree(tmp_path: Path) -> Path:
    (tmp_path / "mamey").mkdir(parents=True)
    (tmp_path / "mamey" / "__init__.py").write_text('__version__ = "1.0.0"\n', encoding="utf-8")
    (tmp_path / "BUILD_STAMP.txt").write_text("build=test\n", encoding="utf-8")
    return tmp_path


def _profile(tmp_path: Path, controls: dict) -> Path:
    path = tmp_path / "operator_policy.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "schema_version": "sapote_privacy_profile_v1",
        "profile_id": "generic-policy-fixture",
        "default_tier": "INTERNAL",
        "tiers": [{"tier_id": "INTERNAL", "public_export": False}],
        "strain_assignments": [],
        "public_export_policy": controls,
    }), encoding="utf-8")
    return path


def _allowance(identifier_id: str, relative_path: str, text: str, **overrides) -> dict:
    row = {
        "identifier_id": identifier_id,
        "relative_path": relative_path,
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "reason": "synthetic regression fixture",
        "purpose": "CONTENT_ONLY_EXCEPTION",
        "state": "ACTIVE",
    }
    row.update(overrides)
    return row


def test_default_policy_detects_nested_internal_staging_root(tmp_path):
    audit = _audit_module()
    root = _tree(tmp_path)
    staged = root / "docs" / "future_improvements"
    staged.mkdir(parents=True)
    (staged / "notes.md").write_text("generic staged note\n", encoding="utf-8")

    hits = audit.audit(root)
    assert "PUBLIC_POLICY_EXCLUDED_ROOT_SHIPS: docs/future_improvements" in hits


def test_explicit_policy_fails_on_generic_private_literal_in_documentation(tmp_path):
    audit = _audit_module()
    root = _tree(tmp_path / "tree")
    (root / "docs").mkdir()
    (root / "docs" / "notes.md").write_text("PROJECT-ORCHID-EMBER\n", encoding="utf-8")
    profile = _profile(tmp_path, {
        "private_identifiers": [{"identifier_id": "project-code", "literal": "PROJECT-ORCHID-EMBER"}],
        "exclude_root_names": [], "exclude_relative_paths": [], "allowlisted_occurrences": [],
    })

    policy = audit.load_public_export_policy(profile)
    assert "PUBLIC_POLICY_PRIVATE_IDENTIFIER_IN_CONTENT: project-code: docs/notes.md" in audit.audit(root, policy)


def test_apply_policy_exclusions_removes_only_disposable_stage_roots(tmp_path):
    audit = _audit_module()
    root = _tree(tmp_path / "tree")
    staged = root / "docs" / "future_improvements"
    staged.mkdir(parents=True)
    (staged / "notes.md").write_text("generic staged note\n", encoding="utf-8")

    removed, problems = audit.apply_public_export_exclusions(root, audit.load_public_export_policy())
    assert problems == []
    assert removed == ["docs/future_improvements"]
    assert not staged.exists()
    assert audit.audit(root) == []


def test_allowlist_is_exact_path_and_byte_bound_but_never_allows_a_path_leak(tmp_path):
    audit = _audit_module()
    root = _tree(tmp_path / "tree")
    (root / "docs").mkdir()
    allowed = root / "docs" / "fixture.md"
    text = "DEMO-INTERNAL-IDENTIFIER is an explicitly source-bound test literal.\n"
    allowed.write_text(text, encoding="utf-8")
    profile = _profile(tmp_path, {
        "private_identifiers": [{"identifier_id": "fixture-only", "literal": "DEMO-INTERNAL-IDENTIFIER"}],
        "exclude_root_names": [], "exclude_relative_paths": [],
        "allowlisted_occurrences": [_allowance("fixture-only", "docs/fixture.md", text)],
    })
    policy = audit.load_public_export_policy(profile)
    assert audit.audit(root, policy) == []

    allowed.write_text(text + "changed\n", encoding="utf-8")
    assert "PUBLIC_POLICY_PRIVATE_IDENTIFIER_IN_CONTENT: fixture-only: docs/fixture.md" in audit.audit(root, policy)
    (root / "docs" / "DEMO-INTERNAL-IDENTIFIER-path.md").write_text("ordinary\n", encoding="utf-8")
    assert any("PUBLIC_POLICY_PRIVATE_IDENTIFIER_IN_PATH: fixture-only" in item for item in audit.audit(root, policy))


def test_policy_rejects_traversal_and_reports_binary_vendor_cache_surfaces(tmp_path):
    audit = _audit_module()
    root = _tree(tmp_path / "tree")
    bad = _profile(tmp_path, {"exclude_relative_paths": ["../unsafe"], "private_identifiers": [], "allowlisted_occurrences": []})
    with pytest.raises(audit.PrivacyProfileError, match="without '..'"):
        audit.load_public_export_policy(bad)

    (root / "vendor").mkdir()
    (root / "vendor" / "fixture.whl").write_bytes(b"not decoded")
    (root / ".DS_Store").write_bytes(b"cache")
    report = audit.audit_surface_report(root, audit.load_public_export_policy())
    assert report["VENDOR_BINARY_PATH_ONLY"] == 1
    assert report["CACHE_EXCLUDED_BY_BUILDER"] == 1


def test_cache_is_typed_but_not_misreported_as_shipped_documentation(tmp_path):
    audit = _audit_module()
    root = _tree(tmp_path / "tree")
    cache = root / ".pytest_cache" / "v"
    cache.mkdir(parents=True)
    (cache / "nodeids").write_text("SYNTHETIC-CACHE-ONLY-TOKEN\n", encoding="utf-8")

    # The cache is visible in the typed report and removed by the builder; its
    # contents are not a shipped documentation surface for the plain audit.
    assert audit.audit(root) == []
    assert audit.audit_surface_report(root, audit.load_public_export_policy())["CACHE_EXCLUDED_BY_BUILDER"] == 1


def test_builder_wires_explicit_stage_exclusion_and_same_profile_to_both_audits():
    script = (ROOT / "tools" / "make_public_tier.sh").read_text(encoding="utf-8")
    assert "--apply-public-export-exclusions" in script
    assert "--privacy-profile" in script
    assert "public_release_audit_stage" in script
    assert "verify_code_tier_derivation" in script
    assert "PUBLIC_POLICY_ARGS" not in script
    assert "finalize_public_archive.py" in script


def test_policy_refuses_leaf_symlink_before_deletion_and_preserves_external_bytes(tmp_path):
    audit = _audit_module()
    root = _tree(tmp_path / "stage")
    (root / "docs").mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel.txt"
    sentinel.write_text("external sentinel\n", encoding="utf-8")
    before = hashlib.sha256(sentinel.read_bytes()).hexdigest()
    os.symlink(outside, root / "docs" / "future_improvements", target_is_directory=True)

    removed, problems = audit.apply_public_export_exclusions(root, audit.load_public_export_policy())

    assert removed == []
    assert problems == ["PUBLIC_POLICY_EXCLUSION_SYMLINK: docs/future_improvements"]
    assert sentinel.exists()
    assert hashlib.sha256(sentinel.read_bytes()).hexdigest() == before
    assert (root / "docs" / "future_improvements").is_symlink()


def test_policy_refuses_symlinked_ancestor_before_deletion_and_preserves_external_bytes(tmp_path):
    audit = _audit_module()
    root = _tree(tmp_path / "stage")
    outside = tmp_path / "outside"
    secret = outside / "secret"
    secret.mkdir(parents=True)
    sentinel = secret / "sentinel.txt"
    sentinel.write_text("outside must remain\n", encoding="utf-8")
    before = hashlib.sha256(sentinel.read_bytes()).hexdigest()
    os.symlink(outside, root / "link", target_is_directory=True)
    profile = _profile(tmp_path, {
        "exclude_root_names": [], "exclude_relative_paths": ["link/secret"],
        "private_identifiers": [], "allowlisted_occurrences": [],
    })

    removed, problems = audit.apply_public_export_exclusions(root, audit.load_public_export_policy(profile))

    assert removed == []
    assert problems == ["PUBLIC_POLICY_EXCLUSION_SYMLINK: link"]
    assert secret.is_dir() and sentinel.exists()
    assert hashlib.sha256(sentinel.read_bytes()).hexdigest() == before


def test_preflight_refuses_resolved_target_outside_stage_and_stage_root_equality(tmp_path):
    audit = _audit_module()
    root = _tree(tmp_path / "stage")
    outside = tmp_path / "outside"
    outside.mkdir()
    stage_root, root_problems = audit._resolved_stage_root(root)
    assert root_problems == []
    assert stage_root is not None

    checked, problem = audit._validated_exclusion_target(stage_root, outside)
    assert checked is None
    assert problem == f"PUBLIC_POLICY_EXCLUSION_OUTSIDE_STAGE: {outside}"
    checked, problem = audit._validated_exclusion_target(stage_root, stage_root)
    assert checked is None
    assert problem == "PUBLIC_POLICY_EXCLUSION_STAGE_ROOT_EQUALITY"


def test_explicit_missing_or_nondirectory_exclusion_refuses_without_stage_mutation(tmp_path):
    audit = _audit_module()
    root = _tree(tmp_path / "stage")
    (root / "docs").mkdir()
    protected = root / "docs" / "keep.md"
    protected.write_text("keep bytes\n", encoding="utf-8")
    before = hashlib.sha256(protected.read_bytes()).hexdigest()
    missing_profile = _profile(tmp_path / "missing", {
        "exclude_root_names": [], "exclude_relative_paths": ["docs/missing"],
        "private_identifiers": [], "allowlisted_occurrences": [],
    })
    removed, problems = audit.apply_public_export_exclusions(root, audit.load_public_export_policy(missing_profile))
    assert removed == []
    assert problems == ["PUBLIC_POLICY_EXCLUSION_MISSING: docs/missing"]
    assert hashlib.sha256(protected.read_bytes()).hexdigest() == before

    file_profile = _profile(tmp_path / "file", {
        "exclude_root_names": [], "exclude_relative_paths": ["docs/keep.md"],
        "private_identifiers": [], "allowlisted_occurrences": [],
    })
    removed, problems = audit.apply_public_export_exclusions(root, audit.load_public_export_policy(file_profile))
    assert removed == []
    assert problems == ["PUBLIC_POLICY_EXCLUSION_NOT_DIRECTORY: docs/keep.md"]
    assert hashlib.sha256(protected.read_bytes()).hexdigest() == before


def test_repaired_ordinary_nested_root_and_generic_literal_fixture_close_together(tmp_path):
    audit = _audit_module()
    root = _tree(tmp_path / "stage")
    staged = root / "docs" / "future_improvements"
    staged.mkdir(parents=True)
    (staged / "internal.md").write_text("PROJECT-ORCHID-EMBER\n", encoding="utf-8")
    profile = _profile(tmp_path, {
        "exclude_root_names": [], "exclude_relative_paths": [],
        "private_identifiers": [{"identifier_id": "project-code", "literal": "PROJECT-ORCHID-EMBER"}],
        "allowlisted_occurrences": [],
    })
    policy = audit.load_public_export_policy(profile)
    assert any("PUBLIC_POLICY_EXCLUDED_ROOT_SHIPS" in hit for hit in audit.audit(root, policy))
    removed, problems = audit.apply_public_export_exclusions(root, policy)
    assert problems == []
    assert removed == ["docs/future_improvements"]
    assert audit.audit(root, policy) == []


@pytest.mark.parametrize("state", ["REVOKED", "INACTIVE", "UNKNOWN", "active", ""])
def test_allowance_state_must_be_exact_active(tmp_path, state):
    audit = _audit_module()
    text = "DEMO-PRIVATE-ALLOWANCE-TOKEN\n"
    controls = {
        "exclude_root_names": [], "exclude_relative_paths": [],
        "private_identifiers": [{"identifier_id": "demo", "literal": "DEMO-PRIVATE-ALLOWANCE-TOKEN"}],
        "allowlisted_occurrences": [_allowance("demo", "docs/fixture.md", text, state=state)],
    }
    with pytest.raises(audit.PrivacyProfileError, match="state must be ACTIVE|requires non-empty"):
        audit.load_public_export_policy(_profile(tmp_path, controls))


@pytest.mark.parametrize("purpose", ["TEST_FIXTURE", "CONTENT_EXCEPTION", "UNKNOWN", ""])
def test_allowance_purpose_must_be_exact_content_only_exception(tmp_path, purpose):
    audit = _audit_module()
    text = "DEMO-PRIVATE-ALLOWANCE-TOKEN\n"
    controls = {
        "exclude_root_names": [], "exclude_relative_paths": [],
        "private_identifiers": [{"identifier_id": "demo", "literal": "DEMO-PRIVATE-ALLOWANCE-TOKEN"}],
        "allowlisted_occurrences": [_allowance("demo", "docs/fixture.md", text, purpose=purpose)],
    }
    with pytest.raises(audit.PrivacyProfileError, match="purpose must be CONTENT_ONLY_EXCEPTION|requires non-empty"):
        audit.load_public_export_policy(_profile(tmp_path, controls))


def test_allowance_missing_unknown_and_duplicate_fields_fail_closed(tmp_path):
    audit = _audit_module()
    text = "DEMO-PRIVATE-ALLOWANCE-TOKEN\n"
    base = {
        "exclude_root_names": [], "exclude_relative_paths": [],
        "private_identifiers": [{"identifier_id": "demo", "literal": "DEMO-PRIVATE-ALLOWANCE-TOKEN"}],
    }
    missing = _allowance("demo", "docs/fixture.md", text)
    missing.pop("purpose")
    with pytest.raises(audit.PrivacyProfileError, match="missing purpose"):
        audit.load_public_export_policy(_profile(tmp_path / "missing", {**base, "allowlisted_occurrences": [missing]}))
    unknown = _allowance("demo", "docs/fixture.md", text, unexpected="ignored-before-repair")
    with pytest.raises(audit.PrivacyProfileError, match="unknown unexpected"):
        audit.load_public_export_policy(_profile(tmp_path / "unknown", {**base, "allowlisted_occurrences": [unknown]}))
    duplicate = _allowance("demo", "docs/fixture.md", text)
    with pytest.raises(audit.PrivacyProfileError, match="duplicate public_export_policy allowlisted occurrence"):
        audit.load_public_export_policy(_profile(tmp_path / "duplicate", {**base, "allowlisted_occurrences": [duplicate, duplicate]}))


def test_duplicate_json_purpose_key_is_not_silently_overwritten(tmp_path):
    audit = _audit_module()
    raw = """{
      "schema_version": "sapote_privacy_profile_v1",
      "profile_id": "generic-fixture",
      "default_tier": "INTERNAL",
      "tiers": [{"tier_id": "INTERNAL", "public_export": false}],
      "strain_assignments": [],
      "public_export_policy": {
        "exclude_root_names": [], "exclude_relative_paths": [],
        "private_identifiers": [{"identifier_id": "demo", "literal": "DEMO-PRIVATE-ALLOWANCE-TOKEN"}],
        "allowlisted_occurrences": [{
          "identifier_id": "demo", "relative_path": "docs/fixture.md",
          "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
          "reason": "synthetic", "purpose": "CONTENT_ONLY_EXCEPTION",
          "purpose": "TEST_FIXTURE", "state": "ACTIVE"
        }]
      }
    }"""
    profile = tmp_path / "duplicate_key.json"
    profile.write_text(raw, encoding="utf-8")
    with pytest.raises(audit.PrivacyProfileError, match="duplicate object key: purpose"):
        audit.load_public_export_policy(profile)


def test_portable_relative_path_rejects_backslash_and_nul(tmp_path):
    audit = _audit_module()
    base = {"exclude_root_names": [], "private_identifiers": [], "allowlisted_occurrences": []}
    with pytest.raises(audit.PrivacyProfileError, match="portable POSIX separators"):
        audit.load_public_export_policy(_profile(tmp_path / "backslash", {
            **base, "exclude_relative_paths": ["docs\\hold"],
        }))
    with pytest.raises(audit.PrivacyProfileError, match="portable POSIX separators"):
        audit.load_public_export_policy(_profile(tmp_path / "nul", {
            **base, "exclude_relative_paths": ["docs/\x00hold"],
        }))


def test_allowance_requires_exact_regular_staged_file_and_refuses_directory_or_symlink(tmp_path):
    audit = _audit_module()
    root = _tree(tmp_path / "stage")
    (root / "docs" / "fixture.md").mkdir(parents=True)
    text = "DEMO-PRIVATE-ALLOWANCE-TOKEN\n"
    profile = _profile(tmp_path / "directory", {
        "exclude_root_names": [], "exclude_relative_paths": [],
        "private_identifiers": [{"identifier_id": "demo", "literal": "DEMO-PRIVATE-ALLOWANCE-TOKEN"}],
        "allowlisted_occurrences": [_allowance("demo", "docs/fixture.md", text)],
    })
    assert "PUBLIC_POLICY_ALLOWANCE_NOT_REGULAR_FILE: docs/fixture.md" in audit.audit(
        root, audit.load_public_export_policy(profile)
    )

    outside = tmp_path / "outside.md"
    outside.write_text(text, encoding="utf-8")
    (root / "docs" / "fixture.md").rmdir()
    os.symlink(outside, root / "docs" / "fixture.md")
    assert "PUBLIC_POLICY_ALLOWANCE_SYMLINK: docs/fixture.md" in audit.audit(
        root, audit.load_public_export_policy(profile)
    )
