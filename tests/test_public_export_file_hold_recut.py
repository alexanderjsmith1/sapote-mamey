"""Authored prior-omission re-cut controls; no empirical held file is used."""
from dataclasses import replace
import json
import os
from pathlib import Path
import shutil
import sys

import pytest
from tests.test_public_export_file_holds_m5 import fixture, held, snapshot, tool
from mamey.privacy_profile import (
    PUBLIC_FILE_HOLD_RECEIPT, public_file_hold_findings,
    verify_public_file_hold_omissions,
)


def prior_fixture(tmp_path, *, excluded_parent=False):
    audit = tool("public_release_audit")
    raw, exported, policy = fixture(tmp_path)
    if excluded_parent:
        policy = replace(policy, excluded_relative_paths=frozenset({"fixture_keys/2"}))
    assert audit.apply_public_export_file_holds(raw, exported, policy)[1] == []
    if excluded_parent:
        assert audit.apply_public_export_exclusions(exported, policy) == (["fixture_keys/2"], [])
    source = tmp_path / "prior_source"
    stage = tmp_path / "recut_stage"
    shutil.copytree(exported, source)
    shutil.copytree(source, stage)
    return audit, raw, source, stage, policy


@pytest.mark.parametrize("excluded_parent", [False, True])
def test_verified_prior_omission_preflight_apply_derivation_preserve_every_byte(
        tmp_path, monkeypatch, capsys, excluded_parent):
    audit, raw, source, stage, policy = prior_fixture(tmp_path, excluded_parent=excluded_parent)
    monkeypatch.setattr(audit, "load_public_export_policy", lambda path: policy)
    before_source, before_stage = snapshot(source), snapshot(stage)
    assert public_file_hold_findings(source, policy) == []
    assert audit.main([str(source), "--check-public-export-file-holds"]) == 0
    assert "verified prior omissions" in capsys.readouterr().out
    assert audit.apply_public_export_file_holds(source, stage, policy) == ([], [])
    assert verify_public_file_hold_omissions(source, stage, policy) == (frozenset(), [])
    derive = tool("verify_tier_derivation")
    monkeypatch.setattr(derive, "load_public_export_policy", lambda path: policy)
    monkeypatch.setattr(sys, "argv", ["derive", str(source), str(stage)])
    assert derive.main() == 0
    assert snapshot(source) == before_source and snapshot(stage) == before_stage
    document = json.loads((stage / PUBLIC_FILE_HOLD_RECEIPT).read_text())
    assert document["disposition"] == "PUBLIC_EXPORT_HOLD_UNRESOLVED_AUTHORITY"
    assert (source / PUBLIC_FILE_HOLD_RECEIPT).read_bytes() == (stage / PUBLIC_FILE_HOLD_RECEIPT).read_bytes()


DAMAGES = [
    "missing_receipt", "malformed", "wrong_schema", "cleared_disposition", "wrong_hash",
    "wrong_locator", "unknown_id", "missing_record", "duplicate_record", "duplicate_key",
    "extra_field", "missing_namespace", "live_held_file", "mutated_held_locator",
    "renamed_json", "renamed_other_suffix", "moved_outside_namespace", "duplicate_payload",
    "receipt_symlink", "receipt_hardlink", "held_symlink",
]


