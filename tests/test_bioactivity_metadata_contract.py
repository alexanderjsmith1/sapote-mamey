"""Focused acceptance tests for the typed bioactivity metadata contract."""

import ast
import copy
from dataclasses import asdict
import inspect
import json
import textwrap

import pytest

from mamey import cli
from mamey.bioactivity_metadata import (
    BioactivityMetadataError,
    SCHEMA_VERSION,
    display_text,
    normalize_bioactivity,
    not_supplied,
    validate_receipt_locator,
)
from mamey.models import AssemblyMetrics, BGCRecord, MameyRun, RunContext


def _typed(**changes):
    value = not_supplied()
    value.update(changes)
    return value


def _context(**changes):
    value = {
        "strain_id": "GENERIC",
        "display_name": "Generic strain",
        "version": "test",
        "analysis_mode": "gold",
        "input_zip": "fixtures/input.zip",
        "outdir": "runs/GENERIC",
    }
    value.update(changes)
    return RunContext(**value)


def test_omission_is_typed_not_supplied_without_named_assay():
    value = normalize_bioactivity()
    assert value == not_supplied()
    assert value["assays"] == []


def test_direct_api_omission_is_deterministic():
    assert normalize_bioactivity(None) == normalize_bioactivity(None)


def test_run_context_omission_is_canonical_not_supplied():
    first = _context()
    second = _context()
    assert first.bioactivity == not_supplied()
    assert second.bioactivity == not_supplied()
    assert first.bioactivity is not second.bioactivity
    assert first == second
    assert asdict(first)["bioactivity"] == not_supplied()


def test_run_context_normalizes_exact_structured_object_deterministically():
    supplied = _typed(
        metadata_state="SUPPLIED_UNKNOWN",
        observation_state="UNKNOWN",
        warnings=["USER_SUPPLIED_UNKNOWN"],
    )
    expected = normalize_bioactivity(supplied)
    first = _context(bioactivity=supplied)
    second = _context(bioactivity=copy.deepcopy(supplied))
    supplied["warnings"].append("MUTATED_AFTER_CONSTRUCTION")
    assert first.bioactivity == expected
    assert second.bioactivity == expected
    assert first.bioactivity is not supplied


def test_run_context_arbitrary_mapping_fails_with_typed_hold():
    with pytest.raises(BioactivityMetadataError) as caught:
        _context(bioactivity={"unrecognized": True})
    assert caught.value.code == "BIOACTIVITY_LEGACY_SHAPE_HOLD"


@pytest.mark.parametrize("legacy", [
    "",
    "generic historical context",
    {"status": "unknown", "targets": "generic target"},
    {"status": "unknown", "targets": "generic target", "compound_linkage": "unknown"},
])
def test_run_context_preserves_finite_legacy_migration(legacy):
    assert _context(bioactivity=legacy).bioactivity == normalize_bioactivity(legacy)


def test_cli_malformed_mapping_is_typed_prewrite_refusal(tmp_path, capsys):
    outdir = tmp_path / "must-not-exist"
    result = cli.run_one_strain(
        strain_id="GENERIC",
        display_name="Generic strain",
        input_zip="fixtures/missing.zip",
        outdir=str(outdir),
        mode="gold",
        taxonomy="not verified",
        source="not supplied",
        bioactivity={"unrecognized": True},
    )
    captured = capsys.readouterr()
    assert result == {"status": "BIOACTIVITY_LEGACY_SHAPE_HOLD", "written": False}
    assert captured.out == ""
    assert captured.err == (
        "ERROR: BIOACTIVITY_LEGACY_SHAPE_HOLD: "
        "legacy dictionary keys are not whitelisted\n"
    )
    assert "Traceback" not in captured.err
    assert "unrecognized" not in captured.err
    assert not outdir.exists()


def test_cli_valid_mapping_reaches_output_boundary_unchanged(tmp_path, monkeypatch):
    supplied = _typed(
        metadata_state="SUPPLIED_UNKNOWN",
        observation_state="UNKNOWN",
        warnings=["GENERIC_UNKNOWN"],
    )
    expected = normalize_bioactivity(supplied)
    observed = []
    real_normalize = cli.normalize_bioactivity

    class StopAfterAdmission(RuntimeError):
        pass

    def record_admission(value):
        result = real_normalize(value)
        observed.append(result)
        return result

    def stop_before_write(self, *args, **kwargs):
        raise StopAfterAdmission

    monkeypatch.setattr(cli, "normalize_bioactivity", record_admission)
    monkeypatch.setattr(cli.Path, "mkdir", stop_before_write)
    with pytest.raises(StopAfterAdmission):
        cli.run_one_strain(
            strain_id="GENERIC",
            display_name="Generic strain",
            input_zip="fixtures/input.zip",
            outdir=str(tmp_path / "not-written"),
            mode="gold",
            taxonomy="not verified",
            source="not supplied",
            bioactivity=supplied,
        )
    assert observed == [expected]


