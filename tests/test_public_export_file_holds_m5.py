"""Synthetic software-only file holds; no empirical answer-key or private literals."""
from contextlib import contextmanager
from dataclasses import replace
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import sys

import pytest
import mamey.privacy_profile as privacy

from mamey.privacy_profile import (
    PrivacyProfileError, PublicExportFileHold, PUBLIC_FILE_HOLD_RECEIPT,
    load_public_export_policy, resolve_public_file_holds, public_file_hold_receipt,
    public_file_hold_findings, verify_public_file_hold_omissions,
)

ROOT = Path(__file__).resolve().parents[1]


def tool(name):
    spec = importlib.util.spec_from_file_location("file_hold_test_" + name, ROOT / "tools" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sha(data):
    return hashlib.sha256(data).hexdigest()


def snapshot(root):
    result = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        mode = stat.S_IMODE(path.lstat().st_mode)
        if path.is_symlink():
            result[relative] = ("symlink", mode, os.readlink(path))
        elif path.is_file():
            result[relative] = ("file", mode, sha(path.read_bytes()))
        else:
            result[relative] = ("directory", mode)
    return result


def fixture(tmp_path):
    source, stage = tmp_path / "source", tmp_path / "stage"
    (source / "mamey").mkdir(parents=True)
    (source / "mamey/__init__.py").write_text('__version__ = "1.0.0"\n')
    (source / "BUILD_STAMP.txt").write_text("build=synthetic\n")
    specs = []
    for index in (1, 2):
        parent = source / "fixture_keys" / str(index)
        parent.mkdir(parents=True)
        path = parent / "held.json"
        # Deliberately invented software bytes, with no biological identity/measurements.
        data = json.dumps({"fixture": "INVENTED-SOFTWARE-ANSWER", "case": index}).encode()
        path.write_bytes(data)
        (parent / "keep.json").write_text('{"fixture": "unrelated synthetic baseline"}\n')
        (parent / "README.md").write_text("Separate synthetic reference locator survives.\n")
        relative = path.relative_to(source).as_posix()
        specs.append(PublicExportFileHold("SYNTHETIC-HOLD-" + str(index), parent.relative_to(source).as_posix(),
                                         "*.json", sha(data), sha(relative.encode())))
    policy = replace(load_public_export_policy(), file_holds=tuple(specs))
    shutil.copytree(source, stage)
    return source, stage, policy


def held(root, index):
    return root / "fixture_keys" / str(index) / "held.json"


def test_complete_source_bound_hold_preserves_source_and_every_sibling(tmp_path):
    audit = tool("public_release_audit")
    source, stage, policy = fixture(tmp_path)
    before_source = snapshot(source)
    siblings = {path.relative_to(stage): path.read_bytes() for path in stage.rglob("*")
                if path.is_file() and path.name != "held.json"}
    bindings = resolve_public_file_holds(source, policy)
    removed, problems = audit.apply_public_export_file_holds(source, stage, policy)
    assert problems == [] and len(removed) == 2
    assert snapshot(source) == before_source
    assert all((stage / relative).read_bytes() == data for relative, data in siblings.items())
    assert all(not held(stage, index).exists() for index in (1, 2))
    assert len(list((source / "fixture_keys").rglob("*.json"))) == 4
    assert len(list((stage / "fixture_keys").rglob("*.json"))) == 2
    document = json.loads((stage / PUBLIC_FILE_HOLD_RECEIPT).read_text())
    assert document == public_file_hold_receipt(bindings)
    serialized = json.dumps(document)
    assert str(source) not in serialized and str(stage) not in serialized
    assert "INVENTED-SOFTWARE-ANSWER" not in serialized and "held.json" not in serialized
    assert public_file_hold_findings(stage, policy) == []
    omissions, problems = verify_public_file_hold_omissions(source, stage, policy)
    assert problems == [] and omissions == frozenset({"fixture_keys/1/held.json", "fixture_keys/2/held.json"})


@pytest.mark.parametrize("damage", ["later_missing", "later_stage_digest", "later_source_digest",
                                    "duplicate_hash", "locator_drift", "receipt_occupied", "namespace_missing"])
def test_all_roster_refusals_preserve_first_stage_file_and_source(tmp_path, damage):
    audit = tool("public_release_audit")
    source, stage, policy = fixture(tmp_path)
    if damage == "later_missing":
        held(stage, 2).unlink()
    elif damage == "later_stage_digest":
        held(stage, 2).write_bytes(b"deliberately changed synthetic bytes")
    elif damage == "later_source_digest":
        held(source, 2).write_bytes(b"deliberately changed synthetic bytes")
    elif damage == "duplicate_hash":
        shutil.copyfile(held(stage, 2), held(stage, 2).with_name("duplicate.json"))
    elif damage == "locator_drift":
        held(stage, 2).rename(held(stage, 2).with_name("renamed.json"))
    elif damage == "receipt_occupied":
        (stage / PUBLIC_FILE_HOLD_RECEIPT).write_bytes(b"previous evidence")
    else:
        shutil.rmtree(stage / "fixture_keys/2")
    source_before, stage_before = snapshot(source), snapshot(stage)
    removed, problems = audit.apply_public_export_file_holds(source, stage, policy)
    assert removed == [] and problems
    assert snapshot(source) == source_before and snapshot(stage) == stage_before
    assert held(stage, 1).is_file()


@pytest.mark.parametrize("alias", ["leaf", "ancestor", "hardlink", "root", "overlap"])
def test_aliases_never_remove_outside_or_source_bytes(tmp_path, alias):
    audit = tool("public_release_audit")
    source, stage, policy = fixture(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel.json"
    sentinel.write_bytes(held(stage, 2).read_bytes())
    applied_stage = stage
    if alias == "leaf":
        held(stage, 2).unlink()
        held(stage, 2).symlink_to(sentinel)
    elif alias == "ancestor":
        shutil.rmtree(stage / "fixture_keys/2")
        (stage / "fixture_keys/2").symlink_to(outside, target_is_directory=True)
    elif alias == "hardlink":
        held(stage, 2).unlink()
        os.link(held(source, 2), held(stage, 2))
    elif alias == "root":
        applied_stage = tmp_path / "stage_alias"
        applied_stage.symlink_to(stage, target_is_directory=True)
    else:
        applied_stage = source
    before = snapshot(tmp_path)
    removed, problems = audit.apply_public_export_file_holds(source, applied_stage, policy)
    assert removed == [] and problems
    assert snapshot(tmp_path) == before and sentinel.read_bytes() == held(source, 2).read_bytes()


def test_late_second_stage_identity_drift_is_found_before_first_unlink(tmp_path, monkeypatch):
    audit = tool("public_release_audit")
    source, stage, policy = fixture(tmp_path)
    original = audit.resolve_public_file_holds
    calls = 0
    def mutate_after_initial_rosters(root, selected_policy):
        nonlocal calls
        calls += 1
        if calls == 3:
            held(stage, 2).write_bytes(b"external synthetic drift")
        return original(root, selected_policy)
    monkeypatch.setattr(audit, "resolve_public_file_holds", mutate_after_initial_rosters)
    before_source = snapshot(source)
    first_before = held(stage, 1).read_bytes()
    removed, problems = audit.apply_public_export_file_holds(source, stage, policy)
    assert removed == [] and problems
    assert snapshot(source) == before_source and held(stage, 1).read_bytes() == first_before
    assert held(stage, 2).read_bytes() == b"external synthetic drift"
    assert not (stage / PUBLIC_FILE_HOLD_RECEIPT).exists()


@pytest.mark.parametrize("damage", ["hash", "locator", "extra", "duplicate", "missing_record",
                                    "receipt_symlink", "reintroduced_locator", "unexpected_parent_omission"])
def test_omission_proof_rejects_forged_receipts_and_undeclared_removal(tmp_path, damage):
    audit = tool("public_release_audit")
    source, stage, policy = fixture(tmp_path)
    assert audit.apply_public_export_file_holds(source, stage, policy)[1] == []
    receipt = stage / PUBLIC_FILE_HOLD_RECEIPT
    document = json.loads(receipt.read_text())
    if damage == "hash":
        document["records"][1]["source_sha256"] = "0" * 64
    elif damage == "locator":
        document["records"][1]["relative_path_sha256"] = "0" * 64
    elif damage == "extra":
        document["extra"] = "forged"
    elif damage == "duplicate":
        document["records"].append(document["records"][0])
    elif damage == "missing_record":
        document["records"].pop()
    elif damage == "receipt_symlink":
        other = tmp_path / "outside_receipt.json"
        other.write_bytes(receipt.read_bytes())
        receipt.unlink()
        receipt.symlink_to(other)
    elif damage == "reintroduced_locator":
        held(stage, 1).write_bytes(b"changed content at held locator")
    else:
        shutil.rmtree(stage / "fixture_keys/2")
    if damage not in ("receipt_symlink", "reintroduced_locator", "unexpected_parent_omission"):
        receipt.write_text(json.dumps(document))
    source_before, stage_before = snapshot(source), snapshot(stage)
    omissions, problems = verify_public_file_hold_omissions(source, stage, policy)
    assert omissions == frozenset() and problems
    assert snapshot(source) == source_before and snapshot(stage) == stage_before


@pytest.mark.parametrize("damage", ["retained_changed", "retained_missing", "source_changed"])
def test_actual_derivation_keeps_unrelated_content_checks(tmp_path, monkeypatch, damage):
    audit, derive = tool("public_release_audit"), tool("verify_tier_derivation")
    source, stage, policy = fixture(tmp_path)
    assert audit.apply_public_export_file_holds(source, stage, policy)[1] == []
    monkeypatch.setattr(derive, "load_public_export_policy", lambda path: policy)
    monkeypatch.setattr(sys, "argv", ["verify", str(source), str(stage)])
    assert derive.main() == 0
    retained = stage / "fixture_keys/2/keep.json"
    if damage == "retained_changed":
        retained.write_text('{"fixture": "changed"}')
    elif damage == "retained_missing":
        retained.unlink()
    else:
        held(source, 2).write_bytes(b"source no longer agrees with hold")
    before_source, before_stage = snapshot(source), snapshot(stage)
    assert derive.main() != 0
    assert snapshot(source) == before_source and snapshot(stage) == before_stage


def test_directory_exclusion_api_remains_directory_only(tmp_path):
    audit = tool("public_release_audit")
    source, stage, policy = fixture(tmp_path)
    file_policy = replace(policy, excluded_relative_paths=frozenset({"fixture_keys/1/held.json"}))
    before = snapshot(stage)
    removed, problems = audit.apply_public_export_exclusions(stage, file_policy)
    assert removed == [] and any("NOT_DIRECTORY" in problem for problem in problems)
    assert snapshot(stage) == before


def test_declared_directory_policy_can_remove_parent_after_exact_hold(tmp_path):
    audit = tool("public_release_audit")
    source, stage, policy = fixture(tmp_path)
    policy = replace(policy, excluded_relative_paths=frozenset({"fixture_keys/2"}))
    before_source = snapshot(source)
    assert audit.apply_public_export_file_holds(source, stage, policy)[1] == []
    assert audit.apply_public_export_exclusions(stage, policy) == (["fixture_keys/2"], [])
    assert verify_public_file_hold_omissions(source, stage, policy)[1] == []
    assert snapshot(source) == before_source


def test_missing_namespace_is_explicit_minimal_source_absence(tmp_path):
    audit = tool("public_release_audit")
    source, stage = tmp_path / "source", tmp_path / "stage"
    source.mkdir()
    stage.mkdir()
    policy = load_public_export_policy()
    before = snapshot(tmp_path)
    assert resolve_public_file_holds(source, policy) == ()
    assert audit.apply_public_export_file_holds(source, stage, policy) == ([], [])
    assert public_file_hold_findings(stage, policy) == []
    assert verify_public_file_hold_omissions(source, stage, policy) == (frozenset(), [])
    assert snapshot(tmp_path) == before


def test_default_hold_cannot_be_removed_by_operator_profile(tmp_path):
    default = load_public_export_policy()
    assert len(default.file_holds) == 1
    assert default.file_holds[0].parent == "Wheelhouse/validations"
    profile = tmp_path / "profile.json"
    controls = {"exclude_root_names": [], "exclude_relative_paths": []}
    profile.write_text(json.dumps({"schema_version": "sapote_privacy_profile_v1", "public_export_policy": controls}))
    assert load_public_export_policy(profile).file_holds == default.file_holds
    controls["file_holds"] = []
    profile.write_text(json.dumps({"schema_version": "sapote_privacy_profile_v1", "public_export_policy": controls}))
    with pytest.raises(PrivacyProfileError, match="unknown"):
        load_public_export_policy(profile)


def test_explicit_file_hold_cli_actions_remain_narrow_and_typed(tmp_path, monkeypatch, capsys):
    audit = tool("public_release_audit")
    source, stage, policy = fixture(tmp_path)
    monkeypatch.setattr(audit, "load_public_export_policy", lambda path: policy)
    source_before = snapshot(source)
    assert audit.main([str(source), "--check-public-export-file-holds"]) == 0
    assert "not whole-tree clearance" in capsys.readouterr().out
    assert snapshot(source) == source_before
    with pytest.raises(SystemExit):
        audit.main([str(stage), "--apply-public-export-file-holds"])
    assert audit.main([str(stage), "--apply-public-export-file-holds", "--file-hold-source", str(source)]) == 0
    assert "not whole-tree clearance" in capsys.readouterr().out
    assert audit.main([str(stage), "--file-hold-source", str(source)]) == 0
    assert snapshot(source) == source_before


def test_builder_binds_source_before_copy_and_apply_before_transformation():
    script = (ROOT / "tools/make_public_tier.sh").read_text()
    assert script.index('--check-public-export-file-holds') < script.index('WORK="$(mktemp -d)"')
    assert script.index('cp -a "$SRC/." "$STAGE/"') < script.index('--apply-public-export-file-holds')
    assert script.index('--apply-public-export-file-holds') < script.index('# BEGIN COMMON CORRESPONDENCE EXCLUSION')
    assert 'if [ "$TIER" != "merged" ]; then' in script
    assert '"$PYTHON" "$SRC/tools/public_release_audit.py" "$@"' in script
    audit_helper = script.split("public_release_audit_stage() {", 1)[1].split("\n}", 1)[0]
    assert audit_helper.count('--file-hold-source "$SRC"') == 4


def test_duplicate_receipt_keys_refuse_without_echoing_supplied_key(tmp_path):
    audit = tool("public_release_audit")
    source, stage, policy = fixture(tmp_path)
    assert audit.apply_public_export_file_holds(source, stage, policy)[1] == []
    (stage / PUBLIC_FILE_HOLD_RECEIPT).write_text('{"UNTRUSTED-SYNTHETIC-KEY":1,"UNTRUSTED-SYNTHETIC-KEY":2}')
    before_source, before_stage = snapshot(source), snapshot(stage)
    omitted, problems = verify_public_file_hold_omissions(source, stage, policy)
    assert omitted == frozenset() and problems == ["FILE_HOLD_RECEIPT_UNREADABLE"]
    assert "UNTRUSTED-SYNTHETIC-KEY" not in " ".join(problems)
    assert snapshot(source) == before_source and snapshot(stage) == before_stage


def test_plain_audit_is_readonly_and_refuses_unapplied_hold(tmp_path):
    audit = tool("public_release_audit")
    source, stage, policy = fixture(tmp_path)
    before_source, before_stage = snapshot(source), snapshot(stage)
    expected = {"PUBLIC_PROVENANCE_HOLD_SHIPS: SYNTHETIC-HOLD-1",
                "PUBLIC_PROVENANCE_HOLD_SHIPS: SYNTHETIC-HOLD-2"}
    assert set(public_file_hold_findings(stage, policy)) == expected
    assert expected.issubset(set(audit.audit(stage, policy)))
    assert snapshot(source) == before_source and snapshot(stage) == before_stage


def test_post_preflight_io_failure_requires_disposable_stage_discard(tmp_path, monkeypatch):
    audit = tool("public_release_audit")
    source, stage, policy = fixture(tmp_path)
    before_source = snapshot(source)
    original_unlink = os.unlink
    parent_identity = (held(stage, 2).parent.stat().st_dev, held(stage, 2).parent.stat().st_ino)
    def fail_later(path, *args, **kwargs):
        descriptor = kwargs.get("dir_fd")
        if descriptor is not None:
            info = os.fstat(descriptor)
            if path == "held.json" and (info.st_dev, info.st_ino) == parent_identity:
                raise OSError("invented late filesystem failure")
        return original_unlink(path, *args, **kwargs)
    monkeypatch.setattr(os, "unlink", fail_later)
    monkeypatch.setattr(os, "supports_dir_fd", os.supports_dir_fd | {fail_later})
    removed, problems = audit.apply_public_export_file_holds(source, stage, policy)
    assert removed == [] and "FILE_HOLD_DISCARD_STAGE_REQUIRED" in problems
    assert snapshot(source) == before_source
    assert not held(stage, 1).exists() and held(stage, 2).is_file()
    assert not (stage / PUBLIC_FILE_HOLD_RECEIPT).exists()
    assert (stage / "fixture_keys/1/keep.json").is_file()



def test_large_unrelated_json_streams_without_a_candidate_size_cap(tmp_path, monkeypatch):
    audit = tool("public_release_audit")
    source, stage, policy = fixture(tmp_path)
    large = b'{"synthetic_padding":"' + b"x" * (3 * 1024 * 1024) + b'"}'
    relative = "fixture_keys/2/large_unrelated.json"
    (source / relative).write_bytes(large)
    (stage / relative).write_bytes(large)
    source_before = snapshot(source)
    original_open = privacy._open_public_file_hold
    sizes = []
    class GuardedStream:
        def __init__(self, stream):
            self.stream = stream
        def read(self, size=-1):
            assert 0 < size <= 1024 * 1024, "unbounded candidate/receipt read"
            sizes.append(size)
            return self.stream.read(size)
    @contextmanager
    def bounded_reads(root, relative_path):
        with original_open(root, relative_path) as (stream, identity):
            yield GuardedStream(stream), identity
    monkeypatch.setattr(privacy, "_open_public_file_hold", bounded_reads)
    assert audit.apply_public_export_file_holds(source, stage, policy)[1] == []
    assert max(sizes) == 1024 * 1024
    assert sha((stage / relative).read_bytes()) == sha(large)
    assert snapshot(source) == source_before
    assert verify_public_file_hold_omissions(source, stage, policy)[1] == []


def test_only_receipt_decoding_is_bounded_and_refusal_is_readonly(tmp_path):
    audit = tool("public_release_audit")
    source, stage, policy = fixture(tmp_path)
    assert audit.apply_public_export_file_holds(source, stage, policy)[1] == []
    (stage / PUBLIC_FILE_HOLD_RECEIPT).write_bytes(b" " * 65537)
    before_source, before_stage = snapshot(source), snapshot(stage)
    omitted, problems = verify_public_file_hold_omissions(source, stage, policy)
    assert omitted == frozenset() and problems == ["FILE_HOLD_RECEIPT_TOO_LARGE"]
    assert snapshot(source) == before_source and snapshot(stage) == before_stage


def test_parent_replacement_before_first_unlink_preserves_every_admitted_file(tmp_path, monkeypatch):
    audit = tool("public_release_audit")
    source, stage, policy = fixture(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "held.json"
    sentinel.write_bytes(b"outside synthetic evidence")
    first_parent = held(stage, 1).parent
    detached = first_parent.with_name("1-detached")
    first_before = held(stage, 1).read_bytes()
    source_before = snapshot(source)
    original_identity = audit.public_file_hold_entry_identity
    calls = 0
    def replace_after_complete_parent_admission(descriptor, name):
        nonlocal calls
        calls += 1
        # Two parent admissions, then two complete-roster checks.
        if calls == 4:
            first_parent.rename(detached)
            first_parent.symlink_to(outside, target_is_directory=True)
        return original_identity(descriptor, name)
    monkeypatch.setattr(audit, "public_file_hold_entry_identity", replace_after_complete_parent_admission)
    removed, problems = audit.apply_public_export_file_holds(source, stage, policy)
    assert removed == [] and problems and calls == 4
    assert (detached / "held.json").read_bytes() == first_before
    assert held(stage, 2).is_file() and sentinel.read_bytes() == b"outside synthetic evidence"
    assert snapshot(source) == source_before and not (stage / PUBLIC_FILE_HOLD_RECEIPT).exists()


def test_parent_replacement_at_unlink_cannot_redirect_the_owned_leaf(tmp_path, monkeypatch):
    audit = tool("public_release_audit")
    source, stage, policy = fixture(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "held.json"
    sentinel.write_bytes(b"outside synthetic evidence")
    first_parent = held(stage, 1).parent
    detached = first_parent.with_name("1-detached")
    source_before = snapshot(source)
    original_unlink = os.unlink
    swapped = False
    def replace_at_mutation(path, *args, **kwargs):
        nonlocal swapped
        assert kwargs.get("dir_fd") is not None, "mutation must use its admitted parent descriptor"
        if path == "held.json" and not swapped:
            swapped = True
            first_parent.rename(detached)
            first_parent.symlink_to(outside, target_is_directory=True)
        return original_unlink(path, *args, **kwargs)
    monkeypatch.setattr(os, "unlink", replace_at_mutation)
    monkeypatch.setattr(os, "supports_dir_fd", os.supports_dir_fd | {replace_at_mutation})
    removed, problems = audit.apply_public_export_file_holds(source, stage, policy)
    assert swapped and removed == [] and "FILE_HOLD_DISCARD_STAGE_REQUIRED" in problems
    assert sentinel.read_bytes() == b"outside synthetic evidence"
    assert not (detached / "held.json").exists()
    assert snapshot(source) == source_before


def test_root_replacement_at_receipt_creation_cannot_write_outside_stage(tmp_path, monkeypatch):
    audit = tool("public_release_audit")
    source, stage, policy = fixture(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel"
    sentinel.write_bytes(b"outside synthetic evidence")
    detached = tmp_path / "stage-detached"
    source_before = snapshot(source)
    outside_before = snapshot(outside)
    original_open = os.open
    swapped = False
    def replace_at_receipt(path, flags, *args, **kwargs):
        nonlocal swapped
        if path == PUBLIC_FILE_HOLD_RECEIPT and flags & os.O_CREAT:
            assert flags & os.O_EXCL and flags & os.O_NOFOLLOW
            assert kwargs.get("dir_fd") is not None
            stage.rename(detached)
            stage.symlink_to(outside, target_is_directory=True)
            swapped = True
        return original_open(path, flags, *args, **kwargs)
    monkeypatch.setattr(os, "open", replace_at_receipt)
    # supports_dir_fd is function-keyed: keep the wrapper's advertised original capability.
    monkeypatch.setattr(os, "supports_dir_fd", os.supports_dir_fd | {replace_at_receipt})
    removed, problems = audit.apply_public_export_file_holds(source, stage, policy)
    assert swapped and removed == [] and "FILE_HOLD_DISCARD_STAGE_REQUIRED" in problems
    assert snapshot(outside) == outside_before and snapshot(source) == source_before
    assert (detached / PUBLIC_FILE_HOLD_RECEIPT).is_file()
    assert not (outside / PUBLIC_FILE_HOLD_RECEIPT).exists()



def test_receipt_stat_error_is_not_mistaken_for_missing_destination(tmp_path, monkeypatch):
    audit = tool("public_release_audit")
    source, stage, policy = fixture(tmp_path)
    source_before, stage_before = snapshot(source), snapshot(stage)
    original_stat = os.stat
    def unreadable_receipt(path, *args, **kwargs):
        if path == PUBLIC_FILE_HOLD_RECEIPT and kwargs.get("dir_fd") is not None:
            raise PermissionError("invented receipt probe failure")
        return original_stat(path, *args, **kwargs)
    monkeypatch.setattr(os, "stat", unreadable_receipt)
    monkeypatch.setattr(os, "supports_dir_fd", os.supports_dir_fd | {unreadable_receipt})
    monkeypatch.setattr(os, "supports_follow_symlinks", os.supports_follow_symlinks | {unreadable_receipt})
    removed, problems = audit.apply_public_export_file_holds(source, stage, policy)
    assert removed == [] and problems
    assert "FILE_HOLD_RECEIPT_OCCUPIED" not in problems
    assert "FILE_HOLD_DISCARD_STAGE_REQUIRED" not in problems
    assert snapshot(source) == source_before and snapshot(stage) == stage_before



@pytest.mark.parametrize("invalid_hold_id", [[], {}, None, 0, ""])
def test_malformed_receipt_hold_ids_have_typed_readonly_refusal(tmp_path, invalid_hold_id):
    audit = tool("public_release_audit")
    source, stage, policy = fixture(tmp_path)
    assert audit.apply_public_export_file_holds(source, stage, policy)[1] == []
    receipt = stage / PUBLIC_FILE_HOLD_RECEIPT
    document = json.loads(receipt.read_text())
    document["records"][0]["hold_id"] = invalid_hold_id
    receipt.write_text(json.dumps(document))
    source_before, stage_before = snapshot(source), snapshot(stage)
    assert public_file_hold_findings(stage, policy) == ["FILE_HOLD_RECEIPT_INVALID"]
    assert "FILE_HOLD_RECEIPT_INVALID" in audit.audit(stage, policy)
    assert verify_public_file_hold_omissions(source, stage, policy) == (
        frozenset(), ["FILE_HOLD_SOURCE_RECEIPT_MISMATCH"])
    assert snapshot(source) == source_before and snapshot(stage) == stage_before
