from __future__ import annotations

import csv
import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest

from mamey.exact_identity import ExactLocusIdentityError, exact_locus_display
from mamey.lab_quest import (
    EngineBindingError,
    PackageSnapshot,
    build_engine_command,
    build_run_command,
    build_station_command,
    contained_path,
    export_private_project_handoff,
    formal_review_markdown,
    lab_quest_launch_command,
    load_package_snapshot,
    register_subparser,
    resolve_project_root,
    resolve_engine_binding,
    run_from_args,
    safe_upload_name,
    station_artifact_paths,
    validate_package_with_bound_engine,
    validate_strain_token,
    write_run_receipt,
)
from mamey.lab_quest_registry import EvidenceState, STATIONS, WorkflowRegistry, WorkflowState
from mamey.project_catalog import ProjectCatalog


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _code_tier(tmp_path: Path, *, bundle: str = "9.7.test", engine: str = "1.9.test") -> Path:
    root = tmp_path / "portable_code_tier"
    (root / "mamey").mkdir(parents=True)
    (root / "mamey_run.py").write_text("print('fixture runner')\n", encoding="utf-8")
    (root / "mamey" / "__init__.py").write_text(
        f'__version__ = "{engine}"\nBUNDLE_VERSION = "{bundle}"\n', encoding="utf-8"
    )
    (root / "pyproject.toml").write_text(
        "[project]\nname = 'mamey'\nversion = '" + engine + "'\n"
        "[tool.sapote]\nbundle_version = '" + bundle + "'\n",
        encoding="utf-8",
    )
    return root


def _binding(tmp_path: Path):
    root = _code_tier(tmp_path)
    return resolve_engine_binding(root, expected_bundle_version="9.7.test", expected_engine_version="1.9.test")


def _fixture_package(project: Path) -> PackageSnapshot:
    package = project / "runs" / "TEST-01" / "package"
    package.mkdir(parents=True)
    manifest = {
        "strain_id": "TEST-01",
        "workflow_version": "1.9.test",
        "bundle_version": "9.7.test",
        "mode": "gold",
    }
    (package / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (package / "TEST-01_1_intake.json").write_text(json.dumps({"release": "PRIVATE"}), encoding="utf-8")
    row = {
        "BGC_ID": "BGC001",
        "Node_ID": "NODE_1_length_12345_cov_20.5",
        "antiSMASH_Region": "region001",
        "Products": "RiPP-like",
    }
    _write_csv(package / "TEST-01_2_inventory.csv", [row])
    _write_csv(package / "TEST-01_4_triage_board.csv", [row])
    return PackageSnapshot(
        package=package,
        strain="TEST-01",
        manifest_sha256="",
        workflow_version="1.9.test",
        bundle_version="9.7.test",
        mode="gold",
        release="PRIVATE",
        validator_status="PASS",
        evidence_date_utc="2026-01-01T00:00:00+00:00",
        inventory=tuple(),
        triage=tuple(),
    )


def _snapshot_with_hash(snapshot: PackageSnapshot) -> PackageSnapshot:
    from mamey.lab_quest import sha256_file

    return PackageSnapshot(
        **{**snapshot.__dict__, "manifest_sha256": sha256_file(snapshot.package / "manifest.json")}
    )


def _catalog_package(root: Path, relative: str, strain: str, release: str) -> Path:
    package = root / relative
    package.mkdir(parents=True)
    (package / "manifest.json").write_text(json.dumps({
        "strain_id": strain,
        "bundle_version": "9.7.test",
        "workflow_version": "1.9.test",
        "privacy_tier": "OPEN" if release == "PUBLIC" else "LAB_INTERNAL",
        "privacy_assignment_state": "EXACT",
        "release": release,
    }), encoding="utf-8")
    (package / f"{strain}_2_inventory.csv").write_text("BGC_ID\n", encoding="utf-8")
    return package


def test_exact_locus_display_requires_full_identity():
    value = exact_locus_display("TEST-01", "NODE_1_length_12345_cov_20.5", "region001", "BGC001")
    assert value == "TEST-01 / NODE_1_length_12345_cov_20.5 / region001 / BGC001"
    with pytest.raises(ExactLocusIdentityError):
        exact_locus_display("TEST-01", "NODE_1", "region001", "BGC001")


@pytest.mark.parametrize("name", ["../x.zip", "a/b.zip", r"a\b.zip", "not-a-zip.txt"])
def test_upload_name_rejects_unsafe_inputs(name):
    with pytest.raises(ValueError):
        safe_upload_name(name)


def test_engine_binding_requires_explicit_matching_root_and_versions(tmp_path):
    root = _code_tier(tmp_path)
    binding = resolve_engine_binding(root, expected_bundle_version="9.7.test", expected_engine_version="1.9.test")
    assert binding.code_tier == root
    with pytest.raises(EngineBindingError, match="stale or unexpected"):
        resolve_engine_binding(root, expected_bundle_version="9.7.other", expected_engine_version="1.9.test")
    (root / "mamey" / "__init__.py").write_text('__version__ = "1.9.wrong"\nBUNDLE_VERSION = "9.7.test"\n', encoding="utf-8")
    with pytest.raises(EngineBindingError, match="versions disagree"):
        resolve_engine_binding(root, expected_bundle_version="9.7.test", expected_engine_version="1.9.test")


def test_launcher_requires_an_explicit_project_root():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    register_subparser(subparsers)
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "lab-quest",
                "--code-tier",
                "/portable/code-tier",
                "--expect-bundle-version",
                "9.7.test",
                "--expect-engine-version",
                "1.9.test",
            ]
        )


