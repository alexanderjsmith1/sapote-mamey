"""Exact scanner export exclusions, tested with nonbiological payload bytes."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from tools import scanner_hmm_release_policy as policy
from tests._public_cut_fixture import (
    ROOT, SCANNER_FIXTURE_ASSETS, GENERIC_HMM_ASSETS,
    assert_scanner_archive_policy, public_cut_env, public_cut_source,
)


def _seed(root: Path):
    for relative, payload in {**SCANNER_FIXTURE_ASSETS, **GENERIC_HMM_ASSETS}.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)


def test_only_reserved_scanner_basenames_and_indexes_are_classified():
    expected = {
        base + suffix for base in ("scanner_pfam.hmm", "scanner_pfam_150.hmm")
        for suffix in ("", ".h3f", ".h3i", ".h3m", ".h3p")
    }
    assert policy.SCANNER_ASSET_BASENAMES == expected
    for name in expected:
        assert policy.is_provisioned_scanner_asset(name)
        assert policy.is_provisioned_scanner_asset("operator_copy/hmm/" + name)
        assert not policy.is_provisioned_scanner_asset("../" + name)
        assert not policy.is_provisioned_scanner_asset("/external/" + name)


@pytest.mark.parametrize("name", [
    "generic.hmm", "Pfam-A.hmm", "generic.hmm.h3i", "scanner_pfam.hmm.h3x",
    "scanner_pfam.hmm.bak", "scanner_pfam.hmm.build_receipt.json",
    "prefix_scanner_pfam.hmm", "scanner_pfam.hmm_suffix", "SCANNER_PFAM.HMM",
])
def test_index_like_suffixes_and_name_substrings_are_retained(tmp_path, name):
    target = tmp_path / name
    target.write_bytes(b"unrelated fixture")
    assert not policy.is_provisioned_scanner_asset(name)
    assert policy.strip_stage_assets(tmp_path) == 0
    assert target.read_bytes() == b"unrelated fixture"


def test_staged_strip_preserves_source_and_unrelated_assets(tmp_path):
    source, stage = tmp_path / "source", tmp_path / "stage"
    _seed(source)
    shutil.copytree(source, stage)
    assert policy.strip_stage_assets(stage) == 10
    assert policy.check_stage_assets(stage) == 0
    for relative, payload in {**SCANNER_FIXTURE_ASSETS, **GENERIC_HMM_ASSETS}.items():
        assert (source / relative).read_bytes() == payload
        if relative in SCANNER_FIXTURE_ASSETS:
            assert not (stage / relative).exists()
        else:
            assert (stage / relative).read_bytes() == payload


def test_orphan_indexes_are_stripped(tmp_path):
    target = tmp_path / "scanner_pfam_150.hmm.h3p"
    target.write_bytes(b"orphan index")
    assert policy.strip_stage_assets(tmp_path) == 1
    assert not target.exists()


def test_leaf_symlink_is_unlinked_without_touching_target(tmp_path):
    external = tmp_path / "external"
    external.write_bytes(b"immutable external target")
    stage = tmp_path / "stage"
    stage.mkdir()
    leaf = stage / "scanner_pfam.hmm"
    leaf.symlink_to(external)
    assert policy.strip_stage_assets(stage) == 1
    assert not os.path.lexists(leaf)
    assert external.read_bytes() == b"immutable external target"


def test_stage_root_symlink_is_refused_and_external_directory_is_not_followed(tmp_path):
    external = tmp_path / "external"
    external.mkdir()
    target = external / "scanner_pfam.hmm"
    target.write_bytes(b"immutable external model fixture")
    linked_root = tmp_path / "linked_root"
    linked_root.symlink_to(external, target_is_directory=True)
    with pytest.raises(policy.ScannerAssetPolicyError, match="SCAN_OR_REMOVAL_FAILED"):
        policy.strip_stage_assets(linked_root)
    stage = tmp_path / "stage"
    stage.mkdir()
    (stage / "unrelated_link").symlink_to(external, target_is_directory=True)
    assert policy.strip_stage_assets(stage) == 0
    assert target.read_bytes() == b"immutable external model fixture"


def test_directory_named_as_asset_is_refused(tmp_path):
    (tmp_path / "scanner_pfam.hmm").mkdir()
    other = tmp_path / "scanner_pfam_150.hmm"
    other.write_bytes(b"not removed on incomplete preflight")
    with pytest.raises(policy.ScannerAssetPolicyError, match="ASSET_IS_DIRECTORY"):
        policy.strip_stage_assets(tmp_path)
    assert other.read_bytes() == b"not removed on incomplete preflight"


@pytest.mark.parametrize("operation", [policy.strip_stage_assets, policy.check_stage_assets])
def test_incomplete_traversal_refuses(tmp_path, monkeypatch, operation):
    def unreadable(_directory_fd):
        raise PermissionError("synthetic unreadable directory")
    monkeypatch.setattr(policy.os, "listdir", unreadable)
    with pytest.raises(policy.ScannerAssetPolicyError, match="SCAN_OR_REMOVAL_FAILED"):
        operation(tmp_path)


def test_incomplete_removal_refuses(tmp_path, monkeypatch):
    target = tmp_path / "scanner_pfam.hmm"
    target.write_bytes(b"not removable")
    def refused(*_args, **_kwargs):
        raise PermissionError("synthetic removal refusal")
    monkeypatch.setattr(policy.os, "unlink", refused)
    with pytest.raises(policy.ScannerAssetPolicyError, match="SCAN_OR_REMOVAL_FAILED"):
        policy.strip_stage_assets(tmp_path)
    assert target.read_bytes() == b"not removable"


def test_post_gate_check_refuses_reintroduced_asset(tmp_path):
    policy.strip_stage_assets(tmp_path)
    target = tmp_path / "scanner_pfam.hmm.h3m"
    target.write_bytes(b"reintroduced index")
    with pytest.raises(policy.ScannerAssetPolicyError, match="RESERVED_ASSET_REMAINS"):
        policy.check_stage_assets(tmp_path)
    assert target.read_bytes() == b"reintroduced index"


@pytest.mark.skipif(not shutil.which("bash"), reason="bash unavailable")
@pytest.mark.parametrize("tier", ["code", "clean", "cohort", "public", "merged"])
def test_all_nonprivate_tiers_omit_reserved_assets_and_merged_preserves(tmp_path, tier):
    source = public_cut_source(tmp_path, with_hmm=True)
    output = tmp_path / "output"
    result = subprocess.run(
        ["bash", str(ROOT / "tools/make_public_tier.sh"), tier, str(source), str(output)],
        cwd=source, env=public_cut_env(), capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, (result.stdout + result.stderr)[-3000:]
    archives = list(output.glob("*.zip"))
    assert len(archives) == 1
    assert_scanner_archive_policy(archives[0], source, stripped=tier != "merged")


@pytest.mark.skipif(not shutil.which("bash"), reason="bash unavailable")
def test_builder_refuses_asset_reintroduced_by_real_intier_test(tmp_path):
    source = public_cut_source(tmp_path, with_hmm=True)
    (source / "tests/test_synthetic_payload.py").write_text(
        "from pathlib import Path\n"
        "def test_synthetic_payload():\n"
        "    target = Path('Wheelhouse/hmm/scanner_pfam.hmm.h3i')\n"
        "    target.parent.mkdir(parents=True, exist_ok=True)\n"
        "    target.write_bytes(b'synthetic gate output')\n",
        encoding="utf-8",
    )
    output = tmp_path / "output"
    result = subprocess.run(
        ["bash", str(ROOT / "tools/make_public_tier.sh"), "code", str(source), str(output)],
        cwd=source, env=public_cut_env(skip_pytest=False), capture_output=True, text=True, timeout=120,
    )
    assert result.returncode != 0
    assert "scanner assets reappeared after staged gates" in result.stderr
    assert not list(output.glob("*.zip"))
    for relative, payload in {**SCANNER_FIXTURE_ASSETS, **GENERIC_HMM_ASSETS}.items():
        assert (source / relative).read_bytes() == payload


def test_parity_omission_uses_shared_classifier_without_hiding_generic_drift(tmp_path):
    source = tmp_path / "source"
    public = tmp_path / "public"
    _seed(source)
    shutil.copytree(source, public)
    policy.strip_stage_assets(public)
    argv = [sys.executable, str(ROOT / "tools/verify_tier_derivation.py"),
            str(source), str(public), "--ext", ".hmm,.h3f,.h3i,.h3m,.h3p"]
    matching = subprocess.run(argv, capture_output=True, text=True, timeout=30)
    assert matching.returncode == 0, matching.stdout + matching.stderr
    generic = public / next(iter(GENERIC_HMM_ASSETS))
    generic.unlink()
    missing = subprocess.run(argv, capture_output=True, text=True, timeout=30)
    assert missing.returncode != 0
    assert "MISSING_FROM_PUBLIC : 1" in missing.stdout
    generic.write_bytes(b"changed generic fixture")
    changed = subprocess.run(argv, capture_output=True, text=True, timeout=30)
    assert changed.returncode != 0
    assert "MISMATCHES        : 1" in changed.stdout