def test_cli_command_returns_nonzero_for_typed_prewrite_refusal(tmp_path, capsys):
    outdir = tmp_path / "must-not-exist"
    return_code = cli.main([
        "run",
        "--strain", "GENERIC",
        "--input-zip", "fixtures/missing.zip",
        "--outdir", str(outdir),
        "--mode", "gold",
        "--bioactivity-json", '{"unrecognized": true}',
    ])
    captured = capsys.readouterr()
    assert return_code == 1
    assert "BIOACTIVITY_LEGACY_SHAPE_HOLD" in captured.err
    assert "Traceback" not in captured.err
    assert "unrecognized" not in captured.err
    assert '"written": false' in captured.out
    assert not outdir.exists()


def test_bioactivity_states_do_not_change_triage_bytes():
    bgc = BGCRecord(
        bgc_id="BGC001",
        contig="NODE_1_length_100",
        region_number=1,
        start=0,
        end=100,
        contig_length=100,
        products=["T1PKS"],
    )
    assembly = AssemblyMetrics(genome_bp=100, contigs=1, n50=100, gc_pct=70.0, largest_contig=100)
    states = [
        None,
        _typed(metadata_state="SUPPLIED_UNKNOWN", observation_state="UNKNOWN"),
        _typed(metadata_state="MEASURED_NEGATIVE", observation_state="NEGATIVE"),
        _typed(metadata_state="MEASURED_POSITIVE", observation_state="POSITIVE"),
    ]
    rendered = []
    for state in states:
        run = MameyRun(
            context=_context(bioactivity=state),
            assembly=assembly,
            bgcs=[copy.deepcopy(bgc)],
            scan_status={},
        )
        rendered.append(json.dumps([asdict(row) for row in run.triage], sort_keys=True))
    assert len(set(rendered)) == 1


def test_run_one_strain_has_no_function_local_stderr_owner():
    tree = ast.parse(textwrap.dedent(inspect.getsource(cli.run_one_strain)))
    local_aliases = [
        alias.asname
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
        if alias.name == "sys"
    ]
    assert "_sys" not in local_aliases


def test_example_only_is_refused_before_production_admission():
    with pytest.raises(BioactivityMetadataError, match="BIOACTIVITY_EXAMPLE_ONLY_HOLD"):
        normalize_bioactivity(_typed(usage_scope="EXAMPLE_ONLY"))


@pytest.mark.parametrize("value", [
    {"status": "x"},
    {"status": "x", "targets": "y", "extra": "z"},
    ["not", "a", "recognized", "shape"],
])
def test_only_exact_legacy_shapes_are_considered(value):
    with pytest.raises(BioactivityMetadataError, match="BIOACTIVITY_LEGACY_SHAPE_HOLD"):
        normalize_bioactivity(value)


def test_legacy_scalar_and_empty_string_have_distinct_typed_compatibility_states():
    assert normalize_bioactivity("MRSA+Candida")["metadata_state"] == "LEGACY_UNTYPED_CONTEXT"
    empty = normalize_bioactivity("")
    assert empty["metadata_state"] == "NOT_SUPPLIED"
    assert empty["warnings"] == ["LEGACY_EMPTY_STRING_NORMALIZED"]


def test_typed_metadata_rejects_not_supplied_assays():
    with pytest.raises(BioactivityMetadataError, match="BIOACTIVITY_LEGACY_SHAPE_HOLD"):
        normalize_bioactivity(_typed(assays=[{"assay_name": "not admitted"}]))


@pytest.mark.parametrize("locator", ["evidence/source.json", "evidence://root-1/source.json", "evidence/private-id/source"])
def test_structural_locator_allows_portable_grammar_without_privacy_decision(locator):
    assert validate_receipt_locator(locator) == locator


@pytest.mark.parametrize("locator", ["/absolute/source.json", "../source.json", "file:///tmp/source", "C:\\host\\source", "~/source"])
def test_structural_locator_rejects_host_and_traversal_forms(locator):
    with pytest.raises(BioactivityMetadataError, match="BIOACTIVITY_LOCATOR_HOLD"):
        validate_receipt_locator(locator)


def test_display_never_invents_target_or_bgc_linkage():
    text = display_text(None).lower()
    assert "not supplied" in text
    assert "mrsa" not in text
    assert "bgc" not in text


def test_schema_version_is_fixed():
    malformed = copy.deepcopy(not_supplied())
    malformed["schema_version"] = "future"
    with pytest.raises(BioactivityMetadataError, match="BIOACTIVITY_LEGACY_SHAPE_HOLD"):
        normalize_bioactivity(malformed)
    assert SCHEMA_VERSION == "bioactivity_metadata_v1"


def test_punchcard_refuses_shortened_locus_identity(monkeypatch):
    import importlib.util
    from pathlib import Path
    module_path = Path(__file__).parents[1] / "tools" / "build_punchcard.py"
    spec = importlib.util.spec_from_file_location("build_punchcard_candidate", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    with pytest.raises(ValueError, match="PUNCHCARD_IDENTITY_HOLD"):
        module._complete_identity("GENERIC", {"bgc_id": "BGC001", "contig": "NODE_1"})
    assert module._complete_identity("GENERIC", {
        "bgc_id": "BGC001", "contig": "NODE_1_length_10", "region": "region001",
    }) == "GENERIC / NODE_1_length_10 / region001 / BGC001"