@pytest.mark.parametrize("side", ["source", "stage"])
@pytest.mark.parametrize("damage", DAMAGES)
def test_prior_omission_damage_refuses_without_mutation(tmp_path, monkeypatch, side, damage):
    audit, raw, source, stage, policy = prior_fixture(tmp_path)
    selected = source if side == "source" else stage
    receipt = selected / PUBLIC_FILE_HOLD_RECEIPT
    document = json.loads(receipt.read_text())
    payload = held(raw, 1).read_bytes()  # Authored fixture bytes only.
    if damage == "missing_receipt":
        receipt.unlink()
    elif damage == "malformed":
        receipt.write_text("{")
    elif damage == "duplicate_key":
        receipt.write_text('{"schema":"x","schema":"y"}')
    elif damage == "wrong_schema":
        document["schema"] = "stale.v0"
    elif damage == "cleared_disposition":
        document["disposition"] = "PUBLIC_CLEAR"
    elif damage == "wrong_hash":
        document["records"][0]["source_sha256"] = "0" * 64
    elif damage == "wrong_locator":
        document["records"][0]["relative_path_sha256"] = "0" * 64
    elif damage == "unknown_id":
        document["records"][0]["hold_id"] = "UNKNOWN"
    elif damage == "missing_record":
        document["records"].pop()
    elif damage == "duplicate_record":
        document["records"].append(document["records"][0])
    elif damage == "extra_field":
        document["clearance"] = True
    elif damage == "missing_namespace":
        shutil.rmtree(selected / "fixture_keys/1")
    elif damage == "live_held_file":
        held(selected, 1).write_bytes(payload)
    elif damage == "mutated_held_locator":
        held(selected, 1).write_bytes(b"changed invented fixture bytes")
    elif damage in ("renamed_json", "renamed_other_suffix"):
        name = "renamed.json" if damage == "renamed_json" else "renamed.txt"
        (selected / "fixture_keys/1" / name).write_bytes(payload)
    elif damage == "moved_outside_namespace":
        (selected / "relocated").mkdir()
        (selected / "relocated/answer.bin").write_bytes(payload)
    elif damage == "duplicate_payload":
        for name in ("duplicate-a.json", "duplicate-b.txt"):
            (selected / "fixture_keys/1" / name).write_bytes(payload)
    elif damage in ("receipt_symlink", "receipt_hardlink"):
        outside = tmp_path / "outside_receipt.json"
        outside.write_bytes(receipt.read_bytes())
        receipt.unlink()
        if damage == "receipt_symlink":
            receipt.symlink_to(outside)
        else:
            os.link(outside, receipt)
    elif damage == "held_symlink":
        outside = tmp_path / "outside_payload"
        outside.write_bytes(payload)
        held(selected, 1).symlink_to(outside)
    if damage in {
        "wrong_schema", "cleared_disposition", "wrong_hash", "wrong_locator",
        "unknown_id", "missing_record", "duplicate_record", "extra_field",
    }:
        receipt.write_text(json.dumps(document))
    before_source, before_stage = snapshot(source), snapshot(stage)
    monkeypatch.setattr(audit, "load_public_export_policy", lambda path: policy)
    if side == "source":
        assert audit.main([str(source), "--check-public-export-file-holds"]) == 1
    removed, problems = audit.apply_public_export_file_holds(source, stage, policy)
    assert removed == [] and problems
    assert verify_public_file_hold_omissions(source, stage, policy)[1]
    assert snapshot(source) == before_source and snapshot(stage) == before_stage


@pytest.mark.parametrize("damage", ["changed", "missing"])
def test_recut_does_not_exempt_retained_siblings_from_derivation(tmp_path, monkeypatch, damage):
    audit, raw, source, stage, policy = prior_fixture(tmp_path)
    assert audit.apply_public_export_file_holds(source, stage, policy) == ([], [])
    target = stage / "fixture_keys/2/keep.json"
    if damage == "changed":
        target.write_text('{"fixture":"changed unrelated retained file"}')
    else:
        target.unlink()
    before_source, before_stage = snapshot(source), snapshot(stage)
    derive = tool("verify_tier_derivation")
    monkeypatch.setattr(derive, "load_public_export_policy", lambda path: policy)
    monkeypatch.setattr(sys, "argv", ["derive", str(source), str(stage)])
    assert derive.main() != 0
    assert snapshot(source) == before_source and snapshot(stage) == before_stage


def test_receipt_records_are_bound_to_changed_policy(tmp_path):
    audit, raw, source, stage, policy = prior_fixture(tmp_path)
    holds = (replace(policy.file_holds[0], sha256="0" * 64), *policy.file_holds[1:])
    changed = replace(policy, file_holds=holds)
    before = snapshot(source), snapshot(stage)
    assert audit.apply_public_export_file_holds(source, stage, changed)[1]
    assert (snapshot(source), snapshot(stage)) == before

@pytest.mark.parametrize("entrypoint", ["apply", "proof"])
def test_prior_absence_scan_cannot_silently_skip_unreadable_directories(tmp_path, monkeypatch, entrypoint):
    import mamey.privacy_profile as privacy
    audit, raw, source, stage, policy = prior_fixture(tmp_path)
    before_source, before_stage = snapshot(source), snapshot(stage)
    def unreadable_walk(root, *, followlinks, onerror):
        assert followlinks is False
        onerror(PermissionError("authored unreadable subtree"))
        return iter(())
    monkeypatch.setattr(privacy.os, "walk", unreadable_walk)
    if entrypoint == "apply":
        removed, problems = audit.apply_public_export_file_holds(source, stage, policy)
        assert removed == [] and problems
    else:
        omissions, problems = verify_public_file_hold_omissions(source, stage, policy)
        assert omissions == frozenset() and problems
    assert snapshot(source) == before_source and snapshot(stage) == before_stage