def test_verify_only_checks_binding_without_streamlit(tmp_path, monkeypatch):
    binding_root = _code_tier(tmp_path)
    project = tmp_path / "project"
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None if name == "streamlit" else importlib.util.find_spec(name))
    args = SimpleNamespace(
        project_root=project,
        code_tier=binding_root,
        expect_bundle_version="9.7.test",
        expect_engine_version="1.9.test",
        verify_only=True,
        port=8501,
        headless=True,
    )
    assert run_from_args(args) == 0
    assert (project / "lab_quest_outputs" / "engine_binding.json").is_file()


def test_bound_engine_refuses_runner_or_metadata_drift_before_execution(tmp_path):
    root = _code_tier(tmp_path)
    binding = resolve_engine_binding(root, expected_bundle_version="9.7.test", expected_engine_version="1.9.test")
    (root / "mamey_run.py").write_text("print('changed')\n", encoding="utf-8")
    with pytest.raises(EngineBindingError, match="mamey_run.py"):
        build_engine_command(binding, "--help")
    binding = resolve_engine_binding(root, expected_bundle_version="9.7.test", expected_engine_version="1.9.test")
    (root / "pyproject.toml").write_text((root / "pyproject.toml").read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")
    with pytest.raises(EngineBindingError, match="pyproject.toml"):
        build_engine_command(binding, "--help")


def test_public_catalog_listing_filters_private_identifier_before_rendering(tmp_path):
    project = tmp_path / "project"
    catalog = ProjectCatalog(project)
    public = _catalog_package(project, "runs/public/package", "PUBLIC-DEMO-01", "PUBLIC")
    private = _catalog_package(project, "runs/private/package", "PRIVATE-SYNTHETIC-SECRET", "PRIVATE")
    catalog.register_package(public)
    catalog.register_package(private)

    public_rows = catalog.listing_rows("PUBLIC")
    rendered_widget_payload = json.dumps(public_rows, sort_keys=True)
    assert [row["strain_id"] for row in public_rows] == ["PUBLIC-DEMO-01"]
    assert "PRIVATE-SYNTHETIC-SECRET" not in rendered_widget_payload
    assert catalog.verified_packages("PUBLIC") == (public,)


def test_public_listing_never_touches_a_stale_private_entry(tmp_path):
    project = tmp_path / "project"
    catalog = ProjectCatalog(project)
    public = _catalog_package(project, "runs/public/package", "PUBLIC-DEMO-01", "PUBLIC")
    private_marker = "PRIVATE-SYNTHETIC-SECRET"
    private = _catalog_package(project, f"runs/{private_marker}/package", private_marker, "PRIVATE")
    catalog.register_package(public)
    catalog.register_package(private)
    (private / "manifest.json").write_text('{"changed": true}', encoding="utf-8")

    public_payload = json.dumps(catalog.listing_rows("PUBLIC"), sort_keys=True)
    assert private_marker not in public_payload
    with pytest.raises(ValueError, match=private_marker):
        catalog.listing_rows("PRIVATE_PROJECT")


def test_lab_quest_private_project_export_refuses_stale_engine_binding_before_write(tmp_path):
    binding = _binding(tmp_path)
    project = tmp_path / "project"
    package = _catalog_package(project, "runs/private/package", "PRIVATE-SYNTHETIC-SECRET", "PRIVATE")
    ProjectCatalog(project).register_package(package)
    output = tmp_path / "handoff.zip"
    (binding.code_tier / "mamey_run.py").write_text("print('drifted')\n", encoding="utf-8")

    with pytest.raises(EngineBindingError, match="re-bind before execution"):
        export_private_project_handoff(binding=binding, project_root=project, output_zip=output)
    assert not output.exists()


def test_commands_use_only_explicit_bound_runner_and_contained_paths(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    binding = _binding(tmp_path)
    upload = project / "input.zip"
    upload.write_bytes(b"zip")
    command = build_run_command(binding=binding, project_root=project, input_zip=upload, strain="TEST-01")
    assert command[:2] == [sys.executable, str(binding.code_tier / "mamey_run.py")]
    assert "--input-zip" in command and str(upload) in command
    with pytest.raises(ValueError):
        build_run_command(binding=binding, project_root=project, input_zip=tmp_path / "outside.zip", strain="TEST-01")
    package = project / "runs" / "TEST-01" / "package"
    package.mkdir(parents=True)
    station = build_station_command(binding=binding, project_root=project, package=package, station="MODE_B", run_id="r1")
    assert station[:3] == [sys.executable, str(binding.code_tier / "mamey_run.py"), "emit-strain-modeb"]
    assert str(project / "lab_quest_outputs" / "modeb" / "r1_strain_modeb.md") in station


@pytest.mark.parametrize(
    ("station", "expected_subcommand", "required_flags"),
    [
        ("BLASTP", "blastp-status", ("--package",)),
        ("MODE_B", "emit-strain-modeb", ("--package", "--out")),
        ("FIGURES", "render-all-figures", ("--package", "--fail-fast")),
        ("HANDOFF", "handoff", ("--package", "--out")),
    ],
)
def test_station_commands_preserve_current_mamey_cli_contract(tmp_path, station, expected_subcommand, required_flags):
    """Keep the Lab Quest adapter bound to the supported v9.7.389 command shapes."""
    project = tmp_path / "project"
    package = project / "runs" / "TEST-01" / "package"
    package.mkdir(parents=True)
    command = build_station_command(
        binding=_binding(tmp_path),
        project_root=project,
        package=package,
        station=station,
        run_id="receipt-backed-run",
    )
    assert command[2] == expected_subcommand
    assert all(flag in command for flag in required_flags)
    assert command[command.index("--package") + 1] == str(package.resolve())
    if "--out" in required_flags:
        output = Path(command[command.index("--out") + 1])
        assert output.is_relative_to((project / "lab_quest_outputs").resolve())


def test_postseal_station_receipts_require_exact_output_artifacts(tmp_path):
    project = tmp_path / "project"
    package = project / "runs" / "TEST-01" / "package"
    package.mkdir(parents=True)
    assert station_artifact_paths(project_root=project, package=package, station="BLASTP", run_id="r") == ()
    modeb, = station_artifact_paths(project_root=project, package=package, station="MODE_B", run_id="r")
    figures, = station_artifact_paths(project_root=project, package=package, station="FIGURES", run_id="r")
    handoff, = station_artifact_paths(project_root=project, package=package, station="HANDOFF", run_id="r")
    assert modeb == project / "lab_quest_outputs" / "modeb" / "r_strain_modeb.md"
    assert figures == package / "render_all_figures_summary.json"
    assert handoff == project / "lab_quest_outputs" / "handoffs" / "r_handoff.zip"
    binding = _binding(tmp_path)
    input_zip = project / "input.zip"
    input_zip.write_bytes(b"fixture")
    receipt = write_run_receipt(
        project, ["MODE_B"], input_zip, 0, "", "", binding,
        run_id="r", station="MODE_B", artifact_paths=(modeb,),
    )
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["status"] == "FAIL"
    modeb.parent.mkdir(parents=True)
    modeb.write_text("# receipt-bound skeleton\n", encoding="utf-8")
    receipt = write_run_receipt(
        project, ["MODE_B"], input_zip, 0, "", "", binding,
        run_id="r2", station="MODE_B", artifact_paths=(modeb,),
    )
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["status"] == "PASS"
    assert payload["artifacts"][0]["sha256"]


def test_project_paths_and_strain_tokens_are_contained(tmp_path):
    assert contained_path(tmp_path, "runs").parent == tmp_path.resolve()
    with pytest.raises(ValueError, match="explicit Lab Quest project root"):
        resolve_project_root("")
    with pytest.raises(ValueError):
        contained_path(tmp_path, "..", "escape")
    assert validate_strain_token("TEST-01") == "TEST-01"
    with pytest.raises(ValueError):
        validate_strain_token("../TEST")


def test_scientific_review_record_is_persona_free_and_claim_safe(tmp_path):
    binding = _binding(tmp_path)
    project = tmp_path / "project"
    run = SimpleNamespace(
        state=SimpleNamespace(value="PACKAGE_VALIDATED"),
        evidence_state=SimpleNamespace(value="VALIDATED"),
        run_id="run|with`markdown",
        input_sha256="a" * 64,
    )
    record = formal_review_markdown(binding=binding, project_root=project, run=run, snapshot=None)
    assert record.startswith("# Sapote-Mamey scientific review record")
    assert "Lab Quest" not in record and "🧫" not in record
    assert "LOCAL_WORKFLOW_RECORD_NOT_SCIENTIFIC_ACCEPTANCE" in record
    assert "NOT_ADMITTED_BY_INTERFACE" in record
    assert "run\\|with\\`markdown" in record


def test_package_snapshot_joins_exact_identity_and_fails_closed(monkeypatch, tmp_path):
    project = tmp_path / "project"
    snapshot = _fixture_package(project)
    monkeypatch.setattr("mamey.lab_quest.validate_package", lambda *_args, **_kwargs: {"status": "PASS"})
    loaded = load_package_snapshot(snapshot.package)
    assert loaded.inventory[0]["exact_locus"].endswith("/ region001 / BGC001")
    row = {"BGC_ID": "BGC001", "Node_ID": "NODE_1", "antiSMASH_Region": "region001"}
    _write_csv(snapshot.package / "TEST-01_2_inventory.csv", [row])
    with pytest.raises(ExactLocusIdentityError):
        load_package_snapshot(snapshot.package)


def test_package_validation_executes_bound_runner_before_snapshot_admission(monkeypatch, tmp_path):
    project = tmp_path / "project"
    snapshot = _fixture_package(project)
    binding = _binding(tmp_path)
    observed = {}

    def fake_run(command, *, timeout=3600):
        observed["command"] = command
        return subprocess.CompletedProcess(command, 0, "validated", "")

    monkeypatch.setattr("mamey.lab_quest.run_bound_command", fake_run)
    monkeypatch.setattr("mamey.lab_quest.load_package_snapshot", lambda package: _snapshot_with_hash(snapshot))
    command, completed, admitted = validate_package_with_bound_engine(
        binding=binding,
        project_root=project,
        package=snapshot.package,
    )
    assert command == observed["command"]
    assert completed.returncode == 0 and admitted is not None
    assert command[:3] == [sys.executable, str(binding.code_tier / "mamey_run.py"), "validate"]


def test_receipt_backed_registry_rejects_stale_package_manifest(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    binding = _binding(tmp_path)
    input_zip = project / "input.zip"
    input_zip.write_bytes(b"fixture")
    registry = WorkflowRegistry(project)
    run_id = "fixture-run"
    input_receipt = write_run_receipt(project, ["STAGE"], input_zip, 0, "", "", binding, run_id=run_id, station="INPUT")
    run = registry.create_input_run(input_path=input_zip, receipt=input_receipt, binding=binding, run_id=run_id)
    extraction_receipt = write_run_receipt(project, ["RUN"], input_zip, 0, "", "", binding, run_id=run.run_id, station="EXTRACTION")
    run = registry.transition(run.run_id, WorkflowState.EXTRACTION_RECEIPTED, extraction_receipt)
    snapshot = _snapshot_with_hash(_fixture_package(project))
    package_receipt = write_run_receipt(
        project, ["VALIDATE"], input_zip, 0, "", "", binding,
        run_id=run.run_id, station="PACKAGE", package_snapshot=snapshot,
    )
    run = registry.record_package_validation(run.run_id, snapshot, package_receipt)
    assert run.state is WorkflowState.PACKAGE_VALIDATED
    assert run.evidence_state is EvidenceState.VALIDATED
    assert registry.load_last_validated_run(binding).run_id == run.run_id
    blastp_receipt = write_run_receipt(
        project, ["BLASTP"], input_zip, 0, "", "", binding,
        run_id=run.run_id, station="BLASTP", package_snapshot=snapshot,
    )
    run = registry.transition(run.run_id, WorkflowState.BLASTP_STATUS_RECEIPTED, blastp_receipt)
    modeb, = station_artifact_paths(project_root=project, package=snapshot.package, station="MODE_B", run_id=run.run_id)
    modeb.parent.mkdir(parents=True)
    modeb.write_text("# receipt-bound Mode B skeleton\n", encoding="utf-8")
    modeb_receipt = write_run_receipt(
        project, ["MODE_B"], input_zip, 0, "", "", binding,
        run_id=run.run_id, station="MODE_B", package_snapshot=snapshot, artifact_paths=(modeb,),
    )
    run = registry.transition(run.run_id, WorkflowState.MODE_B_SKELETON_RECEIPTED, modeb_receipt)
    assert registry.load_last_validated_run(binding).run_id == run.run_id
    original_modeb = modeb.read_text(encoding="utf-8")
    modeb.unlink()
    with pytest.raises(ValueError, match="artifact is missing"):
        registry.load_last_validated_run(binding)
    modeb.write_text(original_modeb, encoding="utf-8")
    modeb.write_text("# changed after receipt\n", encoding="utf-8")
    with pytest.raises(ValueError, match="artifact hash is stale"):
        registry.load_last_validated_run(binding)
    modeb.write_text(original_modeb, encoding="utf-8")
    receipt = Path(run.events[-1]["receipt_path"])
    original_receipt = receipt.read_text(encoding="utf-8")
    receipt.write_text('{"changed": true}', encoding="utf-8")
    with pytest.raises(ValueError, match="receipt hash is stale"):
        registry.load_last_validated_run(binding)
    receipt.write_text(original_receipt, encoding="utf-8")
    (snapshot.package / "manifest.json").write_text('{"changed": true}', encoding="utf-8")
    with pytest.raises(ValueError, match="stale"):
        registry.load_last_validated_run(binding)


def test_registry_requires_ordered_successful_receipts(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    binding = _binding(tmp_path)
    input_zip = project / "input.zip"
    input_zip.write_bytes(b"fixture")
    registry = WorkflowRegistry(project)
    receipt = write_run_receipt(project, ["STAGE"], input_zip, 0, "", "", binding, run_id="r", station="INPUT")
    run = registry.create_input_run(input_path=input_zip, receipt=receipt, binding=binding, run_id="r")
    bad_receipt = write_run_receipt(project, ["MODE"], input_zip, 0, "", "", binding, run_id="r", station="MODE_B")
    with pytest.raises(ValueError, match="invalid receipt-backed transition"):
        registry.transition(run.run_id, WorkflowState.MODE_B_SKELETON_RECEIPTED, bad_receipt)
    assert len(registry.status_rows(run.run_id)) == 6


def test_launcher_requires_binding_and_is_loopback_only(tmp_path):
    binding = _binding(tmp_path)
    command, env = lab_quest_launch_command(tmp_path / "project", 9876, True, binding=binding)
    assert command[1:4] == ["-m", "streamlit", "run"]
    assert "127.0.0.1" in command
    assert env["MAMEY_LAB_QUEST_CODE_TIER"] == str(binding.code_tier)


def test_interface_keeps_provenance_accessibility_and_admission_controls_visible():
    app = Path(__file__).resolve().parents[1] / "mamey" / "lab_quest_app.py"
    source = app.read_text(encoding="utf-8")
    assert "_display_provenance(binding, root, run, snapshot)" in source
    assert 'os.environ.get("MAMEY_LAB_QUEST_ROOT")' in source
    assert "show_figure_with_alt_text" in source
    assert "Scientific review" in source
    assert "Low-motion mode (enforced)" in source
    assert "download_button" in source
    assert "page_icon" not in source
    assert "NOT_ADMITTED_BY_INTERFACE" in source
    assert "unsafe_allow_html" not in source
    assert "fonts.googleapis" not in source


def test_streamlit_six_station_smoke_when_optional_dependency_is_installed(tmp_path, monkeypatch):
    if importlib.util.find_spec("streamlit") is None:
        pytest.skip("optional Streamlit dependency is not installed")
    from streamlit.testing.v1 import AppTest

    code_tier = _code_tier(tmp_path)
    project = tmp_path / "project"
    monkeypatch.setenv("MAMEY_LAB_QUEST_ROOT", str(project))
    monkeypatch.setenv("MAMEY_LAB_QUEST_CODE_TIER", str(code_tier))
    monkeypatch.setenv("MAMEY_LAB_QUEST_EXPECT_BUNDLE", "9.7.test")
    monkeypatch.setenv("MAMEY_LAB_QUEST_EXPECT_ENGINE", "1.9.test")
    app = Path(__file__).resolve().parents[1] / "mamey" / "lab_quest_app.py"
    at = AppTest.from_file(str(app)).run()
    assert not at.exception
    assert len(at.tabs) == 6


# v9.7.405: the cli.py `lab-quest` registration hunk landed at composition (Black Cherry); skip lifted.
def test_clean_extracted_bundle_smoke_has_portable_lab_quest_sources(tmp_path):
    source = Path(__file__).resolve().parents[1]
    staged = tmp_path / "staged_bundle"
    shutil.copytree(source / "mamey", staged / "mamey")
    shutil.copy2(source / "mamey_run.py", staged / "mamey_run.py")
    shutil.copy2(source / "pyproject.toml", staged / "pyproject.toml")
    archive = shutil.make_archive(str(tmp_path / "portable_bundle"), "zip", staged)
    extracted = tmp_path / "extracted"
    shutil.unpack_archive(archive, extracted)
    for relative in ("mamey/lab_quest.py", "mamey/lab_quest_registry.py", "mamey/lab_quest_app.py"):
        assert (extracted / relative).is_file()
    text = "\n".join((extracted / rel).read_text(encoding="utf-8") for rel in ("mamey/lab_quest.py", "mamey/lab_quest_app.py"))
    assert "/Users/" not in text and "fonts.googleapis" not in text and "unsafe_allow_html" not in text
    result = subprocess.run([sys.executable, str(extracted / "mamey_run.py"), "lab-quest", "--help"], capture_output=True, text=True, check=False, timeout=60)
    assert result.returncode == 0
    assert "--project-root" in result.stdout
    assert "--code-tier" in result.stdout and "--expect-bundle-version" in result.stdout
