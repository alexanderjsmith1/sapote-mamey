"""Regression tests for the check-only generated-surface ownership planner."""
import hashlib
import importlib.util
import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "generated_surface_ownership.py"
SPEC = importlib.util.spec_from_file_location("generated_surface_ownership", TOOL)
ownership = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ownership)


def _invoke(capsys, *args):
    rc = ownership.main(["--root", str(ROOT), "--json", *args])
    return rc, json.loads(capsys.readouterr().out)


def _tree_hashes(root):
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*")) if path.is_file()
    }


def test_source_final_distinguishes_prior_generated_inputs_from_deferred_tier_outputs(capsys):
    rc, payload = _invoke(
        capsys,
        "--phase", "source-final",
        "--assert-input", "module_manifest,tools_inventory",
        "--assert-final", "module_manifest,tools_inventory,version_build,release_manifest",
    )
    assert rc == 0
    assert payload["status"] == "PASS"
    assert payload["expected_inputs"] == ["module_manifest", "tools_inventory"]
    assert payload["expected_final_outputs"] == ["module_manifest", "tools_inventory", "version_build", "release_manifest"]
    assert payload["deferred_outputs"] == ["tier_manifest", "source_checksums"]


def test_source_final_refuses_tier_outputs_as_source_final_and_creates_nothing(capsys):
    before = _tree_hashes(ROOT)
    rc, payload = _invoke(
        capsys,
        "--phase", "source-final",
        "--assert-input", "module_manifest,tools_inventory",
        "--assert-final", "source_checksums",
    )
    assert rc == 2
    assert payload["status"] == "REFUSED"
    assert any(item["code"] == "DECLARED_FINAL_SET_MISMATCH" for item in payload["findings"])
    assert _tree_hashes(ROOT) == before


def test_tier_final_accepts_final_source_surfaces_as_inputs(capsys):
    rc, payload = _invoke(
        capsys,
        "--phase", "tier-final",
        "--assert-input", "module_manifest,tools_inventory,version_build,release_manifest",
        "--assert-final", "tier_manifest,source_checksums",
    )
    assert rc == 0
    assert payload["status"] == "PASS"
    assert payload["expected_final_outputs"] == ["tier_manifest", "source_checksums"]


def test_missing_owner_or_surface_path_refuses(capsys, tmp_path):
    rc = ownership.main([
        "--root", str(tmp_path), "--phase", "source-generated",
        "--assert-input", "none", "--assert-final", "module_manifest,tools_inventory", "--json",
    ])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 2
    assert payload["status"] == "REFUSED"
    assert any(item["code"] == "MISSING_OWNER_OR_SURFACE_PATH" for item in payload["findings"])
